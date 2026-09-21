"""Small runtime adapter for local Ollama experiments.

The laboratory uses Ollama's native /api/generate endpoint by default.
Timeout=0 means no client-side timeout.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelResponse:
    text: str
    raw: dict[str, Any]
    model: str


def generate(
    prompt: str,
    *,
    endpoint: str = "http://127.0.0.1:11434/api/generate",
    model: str,
    temperature: float = 0.0,
    max_tokens: int = 512,
    timeout: float | None = 120,
    think: bool = False,
) -> ModelResponse:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "think": think,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    # None disables urllib's client-side timeout.
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = json.loads(response.read().decode("utf-8"))

    return ModelResponse(
        text=raw.get("response", ""),
        raw=raw,
        model=raw.get("model", model),
    )


def health(endpoint: str = "http://127.0.0.1:11434/api/tags", timeout: float = 10) -> dict[str, Any]:
    """Return Ollama model inventory or raise a useful connection error."""
    with urllib.request.urlopen(endpoint, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))
