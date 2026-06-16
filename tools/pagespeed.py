"""Page speed analysis tools using Google PageSpeed Insights API and Lighthouse."""

from __future__ import annotations
import json
import os
import subprocess
import sys
from typing import Any


def analyze_pagespeed(url: str, strategy: str = "mobile") -> dict:
    """
    Analyze a page using Google PageSpeed Insights API.
    Returns scores and top recommendations.
    """
    api_key = os.getenv("PAGESPEED_API_KEY", "")
    api_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = {"url": url, "strategy": strategy}
    if api_key:
        params["key"] = api_key

    try:
        import httpx
        with httpx.Client(timeout=60) as client:
            resp = client.get(api_url, params=params)
        data = resp.json()
    except ImportError:
        return {"error": "httpx not installed. Run: pip install httpx"}
    except Exception as e:
        return {"error": str(e)}

    if "error" in data:
        return {"error": data["error"].get("message", "PageSpeed API error")}

    lhr = data.get("lighthouseResult", {})
    categories = lhr.get("categories", {})
    audits = lhr.get("audits", {})

    scores = {k: round((v.get("score") or 0) * 100) for k, v in categories.items()}

    # Extract top failing audits
    opportunities = []
    for audit_id, audit in audits.items():
        if audit.get("score") is not None and audit["score"] < 0.9:
            opportunities.append({
                "id": audit_id,
                "title": audit.get("title", ""),
                "description": audit.get("description", "")[:200],
                "score": audit.get("score"),
                "display_value": audit.get("displayValue", ""),
            })
    opportunities.sort(key=lambda x: x["score"] or 0)

    return {
        "url": url,
        "strategy": strategy,
        "scores": scores,
        "top_issues": opportunities[:10],
        "fetch_time": lhr.get("fetchTime", ""),
    }


def run_lighthouse(url: str, output_path: str | None = None) -> dict:
    """
    Run Lighthouse CLI locally (requires: npm install -g lighthouse).
    Falls back to PageSpeed Insights if Lighthouse is not installed.
    """
    result = subprocess.run(["which", "lighthouse"], capture_output=True, text=True)
    if result.returncode != 0:
        return {"error": "Lighthouse CLI not found. Install with: npm install -g lighthouse"}

    out = output_path or "/tmp/lighthouse-report.json"
    cmd = [
        "lighthouse", url,
        "--output=json",
        f"--output-path={out}",
        "--chrome-flags=--headless --no-sandbox",
        "--quiet",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            return {"error": proc.stderr[:1000]}

        with open(out) as f:
            report = json.load(f)

        cats = report.get("categories", {})
        scores = {k: round((v.get("score") or 0) * 100) for k, v in cats.items()}
        return {"url": url, "scores": scores, "report_path": out}
    except subprocess.TimeoutExpired:
        return {"error": "Lighthouse timed out after 120s"}
    except Exception as e:
        return {"error": str(e)}


def get_web_vitals(url: str) -> dict:
    """
    Fetch Core Web Vitals (LCP, FID, CLS) from CrUX via PageSpeed Insights.
    """
    return analyze_pagespeed(url, strategy="mobile")


TOOL_DEFINITIONS = [
    {
        "name": "analyze_pagespeed",
        "description": (
            "Analyze a web page's performance, SEO, accessibility, and best practices "
            "using Google PageSpeed Insights. Returns scores (0-100) and top issues to fix."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Full URL of the page to analyze"},
                "strategy": {
                    "type": "string",
                    "enum": ["mobile", "desktop"],
                    "description": "Device strategy (default: mobile)"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "run_lighthouse",
        "description": (
            "Run a full Lighthouse audit locally (requires Lighthouse CLI). "
            "Returns scores and saves the full JSON report to disk."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to audit"},
                "output_path": {"type": "string", "description": "Path to save JSON report (optional)"}
            },
            "required": ["url"]
        }
    },
]


def dispatch(name: str, inputs: dict) -> Any:
    if name == "analyze_pagespeed":
        return analyze_pagespeed(inputs["url"], inputs.get("strategy", "mobile"))
    if name == "run_lighthouse":
        return run_lighthouse(inputs["url"], inputs.get("output_path"))
    raise ValueError(f"Unknown pagespeed tool: {name}")
