"""Local Eyes MCP server (stdio)."""

import argparse
import asyncio
import os
import threading
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from .backends import OllamaBackend
from .core import ROOT, run_tool

load_dotenv(Path.cwd() / ".env")
load_dotenv(ROOT / ".env")

mcp = FastMCP(
    "local-eyes",
    log_level="WARNING",
    instructions=(
        "Local Eyes lets you see images. Pass an absolute file path (or URL). "
        "Use read_ui for screenshots of apps and web pages, extract_text for exact text/OCR, "
        "describe_image for anything else or to ask a specific question about an image."
    ),
)

USE_CACHE = os.getenv("LOCAL_EYES_CACHE", "").lower() in ("1", "true", "yes")


@mcp.tool()
async def describe_image(path_or_url: str, question: Optional[str] = None) -> dict:
    """Describe an image, or answer a question about it. path_or_url: absolute local path or http(s) URL."""
    return await run_tool("describe_image", path_or_url, question, USE_CACHE)


@mcp.tool()
async def extract_text(path: str) -> dict:
    """OCR: return all visible text verbatim, plus any error/warning messages shown (great for UI screenshots)."""
    return await run_tool("extract_text", path, None, USE_CACHE)


@mcp.tool()
async def read_ui(path: str) -> dict:
    """Read a UI screenshot: structured elements (type, label, value, state), visible errors, and layout issues."""
    return await run_tool("read_ui", path, None, USE_CACHE)


def main():
    global USE_CACHE
    parser = argparse.ArgumentParser(description="Local Eyes MCP server")
    parser.add_argument("--backend", choices=["ollama", "gemini"], help="overrides LOCAL_EYES_BACKEND")
    parser.add_argument("--cache", action="store_true",
                        help="save good responses to cache/ and replay them (survives rate limits and no wifi)")
    args = parser.parse_args()
    if args.backend:
        os.environ["LOCAL_EYES_BACKEND"] = args.backend
    USE_CACHE = USE_CACHE or args.cache
    if os.getenv("LOCAL_EYES_BACKEND", "ollama") == "ollama":
        # Load the model in the background so the first tool call doesn't pay the load time
        threading.Thread(target=lambda: asyncio.run(OllamaBackend().warm_up()), daemon=True).start()
    mcp.run()


if __name__ == "__main__":
    main()
