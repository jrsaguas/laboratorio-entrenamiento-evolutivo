"""Small runtime adapter for local Ollama experiments.

Timeout=0 at the experiment layer is represented as timeout=None here.
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
    thinking: str | None = None
    final_text: str = ""
    extraction: dict[str, Any] | None = None


def _extract_thinking_and_final(response_text: str) -> tuple[str | None, str, dict[str, Any]]:
    """Separate a Qwen/Ollama thinking section from the final response.

    The raw Ollama response is preserved unchanged. This function only
    determines which text should be exposed as ModelResponse.text for
    downstream evaluation.
    """
    text = response_text.strip()

    if not text:
        return None, "", {"method": "empty_response"}

    close_tag = "</think>"
    if close_tag in text:
        thinking_part, final_part = text.rsplit(close_tag, 1)
        thinking = thinking_part.strip()
        final = final_part.strip()
        return (
            thinking or None,
            final,
            {
                "method": "think_tag",
                "delimiter": close_tag,
                "has_final_text": bool(final),
            },
        )

    return None, text, {"method": "no_think_tag"}


def generate(
    prompt: str,
    *,
    endpoint: str = "http://127.0.0.1:11434/api/generate",
    model: str,
    temperature: float = 0.0,
    max_tokens: int = -1,
    timeout: float | None = None,
    think: bool = False,
    seed: int | None = None,
) -> ModelResponse:
    options: dict[str, Any] = {
        "temperature": temperature,
        "num_predict": max_tokens,
    }
    if seed is not None:
        options["seed"] = seed
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "think": think,
        "options": options,
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = json.loads(response.read().decode("utf-8"))

    raw_response = raw.get("response", "")
    if not isinstance(raw_response, str):
        raw_response = str(raw_response)

    thinking, final_text, extraction = _extract_thinking_and_final(raw_response)

    return ModelResponse(
        text=final_text,
        raw=raw,
        model=raw.get("model", model),
        thinking=thinking,
        final_text=final_text,
        extraction=extraction,
    )


def health(endpoint: str = "http://127.0.0.1:11434/api/tags", timeout: float = 10) -> dict[str, Any]:
    """Return Ollama model inventory or raise a useful connection error."""
    with urllib.request.urlopen(endpoint, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))
