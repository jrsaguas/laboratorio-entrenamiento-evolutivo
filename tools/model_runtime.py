"""Minimal model-runtime abstraction for reproducible laboratory experiments.

The first implementation supports an OpenAI-compatible HTTP endpoint. This keeps
the experiment independent from a particular local serving stack (Ollama,
llama.cpp, vLLM, etc.). A later adapter can target a native API without
changing the experiment runner.
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
    endpoint: str,
    model: str,
    temperature: float = 0.0,
    max_tokens: int = 512,
    timeout: int = 120,
) -> ModelResponse:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = json.loads(response.read().decode("utf-8"))

    text = raw["choices"][0]["message"]["content"]
    return ModelResponse(text=text, raw=raw, model=model)
