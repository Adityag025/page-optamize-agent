"""Core agent: OpenRouter + tool dispatch loop."""

from __future__ import annotations
import json
import os
from typing import Any

from openai import OpenAI

from tools import browser, files, http_tool, code_runner, pagespeed

# Convert from Anthropic-style {name, description, input_schema}
# to OpenAI-style {type, function: {name, description, parameters}}
def _to_openai_tool(t: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
        },
    }


ALL_TOOLS = [
    _to_openai_tool(t)
    for t in (
        browser.TOOL_DEFINITIONS
        + files.TOOL_DEFINITIONS
        + http_tool.TOOL_DEFINITIONS
        + code_runner.TOOL_DEFINITIONS
        + pagespeed.TOOL_DEFINITIONS
    )
]

TOOL_DISPATCHERS = {
    **{t["name"]: browser.dispatch for t in browser.TOOL_DEFINITIONS},
    **{t["name"]: files.dispatch for t in files.TOOL_DEFINITIONS},
    **{t["name"]: http_tool.dispatch for t in http_tool.TOOL_DEFINITIONS},
    **{t["name"]: code_runner.dispatch for t in code_runner.TOOL_DEFINITIONS},
    **{t["name"]: pagespeed.dispatch for t in pagespeed.TOOL_DEFINITIONS},
}

SYSTEM_PROMPT = """You are an AI automation agent. You help users automate repetitive tasks.

You have tools for:
- Browser automation (navigate, click, type, screenshot, extract text/links)
- File & data processing (read/write files, CSV analysis, PDF extraction)
- HTTP/API calls (GET, POST, PUT, DELETE to any URL)
- Code execution (run Python snippets, run shell commands)
- Page speed analysis (Google PageSpeed Insights, Lighthouse)

When given a task:
1. Break it into steps and execute them using your tools.
2. Report results clearly and concisely.
3. If a step fails, try an alternative approach.
4. For multi-step workflows, complete all steps before summarizing.

Always use tools to actually DO the task, not just describe how to do it."""


class Agent:
    def __init__(
        self,
        model: str | None = None,
        max_tokens: int = 2000,
    ):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://github.com/page-optamize-agent",
                "X-Title": "Page Optimize Agent",
            },
        )
        self.model = model or os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")
        self.max_tokens = max_tokens
        self.history: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    def _run_tool(self, tool_name: str, tool_input: dict) -> str:
        dispatcher = TOOL_DISPATCHERS.get(tool_name)
        if not dispatcher:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
        try:
            result = dispatcher(tool_name, tool_input)
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _call_api(self) -> Any:
        return self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            tools=ALL_TOOLS,
            messages=self.history,
        )

    def chat(self, user_message: str) -> str:
        """Blocking chat — returns final reply string."""
        for chunk in self.stream_chat(user_message):
            pass
        return chunk  # last yielded value is the final reply

    def stream_chat(self, user_message: str):
        """
        Generator that yields incremental status strings as tools run,
        then yields the final reply as the last value.
        Useful for streaming UIs (e.g. Gradio).
        """
        self.history.append({"role": "user", "content": user_message})
        accumulated = ""

        while True:
            response = self._call_api()
            choice = response.choices[0]
            message = choice.message
            self.history.append(message.model_dump(exclude_unset=False))

            if choice.finish_reason == "stop":
                final = message.content or ""
                yield accumulated + final
                return

            if choice.finish_reason == "tool_calls" and message.tool_calls:
                for tc in message.tool_calls:
                    fn = tc.function
                    try:
                        tool_input = json.loads(fn.arguments)
                    except json.JSONDecodeError:
                        tool_input = {}

                    # Yield a status line so the UI can show progress
                    status_line = f"*Running `{fn.name}`…*\n\n"
                    accumulated += status_line
                    yield accumulated

                    result_str = self._run_tool(fn.name, tool_input)
                    self.history.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_str,
                    })
                continue

            yield accumulated + (message.content or f"[Stopped: {choice.finish_reason}]")
            return

    def reset(self):
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
