"""Gradio web UI for the AI Automation Agent."""

import os
import gradio as gr
from dotenv import load_dotenv

load_dotenv()

from agent import Agent

MODELS = [
    "anthropic/claude-sonnet-4-5",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "google/gemini-2.0-flash",
    "meta-llama/llama-3.3-70b-instruct",
]

_agents: dict[str, Agent] = {}


def get_agent(model: str) -> Agent:
    if model not in _agents:
        _agents[model] = Agent(model=model)
    return _agents[model]


DESCRIPTION = """
# AI Automation Agent

Describe any task in plain English — the agent will execute it using its tools.

**Capabilities:** Browser automation · File processing · API calls · Code execution · Page speed analysis
"""

EXAMPLES = [
    "Check the page speed of https://example.com",
    "Run Python code to list all prime numbers up to 50",
    "Fetch the title from https://example.com",
    "What files are in my current directory?",
    "Calculate compound interest: 10000 at 8% for 5 years",
]

with gr.Blocks(title="AI Automation Agent", fill_height=True) as demo:
    gr.Markdown(DESCRIPTION)

    with gr.Row():
        model_dd = gr.Dropdown(
            choices=MODELS,
            value=os.getenv("OPENROUTER_MODEL", MODELS[0]),
            label="Model",
            scale=3,
        )
        reset_btn = gr.Button("New Chat", variant="secondary", scale=1)

    chatbot = gr.Chatbot(
        elem_id="chatbot",
        show_label=False,
        render_markdown=True,
        height=460,
    )

    with gr.Row():
        msg_box = gr.Textbox(
            placeholder="Describe your task…",
            show_label=False,
            scale=5,
            autofocus=True,
            lines=1,
        )
        send_btn = gr.Button("Send", variant="primary", scale=1)

    gr.Examples(
        examples=EXAMPLES,
        inputs=msg_box,
        label="Try an example",
    )

    def user_submit(message, history):
        if not message.strip():
            return history, ""
        history = history + [{"role": "user", "content": message}]
        return history, ""

    def bot_reply(history, model):
        user_msg = history[-1]["content"]
        history = history + [{"role": "assistant", "content": ""}]
        agent = get_agent(model)
        for partial in agent.stream_chat(user_msg):
            history[-1]["content"] = partial
            yield history

    def reset_conversation(model):
        if model in _agents:
            _agents[model].reset()
        return [], ""

    msg_box.submit(
        user_submit, [msg_box, chatbot], [chatbot, msg_box], queue=False
    ).then(bot_reply, [chatbot, model_dd], chatbot)

    send_btn.click(
        user_submit, [msg_box, chatbot], [chatbot, msg_box], queue=False
    ).then(bot_reply, [chatbot, model_dd], chatbot)

    reset_btn.click(
        reset_conversation,
        inputs=model_dd,
        outputs=[chatbot, msg_box],
        queue=False,
    )


if __name__ == "__main__":
    demo.queue()
    demo.launch(
        server_name="0.0.0.0",   # accessible on local network / mobile
        server_port=7860,
        share=False,              # set True for a public gradio.live URL
        show_error=True,
    )
