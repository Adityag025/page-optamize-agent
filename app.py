"""Gradio web UI for the AI Automation Agent."""

import os
import gradio as gr
from dotenv import load_dotenv

load_dotenv()

from agent import Agent, SYSTEM_PROMPT

MODELS = [
    "anthropic/claude-sonnet-4-5",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "google/gemini-2.0-flash",
    "meta-llama/llama-3.3-70b-instruct",
]

EXAMPLES = [
    "Check the page speed of https://example.com",
    "Run Python to list all prime numbers up to 100",
    "Fetch the HTML title of https://example.com",
    "What files are in the current directory?",
    "Calculate compound interest: ₹10,000 at 8% for 5 years",
]

CAPABILITIES_MD = """
| Tool | What it does |
|------|-------------|
| Browser | Navigate sites, click, fill forms, extract text & links |
| Files | Read/write text, CSV, PDF, JSON |
| HTTP | Call any REST API (GET, POST, PUT, DELETE) |
| Code | Run Python snippets or shell commands |
| PageSpeed | Google PageSpeed Insights + Lighthouse audit |
"""

CSS = """
body, .gradio-container { background: #0f1117 !important; }
.contain { max-width: 900px; margin: 0 auto; padding: 0 12px; }
.header-box {
  background: linear-gradient(135deg, #1a1f2e 0%, #16213e 100%);
  border: 1px solid #2d3561;
  border-radius: 16px;
  padding: 24px 28px 18px;
  margin-bottom: 16px;
}
.header-box h1 { color: #e2e8f0; font-size: 1.6rem; margin: 0 0 4px; }
.header-box p  { color: #94a3b8; font-size: 0.92rem; margin: 0; }
.example-chip button {
  background: #1a1f2e !important;
  border: 1px solid #2d3561 !important;
  border-radius: 20px !important;
  color: #94a3b8 !important;
  font-size: 0.82rem !important;
  padding: 4px 12px !important;
  cursor: pointer !important;
}
.example-chip button:hover { border-color: #5b6bbf !important; color: #c7d2fe !important; }
footer { display: none !important; }
"""


def make_fresh_agent(model: str) -> Agent:
    return Agent(model=model)


with gr.Blocks(title="AI Automation Agent", fill_height=False) as demo:
    # ── per-session agent history stored in browser state ──────────────
    # Stores the agent's full internal history (incl. tool results).
    # This survives across serverless invocations.
    agent_hist = gr.State(value=None)

    with gr.Column(elem_classes="contain"):

        # Header
        gr.HTML("""
        <div class="header-box">
          <h1>⚡ AI Automation Agent</h1>
          <p>Describe any task in plain English — the agent picks the right tools and executes it.</p>
        </div>
        """)

        # Controls
        with gr.Row():
            model_dd = gr.Dropdown(
                choices=MODELS,
                value=os.getenv("OPENROUTER_MODEL", MODELS[0]),
                label="Model",
                scale=4,
                min_width=220,
            )
            reset_btn = gr.Button("🔄 New Chat", variant="secondary", scale=1, min_width=110)

        # Chatbot
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

        # Input
        with gr.Row():
            msg_box = gr.Textbox(
                placeholder="Describe your task… (Enter to send)",
                show_label=False,
                scale=5,
                autofocus=True,
                lines=1,
                max_lines=4,
            )
            send_btn = gr.Button("Send ➤", variant="primary", scale=1, min_width=90)

        # Example chips (plain buttons — no CSVLogger, works on serverless)
        gr.Markdown("**Try an example:**", visible=True)
        with gr.Row():
            example_btns = [
                gr.Button(ex, elem_classes="example-chip", size="sm", variant="secondary")
                for ex in EXAMPLES
            ]

        # Capabilities accordion
        with gr.Accordion("Available tools", open=False):
            gr.Markdown(CAPABILITIES_MD)

    # ── Logic ─────────────────────────────────────────────────────────────

    def user_submit(message, chatbot_state):
        if not message.strip():
            return chatbot_state, ""
        return chatbot_state + [{"role": "user", "content": message}], ""

    def bot_reply(chatbot_state, saved_hist, model):
        user_msg = chatbot_state[-1]["content"]
        chatbot_state = chatbot_state + [{"role": "assistant", "content": ""}]

        # Fresh agent each call; restore previous conversation via initial_history
        agent = make_fresh_agent(model)
        prev_history = saved_hist  # may be None (fresh) or list (restored)

        for partial in agent.stream_chat(user_msg, initial_history=prev_history):
            chatbot_state[-1]["content"] = partial
            yield chatbot_state, saved_hist  # don't update state mid-stream

        # After streaming: persist full internal history (includes tool calls)
        yield chatbot_state, agent.history

    def reset_conversation():
        return [], None, ""

    def fill_example(example_text):
        return example_text

    # Wire send actions
    msg_box.submit(
        user_submit, [msg_box, chatbot], [chatbot, msg_box], queue=False
    ).then(bot_reply, [chatbot, agent_hist, model_dd], [chatbot, agent_hist])

    send_btn.click(
        user_submit, [msg_box, chatbot], [chatbot, msg_box], queue=False
    ).then(bot_reply, [chatbot, agent_hist, model_dd], [chatbot, agent_hist])

    reset_btn.click(
        reset_conversation, outputs=[chatbot, agent_hist, msg_box], queue=False
    )

    # Wire example chips to fill the textbox
    for btn in example_btns:
        btn.click(fill_example, inputs=btn, outputs=msg_box, queue=False)


if __name__ == "__main__":
    demo.queue()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        css=CSS,
    )
