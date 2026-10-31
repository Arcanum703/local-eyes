# Local Eyes: 2-minute demo script

**Setup before going on stage**
- Terminal at `local-eyes/`, font size large, Windows Terminal dark theme.
- `ollama run gemma4:e4b ""` once beforehand so the model is already loaded (the first load is slow).
- Warm the cache: run the agent command below once with `--cache`, so a replay is ready if anything breaks.
- `demo/broken_form.png` open in an image viewer, next to the terminal.
- Backup: the recorded video of this exact run.

---

**0:00–0:30, the wow moment**

> "This agent's brain is a text-only model. It has never seen a pixel. And my Wi-Fi is off."

*Turn Wi-Fi off on screen (show the tray icon). Run:*

```bash
uv run python scripts/agent_demo.py demo/broken_form.png "Why can't the user sign up? Propose a fix."
```

*While it runs:* "It's calling `read_ui` on Local Eyes, my MCP server. Gemma 4 is looking at the screenshot right here on this laptop."

*Point at the output:* the `read_ui` JSON lists the bad email, the mismatched passwords, the 422 date-format banner and the button hanging off the card. Then the agent's fix appears in green.

> "A text-only agent just debugged a UI from a screenshot, privately and offline."

**0:30–1:00, what it is**

> "Local Eyes is an MCP server: three tools, `read_ui`, `extract_text` and `describe_image`. They return strict JSON validated with Pydantic, and invalid output gets one retry with the error fed back. Any MCP client can use it: Claude Code, Cursor, or your own harness like this one."

*Show the 3-line `claude mcp add` snippet in the README.*

**1:00–1:30, why it matters**

> "Frontier models already see. But the open models people run locally, like gpt-oss, DeepSeek and Qwen-Coder, are text-only, and private setups can't upload screenshots of internal apps to a cloud. Local Eyes gives them eyes with Gemma 4 E4B, running locally on Ollama."

*Run OCR quickly:*

```bash
uv run local-eyes-cli extract_text demo/stacktrace.png --cache
```

> "Exact text from a terminal screenshot, `KeyError: 'HACK25'`, verbatim, ready for the agent to grep."

**1:30–2:00, same tools, bigger brain, and it's open**

> "One env var switches to Gemma 4 31B on the Gemini API when you want more accuracy. A replay cache keeps demos and CI deterministic. It's all MIT on GitHub: Arcanum703/local-eyes. Give your local models eyes."

---

**If things break**
- Model slow or Wi-Fi dead: add `--cache` to the command (the answers are already recorded).
- Ollama down: `--backend gemini` (needs Wi-Fi), or `--cache`.
- Everything down: play the backup video.
