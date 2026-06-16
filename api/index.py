"""Vercel serverless entry point — exposes the Gradio app as an ASGI handler."""

import sys
import os

# Make project root importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app import demo

# Vercel Python runtime expects `app` to be an ASGI callable
app = demo.app
