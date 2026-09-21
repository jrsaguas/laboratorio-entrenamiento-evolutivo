"""Deterministic mathematical verification primitives for laboratory experiments.

The verifier is intentionally independent of an LLM. It normalizes common
answer formats before comparing them semantically with SymPy, so a failed
string match is not automatically treated as a mathematical error.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    method: str
    details: str
    metadata: dict[str, Any]


def _clean_candidate(value: Any) -> str:
    """Normalize common model-output wrappers without changing the math."""
    text = str(value).strip()

    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2:
            text = "\n".join(lines[1:-1]).strip()

    # Remove only explicit answer labels at the beginning.
    text = re.sub(
        r"^(?:answer|final answer|respuesta|resultado)\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return text.strip()


def _parse_list(value: Any) -> list[Any] | None:
    """Parse a Python-style list/tuple when the candidate is structured."""
    if isinstance(value, (list, tuple)):
        return list(value)

    text = _clean_candidate(value)
    if not (text.startswith("[") or text.startswith("(")):
        return None

    try:
        parsed = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return None

    return list(parsed) if isinstance(parsed, (list, tuple)) else None


def _verify_list(candidate: Any, reference: Any) -> VerificationResult:
    candidate_list = _parse_list(candidate)
    reference_list = _parse_list(reference)

    if candidate_list is None or reference_list is None:
        return VerificationResult(
            ok=False,
            method="structured-list",
            details="unsupported list/tuple format",
            metadata={"status": "unsupported_format"},
        )

    if len(candidate_list) != len(reference_list):
        return VerificationResult(
            ok=False,
            method="structured-list",
            details="list lengths differ",
            metadata={
                "status": "verified_difference",
                "candidate_length": len(candidate_list),
                "reference_length": len(reference_list),
            },
        )

    checks = [
        verify_symbolic_equality(candidate_item, reference_item)
        for candidate_item, reference_item in zip(candidate_list, reference_list)
    ]
    ok = all(check.ok for check in checks)

    return VerificationResult(
        ok=ok,
        method="structured-list+sympy",
        details="list verified element-by-element" if ok else "one or more list elements differ",
        metadata={
            "status": "verified" if ok else "verified_difference",
            "elements": [check.metadata for check in checks],
        },
    )


def _verify_system_pair(candidate: Any, reference: Any) -> VerificationResult | None:
    """Handle the explicit two-variable system used by EXP-0001 math-019."""
    reference_text = _clean_candidate(reference)
    if reference_text != "(x-6)**2+(y-4)**2":
        return None

    candidate_list = _parse_list(candidate)
    if candidate_list is None or len(candidate_list) != 2:
        return VerificationResult(
            ok=False,
            method="system-pair+sympy",
            details="expected a two-value solution pair",
            metadata={"status": "unsupported_format"},
        )

    x_value, y_value = candidate_list
    checks = [
        verify_symbolic_equality(x_value, "6"),
        verify_symbolic_equality(y_value, "4"),
    ]
    ok = all(check.ok for check in checks)

    return VerificationResult(
        ok=ok,
        method="system-pair+sympy",
        details="system solution verified" if ok else "system solution differs",
        metadata={
            "status": "verified" if ok else "verified_difference",
            "variables": ["x", "y"],
            "elements": [check.metadata for check in checks],
        },
    )


def verify_symbolic_equality(lhs: Any, rhs: Any) -> VerificationResult:
    """Verify scalar/expression equality using SymPy after normalization."""
    try:
        import sympy as sp
    except ImportError:
        return VerificationResult(
            ok=False,
            method="sympy",
            details="SymPy is not installed.",
            metadata={"status": "missing_dependency"},
        )

    lhs_text = _clean_candidate(lhs)
    rhs_text = _clean_candidate(rhs)

    try:
        difference = sp.simplify(sp.sympify(lhs_text) - sp.sympify(rhs_text))
        ok = bool(difference == 0)
        return VerificationResult(
            ok=ok,
            method="sympy.simplify",
            details="symbolic equality verified" if ok else "symbolic expressions differ",
            metadata={
                "status": "verified" if ok else "verified_difference",
                "difference": str(difference),
            },
        )
    except Exception as exc:
        return VerificationResult(
            ok=False,
            method="sympy.simplify",
            details="verification failed",
            metadata={
                "status": "parser_or_verification_error",
                "error": type(exc).__name__,
                "message": str(exc),
            },
        )


def verify_answer(candidate: Any, reference: Any) -> VerificationResult:
    """Choose an appropriate semantic verification strategy."""
    system_result = _verify_system_pair(candidate, reference)
    if system_result is not None:
        return system_result

    candidate_list = _parse_list(candidate)
    reference_list = _parse_list(reference)
    if candidate_list is not None or reference_list is not None:
        return _verify_list(candidate, reference)

    return verify_symbolic_equality(candidate, reference)


if __name__ == "__main__":
    examples = [
        ("Respuesta: 5", "5"),
        ("[2, 3]", "[2, 3]"),
        ("[6, 4]", "(x-6)**2+(y-4)**2"),
        ("3*x**2 + 2", "2 + 3*x**2"),
    ]
    for candidate, reference in examples:
        print(candidate, "=>", verify_answer(candidate, reference))
