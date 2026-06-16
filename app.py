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


CAPABILITIES_MD = """
| Tool | What it does |
|------|-------------|
| Browser | Navigate sites, click, fill forms, extract text & links |
| Files | Read/write text, CSV, PDF, JSON |
| HTTP | Call any REST API (GET, POST, PUT, DELETE) |
| Code | Run Python snippets or shell commands |
| PageSpeed | Google PageSpeed Insights + Lighthouse audit |
"""

EXAMPLES = [
    ["Check the page speed of https://example.com"],
    ["Run Python to list all prime numbers up to 100"],
    ["Fetch the HTML title of https://example.com"],
    ["What files are in the current directory?"],
    ["Calculate compound interest: ₹10,000 at 8% for 5 years"],
    ["Write a Python script to count words in a text file"],
]

CSS = """
/* ── layout ─────────────────────────────────────── */
body, .gradio-container { background: #0f1117 !important; }
.contain { max-width: 900px; margin: 0 auto; padding: 0 12px; }

/* ── header ──────────────────────────────────────── */
.header-box {
  background: linear-gradient(135deg, #1a1f2e 0%, #16213e 100%);
  border: 1px solid #2d3561;
  border-radius: 16px;
  padding: 24px 28px 18px;
  margin-bottom: 16px;
}
.header-box h1 { color: #e2e8f0; font-size: 1.6rem; margin: 0 0 4px; }
.header-box p  { color: #94a3b8; font-size: 0.92rem; margin: 0; }

/* ── controls row ────────────────────────────────── */
.controls-row { display: flex; gap: 10px; align-items: flex-end; margin-bottom: 10px; }

/* ── chatbot ─────────────────────────────────────── */
#chatbot { border-radius: 12px !important; }
#chatbot .message.bot { background: #1e2435 !important; }
#chatbot .message.user { background: #2d3561 !important; }

/* ── input row ───────────────────────────────────── */
.input-row { display: flex; gap: 8px; align-items: flex-end; margin-top: 8px; }
#send-btn { min-width: 90px; height: 44px; border-radius: 10px !important; }
#msg-box textarea { border-radius: 10px !important; }

/* ── capabilities accordion ──────────────────────── */
.cap-accordion { margin-top: 12px; }
.cap-accordion > div { background: #1a1f2e !important; border-color: #2d3561 !important; border-radius: 10px !important; }

/* ── examples ────────────────────────────────────── */
.examples-section { margin-top: 8px; }
.examples-section .example {
  background: #1a1f2e !important;
  border: 1px solid #2d3561 !important;
  border-radius: 8px !important;
  color: #94a3b8 !important;
  font-size: 0.85rem !important;
}

/* ── footer ──────────────────────────────────────── */
footer { display: none !important; }
"""

with gr.Blocks(title="AI Automation Agent", fill_height=False) as demo:
    with gr.Column(elem_classes="contain"):

        # ── Header ──────────────────────────────────────
        gr.HTML("""
        <div class="header-box">
          <h1>⚡ AI Automation Agent</h1>
          <p>Describe any task in plain English — the agent picks the right tools and executes it.</p>
        </div>
        """)

        # ── Model selector + New Chat ────────────────────
        with gr.Row(elem_classes="controls-row"):
            model_dd = gr.Dropdown(
                choices=MODELS,
                value=os.getenv("OPENROUTER_MODEL", MODELS[0]),
                label="Model",
                scale=4,
                min_width=220,
            )
            reset_btn = gr.Button("🔄 New Chat", variant="secondary", scale=1, min_width=110)

        # ── Chatbot ──────────────────────────────────────
        chatbot = gr.Chatbot(
            elem_id="chatbot",
            show_label=False,
            render_markdown=True,
            height=480,
            placeholder="<p style='color:#4a5568;text-align:center;margin-top:80px'>Send a message to get started…</p>",
            avatar_images=(
                None,
                "https://api.dicebear.com/7.x/bottts-neutral/svg?seed=agent&backgroundColor=1a1f2e",
            ),
        )

        # ── Input row ────────────────────────────────────
        with gr.Row(elem_classes="input-row"):
            msg_box = gr.Textbox(
                elem_id="msg-box",
                placeholder="Describe your task… (Enter to send)",
                show_label=False,
                scale=5,
                autofocus=True,
                lines=1,
                max_lines=4,
            )
            send_btn = gr.Button("Send ➤", elem_id="send-btn", variant="primary", scale=1)

        # ── Capabilities accordion ───────────────────────
        with gr.Accordion("Available tools", open=False, elem_classes="cap-accordion"):
            gr.Markdown(CAPABILITIES_MD)

        # ── Examples ─────────────────────────────────────
        gr.Examples(
            examples=EXAMPLES,
            inputs=msg_box,
            label="Try an example",
            elem_id="examples-section",
        )

    # ── Logic ────────────────────────────────────────────

    def user_submit(message, history):
        if not message.strip():
            return history, ""
        return history + [{"role": "user", "content": message}], ""

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
        reset_conversation, inputs=model_dd, outputs=[chatbot, msg_box], queue=False
    )


if __name__ == "__main__":
    demo.queue()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,        # set True for a public gradio.live URL
        show_error=True,
        css=CSS,
    )
