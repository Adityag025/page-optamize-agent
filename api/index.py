"""
Vercel entry point: FastAPI app with a self-contained chat UI.
No Gradio — avoids all Gradio serverless incompatibilities.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from agent import Agent

app = FastAPI()

MODELS = [
    "anthropic/claude-sonnet-4-5",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "google/gemini-2.0-flash",
    "meta-llama/llama-3.3-70b-instruct",
]

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Automation Agent</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0f1117; --surface: #1a1f2e; --border: #2d3561;
    --accent: #6366f1; --accent-hover: #818cf8;
    --text: #e2e8f0; --muted: #94a3b8;
    --user-bg: #2d3561; --bot-bg: #1e2435;
    --radius: 14px;
  }
  body { background: var(--bg); color: var(--text); font-family: Inter, system-ui, sans-serif;
         min-height: 100dvh; display: flex; flex-direction: column; }
  #app { max-width: 820px; width: 100%; margin: 0 auto; padding: 16px;
         display: flex; flex-direction: column; flex: 1; gap: 12px; }

  /* header */
  header { background: linear-gradient(135deg, var(--surface), #16213e);
           border: 1px solid var(--border); border-radius: var(--radius);
           padding: 18px 22px; }
  header h1 { font-size: 1.4rem; font-weight: 700; }
  header p  { color: var(--muted); font-size: 0.85rem; margin-top: 3px; }

  /* controls */
  .controls { display: flex; gap: 10px; align-items: center; }
  select {
    flex: 1; background: var(--surface); color: var(--text);
    border: 1px solid var(--border); border-radius: 10px;
    padding: 8px 12px; font-size: 0.875rem; cursor: pointer; outline: none;
  }
  .btn-reset {
    background: var(--surface); color: var(--muted);
    border: 1px solid var(--border); border-radius: 10px;
    padding: 8px 14px; font-size: 0.875rem; cursor: pointer; white-space: nowrap;
    transition: color .15s, border-color .15s;
  }
  .btn-reset:hover { color: var(--text); border-color: var(--accent); }

  /* chat */
  #chat {
    flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 12px;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 16px; min-height: 360px;
  }
  #chat:empty::after {
    content: "Send a message to get started…";
    color: var(--muted); font-size: 0.9rem;
    display: flex; align-items: center; justify-content: center;
    height: 100%; text-align: center;
  }
  .msg { max-width: 82%; padding: 10px 14px; border-radius: 12px;
         line-height: 1.55; font-size: 0.9rem; word-break: break-word; }
  .msg.user { background: var(--user-bg); align-self: flex-end; border-bottom-right-radius: 4px; }
  .msg.bot  { background: var(--bot-bg);  align-self: flex-start; border-bottom-left-radius: 4px; }
  .msg pre  { background: #0d1117; border-radius: 8px; padding: 10px; margin-top: 8px;
              overflow-x: auto; font-size: 0.82rem; }
  .msg code { font-family: 'Fira Code', monospace; font-size: 0.85em; }
  .msg p    { margin-bottom: 6px; }
  .msg p:last-child { margin-bottom: 0; }
  .tool-badge {
    display: inline-block; background: #1e2d3d; color: #7dd3fc;
    border: 1px solid #1e4a6e; border-radius: 6px;
    padding: 2px 8px; font-size: 0.78rem; font-family: monospace; margin: 2px 0;
  }

  /* input */
  .input-row { display: flex; gap: 8px; align-items: flex-end; }
  textarea {
    flex: 1; background: var(--surface); color: var(--text);
    border: 1px solid var(--border); border-radius: 12px;
    padding: 10px 14px; font-size: 0.9rem; resize: none;
    min-height: 44px; max-height: 120px; outline: none; font-family: inherit;
    transition: border-color .15s;
  }
  textarea:focus { border-color: var(--accent); }
  .btn-send {
    background: var(--accent); color: #fff; border: none;
    border-radius: 12px; padding: 10px 20px; font-size: 0.9rem;
    cursor: pointer; white-space: nowrap; font-weight: 600;
    transition: background .15s; min-height: 44px;
  }
  .btn-send:hover   { background: var(--accent-hover); }
  .btn-send:disabled { background: #374151; cursor: not-allowed; }

  /* examples */
  .examples { display: flex; flex-wrap: wrap; gap: 8px; }
  .chip {
    background: var(--surface); color: var(--muted);
    border: 1px solid var(--border); border-radius: 20px;
    padding: 5px 13px; font-size: 0.8rem; cursor: pointer;
    transition: color .15s, border-color .15s;
  }
  .chip:hover { color: var(--text); border-color: var(--accent); }

  @media (max-width: 600px) {
    #app { padding: 10px; }
    .msg { max-width: 94%; }
  }
</style>
</head>
<body>
<div id="app">
  <header>
    <h1>⚡ AI Automation Agent</h1>
    <p>Describe any task in plain English — the agent picks the right tools and executes it.</p>
  </header>

  <div class="controls">
    <select id="model-select">
      MODELS_OPTIONS
    </select>
    <button class="btn-reset" onclick="resetChat()">🔄 New Chat</button>
  </div>

  <div id="chat"></div>

  <div class="input-row">
    <textarea id="input" placeholder="Describe your task… (Enter to send, Shift+Enter for newline)"
              rows="1" oninput="autoResize(this)"></textarea>
    <button class="btn-send" id="send-btn" onclick="sendMessage()">Send ➤</button>
  </div>

  <div class="examples">
    <span class="chip" onclick="fillInput(this)">Check page speed of example.com</span>
    <span class="chip" onclick="fillInput(this)">List prime numbers up to 100</span>
    <span class="chip" onclick="fillInput(this)">Fetch title of https://example.com</span>
    <span class="chip" onclick="fillInput(this)">Calculate ₹10,000 at 8% for 5 years</span>
    <span class="chip" onclick="fillInput(this)">What files are in the current directory?</span>
  </div>
</div>

<script>
let agentHistory = null;

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function fillInput(el) {
  const inp = document.getElementById('input');
  inp.value = el.textContent;
  inp.focus();
  autoResize(inp);
}

function resetChat() {
  document.getElementById('chat').innerHTML = '';
  agentHistory = null;
}

function addMessage(role, text) {
  const chat = document.getElementById('chat');
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  div.innerHTML = renderMarkdown(text);
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

function renderMarkdown(text) {
  // minimal markdown: code blocks, inline code, bold, tool badges
  return text
    .replace(/```([\\s\\S]*?)```/g, '<pre><code>$1</code></pre>')
    .replace(/`([^`]+)`/g, (_, c) => {
      if (c.includes('(') || c.endsWith('…')) {
        return '<span class="tool-badge">🔧 ' + escHtml(c) + '</span>';
      }
      return '<code>' + escHtml(c) + '</code>';
    })
    .replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>')
    .replace(/\\*Running (.+?)\\*\\n?/g, '<span class="tool-badge">🔧 Running $1</span><br>')
    .replace(/\\n/g, '<br>');
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

document.getElementById('input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

async function sendMessage() {
  const inp = document.getElementById('input');
  const msg = inp.value.trim();
  if (!msg) return;

  inp.value = '';
  autoResize(inp);
  const btn = document.getElementById('send-btn');
  btn.disabled = true;

  addMessage('user', msg);
  const botDiv = addMessage('bot', '…');

  const model = document.getElementById('model-select').value;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg, history: agentHistory, model })
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\\n');
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const payload = JSON.parse(line.slice(6));
          botDiv.innerHTML = renderMarkdown(payload.text);
          document.getElementById('chat').scrollTop = 9999;
          if (payload.done && payload.history) {
            agentHistory = payload.history;
          }
        } catch {}
      }
    }
  } catch (err) {
    botDiv.innerHTML = '<span style="color:#f87171">Error: ' + escHtml(String(err)) + '</span>';
  }

  btn.disabled = false;
  inp.focus();
}
</script>
</body>
</html>
""".replace(
    "MODELS_OPTIONS",
    "\n".join(
        f'<option value="{m}"{" selected" if i == 0 else ""}>{m}</option>'
        for i, m in enumerate(MODELS)
    ),
)


@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML


class ChatRequest(BaseModel):
    message: str
    history: list | None = None
    model: str = MODELS[0]


@app.post("/api/chat")
async def chat(req: ChatRequest):
    def generate():
        agent = Agent(model=req.model)
        last_partial = ""
        try:
            for partial in agent.stream_chat(req.message, initial_history=req.history):
                last_partial = partial
                data = json.dumps({"text": partial, "done": False})
                yield f"data: {data}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'text': f'Error: {e}', 'done': True, 'history': None})}\n\n"
            return
        # Final event — includes updated history so the client can send it next turn
        yield f"data: {json.dumps({'text': last_partial, 'done': True, 'history': agent.history})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
