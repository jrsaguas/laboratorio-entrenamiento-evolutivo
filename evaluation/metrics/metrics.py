"""Metrics used by EXP-0001."""

from __future__ import annotations

from typing import Any


def exact_match(predicted: str, expected: str) -> bool:
    return predicted.strip() == expected.strip()


def contains_expected(predicted: str, expected: str) -> bool:
    return expected.strip() in predicted


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    statuses: dict[str, int] = {}
    for row in results:
        verification = row.get("verification") or {}
        status = (verification.get("metadata") or {}).get("status")
        if status:
            statuses[status] = statuses.get(status, 0) + 1

    return {
        "total": total,
        "exact_match": sum(bool(r.get("exact_match")) for r in results),
        "contains_expected": sum(bool(r.get("contains_expected")) for r in results),
        "verification_success": sum(bool(r.get("verification_success")) for r in results),
        "verification_unsupported": statuses.get("unsupported_format", 0),
        "verification_parser_errors": statuses.get("parser_or_verification_error", 0),
        "errors": sum(bool(r.get("error")) for r in results),
    }
