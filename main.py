#!/usr/bin/env python3
"""Conversational AI automation agent — CLI entry point."""

import os
import sys

from dotenv import load_dotenv

load_dotenv()


def print_banner():
    print("=" * 60)
    print("  AI Automation Agent")
    print("  Type your task in plain English. Type /quit to exit.")
    print("  Type /reset to start a new conversation.")
    print("  Type /help for available capabilities.")
    print("=" * 60)
    print()


HELP_TEXT = """
Available capabilities:

  Browser automation
    - Navigate websites, click buttons, fill forms
    - Extract text, links, or take screenshots
    Example: "Go to example.com and extract all the links"

  File & data processing
    - Read/write text, CSV, JSON, PDF files
    - Analyze CSV data (stats, filter, sort, group)
    Example: "Read data.csv and show me the top 5 rows by revenue"

  API & integrations
    - Make HTTP requests to any REST API
    Example: "Call the GitHub API and list my repos"

  Code execution
    - Run Python code or shell commands
    Example: "Write a Python script to rename all jpg files in ~/Downloads"

  Page speed optimization
    - Analyze any URL with Google PageSpeed Insights
    Example: "Check the page speed of https://example.com"

Commands:
  /reset   — clear conversation history
  /help    — show this help
  /quit    — exit
"""


def main():
    print_banner()

    if not os.getenv("OPENROUTER_API_KEY"):
        print("ERROR: OPENROUTER_API_KEY is not set.")
        print("  Set it in your .env file or export it:")
        print("  export OPENROUTER_API_KEY=sk-or-...")
        sys.exit(1)

    from agent import Agent
    agent = Agent()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("/quit", "/exit", "quit", "exit"):
            print("Goodbye!")
            break

        if user_input.lower() == "/reset":
            agent.reset()
            print("[Conversation reset]\n")
            continue

        if user_input.lower() == "/help":
            print(HELP_TEXT)
            continue

        print("Agent: ", end="", flush=True)
        try:
            response = agent.chat(user_input)
            print(response)
        except Exception as e:
            print(f"[Error] {e}")
        print()


if __name__ == "__main__":
    main()
