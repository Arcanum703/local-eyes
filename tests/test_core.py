"""Offline tests: JSON parsing, validation retry, and the replay cache (no model needed)."""

import asyncio

from local_eyes import core


class FakeBackend:
    name, model = "fake", "fake-1"

    def __init__(self, replies):
        self.replies, self.prompts = list(replies), []

    async def generate(self, prompt, image_png, schema):
        self.prompts.append(prompt)
        return self.replies.pop(0)


GOOD = '{"text": "KeyError: \'HACK25\'", "errors": ["KeyError: \'HACK25\'"], "language": "en"}'


def test_parse_json_strips_fences_and_prose():
    assert core.parse_json('Sure!\n```json\n{"a": 1}\n```') == {"a": 1}
    assert core.parse_json('here you go {"a": 2} done') == {"a": 2}


def test_retry_once_with_validation_error(monkeypatch, tmp_path):
    fake = FakeBackend(['{"errors": "not a list"}', GOOD])
    monkeypatch.setattr(core, "get_backend", lambda name=None: fake)
    monkeypatch.setenv("LOCAL_EYES_CACHE_DIR", str(tmp_path))
    out = asyncio.run(core.run_tool("extract_text", "demo/stacktrace.png"))
    assert out["errors"] == ["KeyError: 'HACK25'"]
    assert out["_meta"]["attempts"] == 2
    assert "previous answer was invalid" in fake.prompts[1]


def test_cache_replays_without_backend(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCAL_EYES_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(core, "get_backend", lambda name=None: FakeBackend([GOOD]))
    asyncio.run(core.run_tool("extract_text", "demo/stacktrace.png", use_cache=True))

    def boom(name=None):
        raise AssertionError("backend must not be called on a cache hit")

    monkeypatch.setattr(core, "get_backend", boom)
    out = asyncio.run(core.run_tool("extract_text", "demo/stacktrace.png", use_cache=True))
    assert out["_meta"]["cached"] is True
