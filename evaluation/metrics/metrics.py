"""Metrics used by EXP-0001.

The summary is intentionally condition-aware: verification metrics are only
meaningful for the verified condition, while generation metrics are available
for both conditions.
"""

from __future__ import annotations

from typing import Any


def exact_match(predicted: str, expected: str) -> bool:
    return predicted.strip() == expected.strip()


def contains_expected(predicted: str, expected: str) -> bool:
    return expected.strip() in predicted


def _runtime_tokens(row: dict[str, Any]) -> int:
    runtime = row.get("runtime") or {}
    total = runtime.get("eval_count") or 0
    repair = runtime.get("repair") or {}
    total += repair.get("eval_count") or 0
    return int(total) if isinstance(total, (int, float)) else 0


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    valid = [row for row in results if not row.get("error")]
    statuses: dict[str, int] = {}
    for row in results:
        verification = row.get("verification") or {}
        status = (verification.get("metadata") or {}).get("status")
        if status:
            statuses[status] = statuses.get(status, 0) + 1

    exact = sum(bool(r.get("exact_match")) for r in results)
    contains = sum(bool(r.get("contains_expected")) for r in results)
    verification_success = sum(bool(r.get("verification_success")) for r in results)
    initial_verification_success = sum(bool(r.get("first_verification_success")) for r in results)
    verified_rows = [
        row for row in results
        if row.get("condition") != "baseline" and not row.get("error")
    ]
    detected_errors = sum(
        not bool(r.get("first_verification_success")) for r in verified_rows
    )
    repair_attempts = sum(bool(r.get("repair_attempted")) for r in results)
    repair_successes = sum(
        bool(r.get("repair_attempted")) and bool(r.get("verification_success"))
        for r in results
    )
    false_positives = sum(
        bool(r.get("exact_match")) and not bool(r.get("first_verification_success"))
        for r in verified_rows
    )
    tokens = sum(_runtime_tokens(r) for r in results)
    latency_ms = sum(
        r.get("latency_ms", 0)
        for r in results
        if isinstance(r.get("latency_ms"), (int, float))
    )

    return {
        "total": total,
        "valid": len(valid),
        "errors": total - len(valid),
        "exact_match": exact,
        "exact_accuracy": exact / len(valid) if valid else None,
        "contains_expected": contains,
        "contains_expected_accuracy": contains / len(valid) if valid else None,
        "verification_success": verification_success,
        "verification_success_rate": verification_success / len(valid) if valid else None,
        "initial_verification_success": initial_verification_success,
        "initial_verification_success_rate": initial_verification_success / len(valid) if valid else None,
        "detected_errors": detected_errors,
        "detection_rate": detected_errors / len(verified_rows) if verified_rows else None,
        "repair_attempts": repair_attempts,
        "repair_successes": repair_successes,
        "repair_success_rate": repair_successes / repair_attempts if repair_attempts else None,
        "verifier_false_positive": false_positives,
        "tokens": tokens,
        "latency_ms": round(latency_ms, 3),
        "average_latency_ms": round(latency_ms / len(valid), 3) if valid else None,
        "average_tokens": round(tokens / len(valid), 3) if valid else None,
        "verification_unsupported": statuses.get("unsupported_format", 0),
        "verification_parser_errors": statuses.get("parser_or_verification_error", 0),
        "verification_missing_reference": statuses.get("missing_reference", 0),
        "verification_verified_difference": statuses.get("verified_difference", 0),
    }
