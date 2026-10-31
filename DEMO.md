# Local Eyes: 2-minute demo script

**Measured on this laptop (CPU only, no GPU, Gemma 4 E4B on Ollama, thinking off):**
- `read_ui` live: 55–120 s. `extract_text` live: about 40–110 s. The range depends on what else is using the CPU.
- Agent demo with eyes replayed from `cache/` and the text brain live: about 40 s, streaming.
- Gemini API (`gemma-4-31b-it`, which falls back to `gemma-4-26b-a4b-it` when 31B is overloaded): 15–70 s.

So the stage plan is: **the eyes replay from cache, the brain runs live, Wi-Fi off.** The cached answers were produced by local Gemma 4 on this laptop (`_meta.backend = ollama`). Say so if asked. One real live vision call runs in a second terminal during the pitch.

**Setup before going on stage**
- Two terminals at `local-eyes/`, large font. Close Chrome and other CPU-heavy apps. Stop the kassza demo if it isn't needed.
- Warm the model: `ollama run gemma4:e4b "hi"` (the first load takes about 30 s or more).
- Check the cache is there: `ls cache` shows 2 files.
- Have `demo/broken_form.png` open in an image viewer.
- Backup: the recorded video of this exact run.

---

**0:00–0:30, the wow moment**

> "This agent's brain is a text-only model. It has never seen a pixel. And my Wi-Fi is off."

*Turn Wi-Fi off, show the tray icon. In terminal 1:*

```bash
uv run python scripts/agent_demo.py demo/broken_form.png "Why can't the user sign up? Propose a fix." --cache
```

*Point at the output:* the cyan line shows the agent calling `read_ui`, then the grey line shows Local Eyes' JSON: three errors, each tied to its field. Then the green answer streams in: fix the date to `1998-10-31`, add `.com` to the email, match the passwords, tick the Terms box.

> "A text-only agent just debugged a UI from a screenshot, privately and offline."

**0:30–1:00, what it is, while a live call runs**

*In terminal 2, start a real uncached vision call and talk over it:*

```bash
uv run local-eyes-cli extract_text demo/stacktrace.png
```

> "Local Eyes is an MCP server: three tools, `read_ui`, `extract_text` and `describe_image`. They return strict JSON validated with Pydantic, and invalid output gets one retry with the error fed back. Any MCP client can use it: Claude Code, Cursor, or your own harness like this one. It's three lines of config."

*Show the `claude mcp add` snippet in the README.*

**1:00–1:30, why it matters**

> "Frontier models already see. But the open models people run locally, like gpt-oss, DeepSeek and Qwen-Coder, are text-only, and private setups can't upload screenshots of internal apps to a cloud. Local Eyes gives them eyes with Gemma 4 E4B on Ollama, on a laptop with no GPU."

*When terminal 2 finishes:* "And that was live: exact text from a terminal screenshot, `KeyError: 'HACK25'`, verbatim, ready for an agent to grep."

**1:30–2:00, same tools, bigger brain, and it's open**

> "One env var switches to Gemma 4 31B on the Gemini API when you want more accuracy. The replay cache keeps demos and CI deterministic. It's all MIT on GitHub: Arcanum703/local-eyes. Give your local models eyes."

---

**If things break**
- Terminal 2 is too slow: skip it and say "live calls take about a minute on CPU; here's the recorded one", then run it with `--cache`.
- Ollama down: the agent's brain needs Ollama, so play the backup video.
- Everything down: play the backup video.
