"""Metrics used by EXP-0001."""

from __future__ import annotations

from typing import Any


def exact_match(predicted: str, expected: str) -> bool:
    return predicted.strip() == expected.strip()


def contains_expected(predicted: str, expected: str) -> bool:
    return expected.strip() in predicted


def _runtime_tokens(runtime: dict[str, Any] | None) -> int:
    if not runtime:
        return 0
    if isinstance(runtime.get("eval_count"), (int, float)):
        return int(runtime["eval_count"])
    return sum(
        _runtime_tokens(value)
        for value in runtime.values()
        if isinstance(value, dict)
    )


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    valid = [row for row in results if not row.get("error")]
    verified_rows = [
        row for row in results
        if row.get("condition") != "baseline" and not row.get("error")
    ]

    statuses: dict[str, int] = {}
    for row in results:
        for key in ("verification", "oracle_verification"):
            verification = row.get(key) or {}
            status = (verification.get("metadata") or {}).get("status")
            if status:
                statuses[status] = statuses.get(status, 0) + 1

    exact = sum(bool(r.get("exact_match")) for r in valid)
    contains = sum(bool(r.get("contains_expected")) for r in valid)
    semantic = sum(bool(r.get("semantic_correct")) for r in valid)
    verification_success = sum(bool(r.get("verification_success")) for r in valid)
    initial_verification_success = sum(
        bool(r.get("first_verification_success")) for r in valid
    )
    detected_errors = sum(
        not bool(r.get("first_verification_success"))
        for r in verified_rows
    )
    repair_attempts = sum(bool(r.get("repair_attempted")) for r in valid)
    repair_successes = sum(
        bool(r.get("repair_attempted")) and bool(r.get("verification_success"))
        for r in valid
    )
    false_rejections = sum(
        bool(r.get("semantic_correct"))
        and not bool(r.get("first_verification_success"))
        for r in verified_rows
    )
    tokens = sum(_runtime_tokens(r.get("runtime")) for r in valid)
    latency_ms = sum(
        r.get("latency_ms", 0)
        for r in valid
        if isinstance(r.get("latency_ms"), (int, float))
    )
    verification_latency_ms = sum(
        r.get("verification_latency_ms", 0)
        for r in valid
        if isinstance(r.get("verification_latency_ms"), (int, float))
    )

    return {
        "total": total,
        "valid": len(valid),
        "errors": total - len(valid),
        "exact_match": exact,
        "exact_accuracy": exact / len(valid) if valid else None,
        "contains_expected": contains,
        "contains_expected_accuracy": contains / len(valid) if valid else None,
        "semantic_correct": semantic,
        "semantic_accuracy": semantic / len(valid) if valid else None,
        "verification_success": verification_success,
        "verification_success_rate": verification_success / len(valid) if valid else None,
        "initial_verification_success": initial_verification_success,
        "initial_verification_success_rate": (
            initial_verification_success / len(valid) if valid else None
        ),
        "detected_errors": detected_errors,
        "detection_rate": detected_errors / len(verified_rows) if verified_rows else None,
        "repair_attempts": repair_attempts,
        "repair_successes": repair_successes,
        "repair_success_rate": (
            repair_successes / repair_attempts if repair_attempts else None
        ),
        "verifier_false_rejection": false_rejections,
        "tokens": tokens,
        "average_tokens": round(tokens / len(valid), 3) if valid else None,
        "latency_ms": round(latency_ms, 3),
        "average_latency_ms": round(latency_ms / len(valid), 3) if valid else None,
        "verification_latency_ms": round(verification_latency_ms, 3),
        "average_verification_latency_ms": (
            round(verification_latency_ms / len(valid), 3) if valid else None
        ),
        "verification_unsupported": statuses.get("unsupported_format", 0),
        "verification_parser_errors": statuses.get("parser_or_verification_error", 0),
        "verification_missing_reference": statuses.get("missing_reference", 0),
        "verification_verified_difference": statuses.get("verified_difference", 0),
    }
