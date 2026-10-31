"""A tiny text-only agent that borrows eyes from Local Eyes over MCP.

The "brain" is any Ollama model with tool calling (gpt-oss, qwen, ...). It never receives
image bytes: it only sees the JSON that Local Eyes returns.

    uv run python scripts/agent_demo.py demo/broken_form.png "Why can't the user sign up? Propose a fix."
    AGENT_MODEL=gpt-oss:20b uv run python scripts/agent_demo.py ... --cache
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from local_eyes.backends import OLLAMA_KEEP_ALIVE, OLLAMA_OPTIONS

OLLAMA = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
AGENT_MODEL = os.getenv("AGENT_MODEL", "gemma4:e4b")

GREY, CYAN, GREEN, RESET = "\033[90m", "\033[96m", "\033[92m", "\033[0m"


async def chat(messages, tools):
    """Stream the reply so the answer appears word by word; collect any tool calls."""
    content, calls = "", []
    async with httpx.AsyncClient(timeout=600) as client:
        async with client.stream("POST", f"{OLLAMA}/api/chat", json={
            "model": AGENT_MODEL, "messages": messages, "tools": tools, "stream": True,
            "options": OLLAMA_OPTIONS, "keep_alive": OLLAMA_KEEP_ALIVE, "think": False,
        }) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line:
                    continue
                msg = json.loads(line).get("message", {})
                calls += msg.get("tool_calls") or []
                if msg.get("content"):
                    if not content:
                        print(GREEN, end="")
                    content += msg["content"]
                    print(msg["content"], end="", flush=True)
    if content:
        print(RESET)
    return {"role": "assistant", "content": content, "tool_calls": calls}


def compact(text):
    """Drop nulls/empties and whitespace so a CPU-bound brain reads fewer tokens."""
    def clean(x):
        if isinstance(x, dict):
            return {k: clean(v) for k, v in x.items() if v not in (None, [], "") and k != "_meta"}
        if isinstance(x, list):
            return [clean(v) for v in x]
        return x
    try:
        return json.dumps(clean(json.loads(text)), separators=(",", ":"), ensure_ascii=False)
    except json.JSONDecodeError:
        return text


async def main():
    sys.stdout.reconfigure(encoding="utf-8")
    image, task, *flags = sys.argv[1:]
    image = str(Path(image).resolve())
    server = StdioServerParameters(command=sys.executable, args=["-m", "local_eyes.server", *flags])
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = (await session.list_tools()).tools
            tools = [{"type": "function", "function": {
                "name": t.name, "description": t.description, "parameters": t.inputSchema}} for t in listed]

            messages = [
                {"role": "system", "content": "You are a coding agent. You cannot see images yourself; "
                 "use the Local Eyes tools to look at them, then answer concisely with a concrete fix."},
                {"role": "user", "content": f"{task}\nScreenshot: {image}"},
            ]
            print(f"{GREY}agent brain: {AGENT_MODEL} (text only)  |  eyes: Local Eyes MCP{RESET}\n")
            for _ in range(5):
                msg = await chat(messages, tools)
                messages.append(msg)
                calls = msg.get("tool_calls") or []
                if not calls:
                    print()
                    return
                for call in calls:
                    name, args = call["function"]["name"], call["function"]["arguments"]
                    print(f"{CYAN}-> {name}({json.dumps(args)}){RESET}")
                    result = await session.call_tool(name, args)
                    raw = result.content[0].text
                    text = compact(raw)
                    meta = {} if result.isError else json.loads(raw).get("_meta", {})
                    print(f"{GREY}{text}")
                    took = "replayed from cache" if meta.get("cached") else f"{meta.get('latency_ms')} ms"
                    print(f"[eyes: {meta.get('backend')} / {meta.get('model')}, {took}]{RESET}\n")
                    messages.append({"role": "tool", "tool_name": name, "content": text})


asyncio.run(main())
