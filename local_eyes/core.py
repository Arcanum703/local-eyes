"""Load an image, ask Gemma 4 for JSON, validate it, retry once, cache it."""

import hashlib
import io
import json
import os
import re
import time
from pathlib import Path

import httpx
from PIL import Image
from pydantic import BaseModel, ValidationError

from .backends import get_backend
from .schemas import DescribeResult, ExtractTextResult, ReadUiResult

ROOT = Path(__file__).resolve().parent.parent
MAX_SIDE = int(os.getenv("LOCAL_EYES_MAX_SIDE", "1600"))

PROMPTS = {
    "describe_image": (
        DescribeResult,
        "Look at the image carefully. {question_line}"
        "Describe only what is actually visible; do not guess what is outside the frame.",
    ),
    "extract_text": (
        ExtractTextResult,
        "Transcribe ALL text visible in the image exactly as written, in reading order. "
        "Keep original spelling, numbers, punctuation and line breaks. Do not translate or summarise. "
        "Also list separately, verbatim, every error, warning or validation message you can see.",
    ),
    "read_ui": (
        ReadUiResult,
        "This is a screenshot of a user interface. Act as a careful QA tester. "
        "List the interactive and text elements with their labels, current values and states. "
        "List every visible error, warning or validation message verbatim and which field it belongs to. "
        "List layout problems such as overlapping, cut-off, misaligned or unreadable elements. "
        "Report only what is visible.",
    ),
}


class Cache:
    """Content-addressed cache: same tool + same image bytes + same question -> same answer."""

    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.dir = Path(os.getenv("LOCAL_EYES_CACHE_DIR", ROOT / "cache"))

    def key(self, tool: str, image: bytes, question: str | None) -> str:
        h = hashlib.sha256(image)
        h.update(f"|{tool}|{question or ''}".encode())
        return h.hexdigest()[:24]

    def get(self, key: str) -> dict | None:
        p = self.dir / f"{key}.json"
        if self.enabled and p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return None

    def put(self, key: str, value: dict) -> None:
        if self.enabled:
            self.dir.mkdir(parents=True, exist_ok=True)
            (self.dir / f"{key}.json").write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def load_image(path_or_url: str) -> bytes:
    if path_or_url.startswith(("http://", "https://")):
        r = httpx.get(path_or_url, timeout=30, follow_redirects=True)
        r.raise_for_status()
        return r.content
    p = Path(path_or_url).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"No image at {p.resolve()}")
    return p.read_bytes()


def to_png(raw: bytes) -> bytes:
    """Normalise any image to RGB PNG, downscaled so small models stay fast."""
    img = Image.open(io.BytesIO(raw))
    img = img.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def parse_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    if not text.startswith("{"):
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            text = text[start:end + 1]
    return json.loads(text)


def build_prompt(tool: str, question: str | None) -> tuple[type[BaseModel], str, dict]:
    model, instructions = PROMPTS[tool]
    question_line = f"Answer this question about it: {question}\n" if question else ""
    schema = model.model_json_schema()
    prompt = (
        instructions.format(question_line=question_line)
        + "\n\nRespond with ONLY a JSON object matching this JSON schema, no prose, no markdown:\n"
        + json.dumps(schema)
    )
    return model, prompt, schema


async def run_tool(tool: str, path_or_url: str, question: str | None = None,
                   use_cache: bool = False, backend_name: str | None = None) -> dict:
    raw = load_image(path_or_url)
    cache = Cache(use_cache)
    key = cache.key(tool, raw, question)
    hit = cache.get(key)
    if hit:
        hit["_meta"] = {**hit.get("_meta", {}), "cached": True}
        return hit

    backend = get_backend(backend_name)
    model, prompt, schema = build_prompt(tool, question)
    png = to_png(raw)
    started = time.perf_counter()

    text = await backend.generate(prompt, png, schema)
    attempts = 1
    try:
        result = model.model_validate(parse_json(text))
    except (json.JSONDecodeError, ValidationError) as err:
        # One retry, telling the model exactly what was wrong
        attempts = 2
        retry_prompt = (
            f"{prompt}\n\nYour previous answer was invalid.\nError: {str(err)[:1500]}\n"
            f"Previous answer: {text[:2000]}\nReturn ONLY the corrected JSON object."
        )
        text = await backend.generate(retry_prompt, png, schema)
        result = model.model_validate(parse_json(text))

    out = result.model_dump()
    out["_meta"] = {
        "backend": backend.name,
        "model": backend.model,
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "attempts": attempts,
        "cached": False,
    }
    cache.put(key, out)
    return out
