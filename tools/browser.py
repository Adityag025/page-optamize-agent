"""Browser automation tools using Playwright."""

from __future__ import annotations
import asyncio
import base64
from typing import Any

_browser = None
_page = None
_playwright = None


async def _get_page():
    global _browser, _page, _playwright
    if _page is None:
        from playwright.async_api import async_playwright
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(headless=True)
        _page = await _browser.new_page()
    return _page


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def _navigate(url: str) -> dict:
    page = await _get_page()
    response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    title = await page.title()
    return {"url": page.url, "title": title, "status": response.status if response else None}


async def _get_text(selector: str | None = None) -> dict:
    page = await _get_page()
    if selector:
        element = await page.query_selector(selector)
        text = await element.inner_text() if element else ""
    else:
        text = await page.inner_text("body")
    return {"text": text[:8000]}  # cap to avoid huge payloads


async def _click(selector: str) -> dict:
    page = await _get_page()
    await page.click(selector, timeout=10000)
    await page.wait_for_load_state("domcontentloaded")
    return {"clicked": selector, "current_url": page.url}


async def _type_text(selector: str, text: str) -> dict:
    page = await _get_page()
    await page.fill(selector, text)
    return {"typed": text, "into": selector}


async def _screenshot() -> dict:
    page = await _get_page()
    data = await page.screenshot(type="png")
    b64 = base64.b64encode(data).decode()
    return {"screenshot_base64": b64, "url": page.url}


async def _get_links() -> dict:
    page = await _get_page()
    links = await page.eval_on_selector_all(
        "a[href]",
        "els => els.map(e => ({text: e.innerText.trim(), href: e.href}))"
    )
    return {"links": links[:50]}


async def _close():
    global _browser, _page, _playwright
    if _browser:
        await _browser.close()
    if _playwright:
        await _playwright.stop()
    _browser = None
    _page = None
    _playwright = None


def navigate(url: str) -> dict:
    return _run(_navigate(url))


def get_text(selector: str | None = None) -> dict:
    return _run(_get_text(selector))


def click(selector: str) -> dict:
    return _run(_click(selector))


def type_text(selector: str, text: str) -> dict:
    return _run(_type_text(selector, text))


def screenshot() -> dict:
    return _run(_screenshot())


def get_links() -> dict:
    return _run(_get_links())


def close_browser() -> dict:
    _run(_close())
    return {"status": "browser closed"}


TOOL_DEFINITIONS = [
    {
        "name": "browser_navigate",
        "description": "Navigate the browser to a URL. Use this to open websites.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to navigate to"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "browser_get_text",
        "description": "Get text content from the current page, optionally scoped to a CSS selector.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector to scope extraction (optional, defaults to full body)"}
            }
        }
    },
    {
        "name": "browser_click",
        "description": "Click an element on the page using a CSS selector.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector of the element to click"}
            },
            "required": ["selector"]
        }
    },
    {
        "name": "browser_type",
        "description": "Type text into an input field using a CSS selector.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector of the input field"},
                "text": {"type": "string", "description": "Text to type"}
            },
            "required": ["selector", "text"]
        }
    },
    {
        "name": "browser_screenshot",
        "description": "Take a screenshot of the current page. Returns base64-encoded PNG.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "browser_get_links",
        "description": "Get all hyperlinks from the current page.",
        "input_schema": {"type": "object", "properties": {}}
    },
]


def dispatch(name: str, inputs: dict) -> Any:
    if name == "browser_navigate":
        return navigate(inputs["url"])
    if name == "browser_get_text":
        return get_text(inputs.get("selector"))
    if name == "browser_click":
        return click(inputs["selector"])
    if name == "browser_type":
        return type_text(inputs["selector"], inputs["text"])
    if name == "browser_screenshot":
        return screenshot()
    if name == "browser_get_links":
        return get_links()
    raise ValueError(f"Unknown browser tool: {name}")
