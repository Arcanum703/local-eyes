"""Vision backends: Gemma 4 on Ollama (local) or on the Gemini API."""

import base64
import os

import httpx


class BackendError(RuntimeError):
    pass


class OllamaBackend:
    name = "ollama"

    def __init__(self):
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", "gemma4:e4b")

    async def generate(self, prompt: str, image_png: bytes, schema: dict) -> str:
        body = {
            "model": self.model,
            "messages": [{
                "role": "user",
                "content": prompt,
                "images": [base64.b64encode(image_png).decode()],
            }],
            "format": schema,  # constrained decoding to the JSON schema
            "stream": False,
            "options": {"temperature": 0},
        }
        try:
            async with httpx.AsyncClient(timeout=600) as client:
                r = await client.post(f"{self.host}/api/chat", json=body)
        except httpx.ConnectError as e:
            raise BackendError(f"Cannot reach Ollama at {self.host}. Is it running? ({e})") from e
        if r.status_code == 404:
            raise BackendError(f"Model {self.model} is not in Ollama yet. Run: ollama pull {self.model}")
        if r.status_code != 200:
            raise BackendError(f"Ollama {r.status_code}: {r.text[:500]}")
        return r.json()["message"]["content"]


class GeminiBackend:
    name = "gemini"
    url = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self):
        self.key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model = os.getenv("GEMINI_MODEL", "gemma-4-31b-it")
        self.json_mode = True  # switched off if the model rejects JSON mode
        if not self.key:
            raise BackendError("GEMINI_API_KEY is not set. Put it in local-eyes/.env")

    async def generate(self, prompt: str, image_png: bytes, schema: dict) -> str:
        body = {
            "contents": [{
                "role": "user",
                "parts": [
                    {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(image_png).decode()}},
                    {"text": prompt},
                ],
            }],
            "generationConfig": {"temperature": 0},
        }
        if self.json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"
        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(self.url.format(model=self.model), json=body,
                                  headers={"x-goog-api-key": self.key})
            if r.status_code == 400 and self.json_mode and "json" in r.text.lower():
                self.json_mode = False
                return await self.generate(prompt, image_png, schema)
        if r.status_code != 200:
            raise BackendError(f"Gemini {r.status_code}: {r.text[:500]}")
        data = r.json()
        try:
            parts = data["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError) as e:
            raise BackendError(f"Gemini returned no content: {str(data)[:500]}") from e
        # Skip thought parts if the model emits any
        return "".join(p.get("text", "") for p in parts if not p.get("thought"))


def get_backend(name: str | None = None):
    name = (name or os.getenv("LOCAL_EYES_BACKEND", "ollama")).lower()
    if name == "ollama":
        return OllamaBackend()
    if name == "gemini":
        return GeminiBackend()
    raise BackendError(f"Unknown backend {name!r}; use 'ollama' or 'gemini'")
