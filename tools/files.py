"""File and data processing tools."""

from __future__ import annotations
import csv
import json
import os
from pathlib import Path
from typing import Any


def _safe_path(path: str) -> Path:
    p = Path(path).expanduser().resolve()
    return p


def read_file(path: str, encoding: str = "utf-8") -> dict:
    p = _safe_path(path)
    if not p.exists():
        return {"error": f"File not found: {path}"}
    suffix = p.suffix.lower()

    if suffix == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(str(p))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return {"content": text[:10000], "pages": len(reader.pages), "truncated": len(text) > 10000}
        except ImportError:
            return {"error": "pypdf not installed. Run: pip install pypdf"}

    if suffix in (".csv",):
        rows = []
        with open(p, newline="", encoding=encoding) as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= 100:
                    return {"rows": rows, "truncated": True, "note": "Showing first 100 rows"}
                rows.append(dict(row))
        return {"rows": rows, "count": len(rows)}

    if suffix in (".json", ".jsonl"):
        text = p.read_text(encoding=encoding)
        if suffix == ".jsonl":
            lines = [json.loads(l) for l in text.splitlines() if l.strip()]
            return {"records": lines[:50], "total_lines": len(lines)}
        return {"data": json.loads(text)}

    # plain text / code / etc.
    text = p.read_text(encoding=encoding, errors="replace")
    return {"content": text[:10000], "truncated": len(text) > 10000, "size_bytes": p.stat().st_size}


def write_file(path: str, content: str, mode: str = "w") -> dict:
    p = _safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, mode, encoding="utf-8") as f:
        f.write(content)
    return {"written": str(p), "bytes": len(content.encode())}


def list_directory(path: str = ".") -> dict:
    p = _safe_path(path)
    if not p.exists():
        return {"error": f"Directory not found: {path}"}
    entries = []
    for entry in sorted(p.iterdir()):
        entries.append({
            "name": entry.name,
            "type": "dir" if entry.is_dir() else "file",
            "size": entry.stat().st_size if entry.is_file() else None
        })
    return {"path": str(p), "entries": entries}


def process_csv(path: str, operation: str, **kwargs) -> dict:
    """Run a pandas operation on a CSV file."""
    try:
        import pandas as pd
    except ImportError:
        return {"error": "pandas not installed. Run: pip install pandas"}
    p = _safe_path(path)
    df = pd.read_csv(str(p))

    if operation == "describe":
        return {"stats": df.describe().to_dict()}
    if operation == "head":
        n = kwargs.get("n", 5)
        return {"rows": df.head(n).to_dict(orient="records")}
    if operation == "columns":
        return {"columns": list(df.columns), "shape": list(df.shape)}
    if operation == "filter":
        col, value = kwargs["column"], kwargs["value"]
        result = df[df[col] == value]
        return {"rows": result.head(50).to_dict(orient="records"), "count": len(result)}
    if operation == "sort":
        col = kwargs["column"]
        asc = kwargs.get("ascending", True)
        result = df.sort_values(col, ascending=asc)
        return {"rows": result.head(50).to_dict(orient="records")}
    if operation == "group_sum":
        col = kwargs["column"]
        result = df.groupby(col).sum(numeric_only=True).reset_index()
        return {"rows": result.to_dict(orient="records")}
    return {"error": f"Unknown operation: {operation}"}


TOOL_DEFINITIONS = [
    {
        "name": "read_file",
        "description": "Read a file from disk. Supports .txt, .py, .csv, .json, .jsonl, .pdf and more.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative file path"},
                "encoding": {"type": "string", "description": "Text encoding (default: utf-8)"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write text content to a file on disk.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write to"},
                "content": {"type": "string", "description": "Content to write"},
                "mode": {"type": "string", "enum": ["w", "a"], "description": "w=overwrite, a=append (default: w)"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "list_directory",
        "description": "List files and folders in a directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path (default: current directory)"}
            }
        }
    },
    {
        "name": "process_csv",
        "description": "Analyze or transform a CSV file using pandas. Operations: describe, head, columns, filter, sort, group_sum.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the CSV file"},
                "operation": {
                    "type": "string",
                    "enum": ["describe", "head", "columns", "filter", "sort", "group_sum"],
                    "description": "Operation to perform"
                },
                "column": {"type": "string", "description": "Column name (required for filter, sort, group_sum)"},
                "value": {"type": "string", "description": "Filter value (for filter operation)"},
                "n": {"type": "integer", "description": "Number of rows for head (default: 5)"},
                "ascending": {"type": "boolean", "description": "Sort order for sort operation"}
            },
            "required": ["path", "operation"]
        }
    },
]


def dispatch(name: str, inputs: dict) -> Any:
    if name == "read_file":
        return read_file(inputs["path"], inputs.get("encoding", "utf-8"))
    if name == "write_file":
        return write_file(inputs["path"], inputs["content"], inputs.get("mode", "w"))
    if name == "list_directory":
        return list_directory(inputs.get("path", "."))
    if name == "process_csv":
        kwargs = {k: v for k, v in inputs.items() if k not in ("path", "operation")}
        return process_csv(inputs["path"], inputs["operation"], **kwargs)
    raise ValueError(f"Unknown file tool: {name}")
