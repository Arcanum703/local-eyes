"""Run a Local Eyes tool from the terminal, without an MCP client.

    local-eyes-cli read_ui demo/broken_form.png --backend ollama --cache
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from .core import ROOT, run_tool


def main():
    load_dotenv(Path.cwd() / ".env")
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Local Eyes CLI")
    parser.add_argument("tool", choices=["describe_image", "extract_text", "read_ui"])
    parser.add_argument("image", help="path or URL")
    parser.add_argument("question", nargs="?", help="question for describe_image")
    parser.add_argument("--backend", choices=["ollama", "gemini"])
    parser.add_argument("--cache", action="store_true")
    args = parser.parse_args()
    out = asyncio.run(run_tool(args.tool, args.image, args.question, args.cache, args.backend))
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
