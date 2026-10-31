# Local Eyes 👁️

**Private eyes for text-only AI agents.** Local Eyes is an MCP server that lets any agent or model *see* images, using **Gemma 4** running on your own machine (Ollama) or through the Gemini API.

Frontier models can already see. But many of the open models people run locally for coding and agents are text-only (gpt-oss, DeepSeek, Qwen-Coder), and private or offline setups can't send screenshots to a cloud model. Local Eyes plugs Gemma 4's vision into any MCP client as three tools that return strict JSON. A text-only agent can then read a broken UI, a stack-trace screenshot or a photo of a receipt, without the image ever leaving the laptop.

```
 text-only agent ──MCP──▶ Local Eyes ──▶ Gemma 4 (Ollama, on this machine)
 (gpt-oss, Qwen,          read_ui           └─ or gemma-4-31b-it on the Gemini API
  Claude, Cursor…)        extract_text
                          describe_image  ◀── validated JSON (Pydantic), 1 auto-retry
```

## Tools

| Tool | Input | Returns |
|---|---|---|
| `read_ui(path)` | UI screenshot | `screen_summary`, `elements[]` (type, label, value, state), `errors[]` (message, element, severity), `layout_issues[]` |
| `extract_text(path)` | any image | `text` (verbatim OCR, line breaks kept), `errors[]` (error/warning messages, verbatim), `language` |
| `describe_image(path_or_url, question?)` | path or URL | `answer`, `description`, `key_details[]`, `visible_text[]` |

Every result is validated against a Pydantic schema. If the model returns invalid JSON, Local Eyes retries once and sends back the exact validation error. On Ollama, the schema is also enforced while the model writes its answer (structured outputs). Each result carries `_meta` with the backend, model, latency, attempts and whether it came from the cache.

## Setup

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/Arcanum703/local-eyes && cd local-eyes
uv sync
cp .env.example .env        # pick a backend; add GEMINI_API_KEY if using gemini
```

**Private mode (Ollama, works offline):**

```bash
ollama pull gemma4:e4b
```

**Cloud mode (Gemini API):** set `LOCAL_EYES_BACKEND=gemini` and `GEMINI_API_KEY=...` (from [AI Studio](https://aistudio.google.com/apikey)) in `.env`. The default model is `gemma-4-31b-it`. If it returns 5xx or times out (common under load), Local Eyes falls back to `gemma-4-26b-a4b-it`.

**Speed:** on a CPU-only laptop, Gemma 4 E4B takes about 40–120 s per image. Gemma 4 thinks by default; Local Eyes turns that off for Ollama (`OLLAMA_THINK=1` turns it back on), which made it about 3x faster with the same answers on our demo images. A GPU makes it much faster.

Try it without an MCP client:

```bash
uv run local-eyes-cli read_ui demo/broken_form.png
```

## Connect to any MCP client

**Claude Code** (3 lines):

```bash
claude mcp add local-eyes -- uv --directory /path/to/local-eyes run local-eyes
```

**Claude Desktop / Cursor / any MCP client** (`mcpServers` entry):

```json
"local-eyes": {
  "command": "uv",
  "args": ["--directory", "/path/to/local-eyes", "run", "local-eyes"]
}
```

Add `"--backend", "gemini"` or `"--cache"` to the args to change behaviour, or set `LOCAL_EYES_BACKEND` in `.env`.

## Replay cache (`--cache`)

With `--cache`, every validated response is saved to `cache/<hash>.json`. The key is the image bytes + tool + question, so the backend doesn't matter. The next identical call is answered from disk instantly, with no model and no network. This keeps a live demo working through rate limits or dead conference Wi-Fi. Cached results show `"_meta": {"cached": true}`. Answers for the demo images ship in `cache/`.

## Demo: a text-only agent fixes a broken form

`scripts/agent_demo.py` is a ~80-line agent harness. Its "brain" is any Ollama model with tool calling, and it never receives image bytes, only Local Eyes' JSON:

```bash
uv run python scripts/agent_demo.py demo/broken_form.png "Why can't the user sign up? Propose a fix." --cache
# any tool-calling Ollama model can be the brain: AGENT_MODEL=gpt-oss:20b ...
```

The agent calls `read_ui`, learns about the invalid email, the mismatched passwords and the `422 date_of_birth expected YYYY-MM-DD` banner, then proposes the fix: `1998-10-31`, add `.com`, match the passwords, tick the Terms box. (The 31B/26B models on Gemini also spot the submit button hanging off the card; E4B misses it.) With Ollama it all works with Wi-Fi off.

Other demo images: `demo/stacktrace.png` (try `extract_text` on it).

`scripts/mcp_smoke.py <tool> <image> [--cache] [--backend gemini]` exercises the server exactly like an MCP client does.

## Configuration

| Env var | Default | |
|---|---|---|
| `LOCAL_EYES_BACKEND` | `ollama` | `ollama` or `gemini` |
| `OLLAMA_HOST` | `http://localhost:11434` | |
| `OLLAMA_MODEL` | `gemma4:e4b` | any Ollama vision model |
| `GEMINI_API_KEY` | | required for `gemini` |
| `GEMINI_MODEL` | `gemma-4-31b-it` | |
| `GEMINI_FALLBACK_MODEL` | `gemma-4-26b-a4b-it` | tried on 5xx / timeout |
| `GEMINI_TIMEOUT` | `90` | seconds per model attempt |
| `OLLAMA_THINK` | off | turn Gemma 4 thinking on |
| `LOCAL_EYES_CACHE` | off | `1` = same as `--cache` |
| `LOCAL_EYES_CACHE_DIR` | `./cache` | |
| `LOCAL_EYES_MAX_SIDE` | `1600` | images are downscaled to this before sending |
| `LOCAL_EYES_ROOT` | unset | if set, local paths must be inside this folder |
| `LOCAL_EYES_ALLOW_PRIVATE_URLS` | off | URLs to localhost/private networks are refused by default |

Only files that decode as images are ever sent to a model (25 MB / 50 MP caps).

## License

MIT. Built at MLH Hacktoberfest Hack Day Budapest, 31 Oct 2026.
