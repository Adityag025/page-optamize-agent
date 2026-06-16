"""HTTP/API tools for calling external services."""

from __future__ import annotations
import json
from typing import Any


def http_request(
    method: str,
    url: str,
    headers: dict | None = None,
    params: dict | None = None,
    body: dict | str | None = None,
    timeout: int = 30,
) -> dict:
    try:
        import httpx
    except ImportError:
        return {"error": "httpx not installed. Run: pip install httpx"}

    method = method.upper()
    kwargs: dict = {"timeout": timeout}
    if headers:
        kwargs["headers"] = headers
    if params:
        kwargs["params"] = params
    if body:
        if isinstance(body, dict):
            kwargs["json"] = body
        else:
            kwargs["content"] = body

    with httpx.Client(follow_redirects=True) as client:
        resp = client.request(method, url, **kwargs)

    content_type = resp.headers.get("content-type", "")
    if "json" in content_type:
        try:
            data = resp.json()
        except Exception:
            data = resp.text
    else:
        data = resp.text[:5000]

    return {
        "status_code": resp.status_code,
        "headers": dict(resp.headers),
        "body": data,
    }


TOOL_DEFINITIONS = [
    {
        "name": "http_request",
        "description": (
            "Make an HTTP request to any URL. Use for calling REST APIs, fetching web pages, "
            "or interacting with external services."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                    "description": "HTTP method"
                },
                "url": {"type": "string", "description": "Full URL including scheme"},
                "headers": {
                    "type": "object",
                    "description": "HTTP headers as key-value pairs",
                    "additionalProperties": {"type": "string"}
                },
                "params": {
                    "type": "object",
                    "description": "Query string parameters",
                    "additionalProperties": {"type": "string"}
                },
                "body": {
                    "description": "Request body — object for JSON, string for raw",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Request timeout in seconds (default: 30)"
                }
            },
            "required": ["method", "url"]
        }
    },
]


def dispatch(name: str, inputs: dict) -> Any:
    if name == "http_request":
        return http_request(
            inputs["method"],
            inputs["url"],
            headers=inputs.get("headers"),
            params=inputs.get("params"),
            body=inputs.get("body"),
            timeout=inputs.get("timeout", 30),
        )
    raise ValueError(f"Unknown http tool: {name}")
