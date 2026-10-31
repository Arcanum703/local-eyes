"""Talk to Local Eyes the way any MCP client does: spawn it over stdio, list tools, call one.

    uv run python scripts/mcp_smoke.py read_ui demo/broken_form.png [--cache] [--backend gemini]
"""

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    tool, image, *flags = sys.argv[1:] or ["read_ui", "demo/broken_form.png"]
    server = StdioServerParameters(command=sys.executable, args=["-m", "local_eyes.server", *flags])
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("tools:", [t.name for t in tools.tools], file=sys.stderr)
            arg = "path_or_url" if tool == "describe_image" else "path"
            result = await session.call_tool(tool, {arg: str(Path(image).resolve())})
            if result.isError:
                sys.exit("tool error: " + result.content[0].text)
            payload = result.structuredContent or json.loads(result.content[0].text)
            sys.stdout.reconfigure(encoding="utf-8")
            print(json.dumps(payload, indent=2, ensure_ascii=False))


asyncio.run(main())
