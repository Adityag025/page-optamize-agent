"""Safe Python code execution tool."""

from __future__ import annotations
import io
import subprocess
import sys
import textwrap
import traceback
from typing import Any


def run_python(code: str, timeout: int = 30) -> dict:
    """
    Execute Python code in a subprocess and return stdout/stderr.
    Runs in isolation so it can't modify the agent's state.
    """
    wrapped = textwrap.dedent(f"""
import sys, json, traceback
_output = []
_error = None
try:
{textwrap.indent(code, "    ")}
except Exception as e:
    _error = traceback.format_exc()
""")
    try:
        result = subprocess.run(
            [sys.executable, "-c", wrapped],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "stdout": result.stdout[:5000],
            "stderr": (result.stderr or "")[:2000],
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Code execution timed out after {timeout}s"}
    except Exception as e:
        return {"error": str(e)}


def run_shell(command: str, timeout: int = 30, cwd: str | None = None) -> dict:
    """Run a shell command and return output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        return {
            "stdout": result.stdout[:5000],
            "stderr": (result.stderr or "")[:2000],
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {timeout}s"}
    except Exception as e:
        return {"error": str(e)}


TOOL_DEFINITIONS = [
    {
        "name": "run_python",
        "description": (
            "Execute Python code and return stdout/stderr. "
            "Use for data transformations, calculations, file processing, or any Python logic. "
            "Code runs in a subprocess — import whatever you need."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"},
                "timeout": {"type": "integer", "description": "Max execution time in seconds (default: 30)"}
            },
            "required": ["code"]
        }
    },
    {
        "name": "run_shell",
        "description": (
            "Run a shell command (bash). Use for file operations, running scripts, "
            "installing packages, checking system state, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to run"},
                "timeout": {"type": "integer", "description": "Max execution time in seconds (default: 30)"},
                "cwd": {"type": "string", "description": "Working directory (optional)"}
            },
            "required": ["command"]
        }
    },
]


def dispatch(name: str, inputs: dict) -> Any:
    if name == "run_python":
        return run_python(inputs["code"], inputs.get("timeout", 30))
    if name == "run_shell":
        return run_shell(inputs["command"], inputs.get("timeout", 30), inputs.get("cwd"))
    raise ValueError(f"Unknown code tool: {name}")
