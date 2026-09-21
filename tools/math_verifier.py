"""Deterministic mathematical verification primitives for laboratory experiments.

The verifier is independent of an LLM. It normalizes common answer formats
before comparing them semantically with SymPy. Structured verification specs
keep task-specific semantics in the dataset instead of hard-coding task IDs.
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
    fence = chr(96) * 3
    if text.startswith(fence) and text.endswith(fence):
        lines = text.splitlines()
        if len(lines) >= 2:
            text = "\n".join(lines[1:-1]).strip()

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
        return VerificationResult(False, "structured-list", "unsupported list/tuple format", {"status": "unsupported_format"})

    if len(candidate_list) != len(reference_list):
        return VerificationResult(
            False, "structured-list", "list lengths differ",
            {"status": "verified_difference", "candidate_length": len(candidate_list), "reference_length": len(reference_list)},
        )

    checks = [verify_symbolic_equality(a, b) for a, b in zip(candidate_list, reference_list)]
    ok = all(check.ok for check in checks)
    return VerificationResult(
        ok,
        "structured-list+sympy",
        "list verified element-by-element" if ok else "one or more list elements differ",
        {"status": "verified" if ok else "verified_difference", "elements": [c.metadata for c in checks]},
    )


def _verify_system(candidate: Any, spec: dict[str, Any]) -> VerificationResult:
    """Verify an ordered solution against explicit expected values."""
    candidate_list = _parse_list(candidate)
    expected = spec.get("expected")
    if candidate_list is None or not isinstance(expected, list):
        return VerificationResult(False, "structured-system", "unsupported system solution format", {"status": "unsupported_format"})

    if len(candidate_list) != len(expected):
        return VerificationResult(False, "structured-system", "solution length differs from expected", {"status": "verified_difference"})

    checks = [verify_symbolic_equality(a, b) for a, b in zip(candidate_list, expected)]
    ok = all(check.ok for check in checks)
    return VerificationResult(
        ok,
        "structured-system+sympy",
        "system solution verified" if ok else "system solution differs",
        {
            "status": "verified" if ok else "verified_difference",
            "variables": spec.get("variables", []),
            "equations": spec.get("equations", []),
            "elements": [c.metadata for c in checks],
        },
    )


def verify_symbolic_equality(lhs: Any, rhs: Any) -> VerificationResult:
    """Verify scalar/expression equality using SymPy after normalization."""
    try:
        import sympy as sp
    except ImportError:
        return VerificationResult(False, "sympy", "SymPy is not installed.", {"status": "missing_dependency"})

    lhs_text = _clean_candidate(lhs)
    rhs_text = _clean_candidate(rhs)
    try:
        difference = sp.simplify(sp.sympify(lhs_text) - sp.sympify(rhs_text))
        ok = bool(difference == 0)
        return VerificationResult(
            ok,
            "sympy.simplify",
            "symbolic equality verified" if ok else "symbolic expressions differ",
            {"status": "verified" if ok else "verified_difference", "difference": str(difference)},
        )
    except Exception as exc:
        return VerificationResult(
            False,
            "sympy.simplify",
            "verification failed",
            {"status": "parser_or_verification_error", "error": type(exc).__name__, "message": str(exc)},
        )


def verify_answer(candidate: Any, reference: Any = None, spec: dict[str, Any] | None = None) -> VerificationResult:
    """Choose verification semantics from an explicit dataset specification."""
    if spec:
        answer_type = spec.get("type")
        if answer_type == "list":
            return _verify_list(candidate, spec.get("expected", reference))
        if answer_type == "system":
            return _verify_system(candidate, spec)
        if answer_type in {"scalar", "expression"}:
            return verify_symbolic_equality(candidate, spec.get("expected", reference))
        return VerificationResult(False, "structured-spec", f"unknown verification type: {answer_type}", {"status": "unsupported_format"})

    candidate_list = _parse_list(candidate)
    reference_list = _parse_list(reference)
    if candidate_list is not None or reference_list is not None:
        return _verify_list(candidate, reference)
    return verify_symbolic_equality(candidate, reference)


if __name__ == "__main__":
    examples = [
        ("Respuesta: 5", "5", None),
        ("[2, 3]", None, {"type": "list", "expected": [2, 3]}),
        ("[6, 4]", None, {"type": "system", "variables": ["x", "y"], "expected": [6, 4], "equations": ["x+y-10", "x-y-2"]}),
        ("3*x**2 + 2", "2 + 3*x**2", None),
    ]
    for candidate, reference, spec in examples:
        print(candidate, "=>", verify_answer(candidate, reference, spec))
