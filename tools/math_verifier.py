"""Deterministic mathematical verification primitives for laboratory experiments."""

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
    text = str(value).strip()
    fence = chr(96) * 3
    if text.startswith(fence) and text.endswith(fence):
        lines = text.splitlines()
        if len(lines) >= 2:
            text = "\n".join(lines[1:-1]).strip()
    return re.sub(
        r"^(?:answer|final answer|respuesta|resultado)\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _parse_list(value: Any) -> list[Any] | None:
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
        return VerificationResult(False, "structured-list", "unsupported list/tuple format",
                                  {"status": "unsupported_format"})
    if len(candidate_list) != len(reference_list):
        return VerificationResult(False, "structured-list", "list lengths differ",
                                  {"status": "verified_difference"})
    checks = [verify_symbolic_equality(a, b) for a, b in zip(candidate_list, reference_list)]
    ok = all(check.ok for check in checks)
    return VerificationResult(
        ok, "structured-list+sympy",
        "list verified element-by-element" if ok else "one or more list elements differ",
        {"status": "verified" if ok else "verified_difference",
         "elements": [c.metadata for c in checks]},
    )


def _verify_system(candidate: Any, spec: dict[str, Any]) -> VerificationResult:
    """Verify the candidate against declared equations, not only expected values."""
    candidate_list = _parse_list(candidate)
    variables = spec.get("variables", [])
    equations = spec.get("equations", [])
    expected = spec.get("expected")
    if (candidate_list is None or not isinstance(variables, list)
            or not isinstance(equations, list)
            or len(candidate_list) != len(variables)
            or len(equations) != len(variables)):
        return VerificationResult(False, "structured-system",
                                  "unsupported system solution format",
                                  {"status": "unsupported_format"})
    try:
        import sympy as sp
        symbols = [sp.Symbol(str(name)) for name in variables]
        local_dict = dict(zip(variables, symbols))
        substitution = dict(zip(symbols, candidate_list))
        residuals = [
            sp.simplify(sp.sympify(equation, locals=local_dict).subs(substitution))
            for equation in equations
        ]
        equations_ok = all(residual == 0 for residual in residuals)
        expected_ok = None
        if isinstance(expected, list) and len(expected) == len(candidate_list):
            expected_ok = all(
                verify_symbolic_equality(a, b).ok
                for a, b in zip(candidate_list, expected)
            )
        ok = equations_ok and expected_ok is not False
        return VerificationResult(
            ok, "structured-system+sympy",
            "system solution satisfies equations" if ok
            else "system solution does not satisfy the declared equations",
            {"status": "verified" if ok else "verified_difference",
             "variables": variables,
             "equations": equations,
             "candidate": candidate_list,
             "residuals": [str(value) for value in residuals],
             "expected_match": expected_ok},
        )
    except Exception as exc:
        return VerificationResult(False, "structured-system+sympy",
                                  "system verification failed",
                                  {"status": "parser_or_verification_error",
                                   "error": type(exc).__name__,
                                   "message": str(exc)})


def verify_symbolic_equality(lhs: Any, rhs: Any) -> VerificationResult:
    try:
        import sympy as sp
    except ImportError:
        return VerificationResult(False, "sympy", "SymPy is not installed.",
                                  {"status": "missing_dependency"})
    try:
        difference = sp.simplify(
            sp.sympify(_clean_candidate(lhs)) - sp.sympify(_clean_candidate(rhs))
        )
        ok = bool(difference == 0)
        return VerificationResult(
            ok, "sympy.simplify",
            "symbolic equality verified" if ok else "symbolic expressions differ",
            {"status": "verified" if ok else "verified_difference",
             "difference": str(difference)},
        )
    except Exception as exc:
        return VerificationResult(False, "sympy.simplify", "verification failed",
                                  {"status": "parser_or_verification_error",
                                   "error": type(exc).__name__,
                                   "message": str(exc)})


def verify_answer(candidate: Any, reference: Any = None,
                  spec: dict[str, Any] | None = None) -> VerificationResult:
    if spec:
        answer_type = spec.get("type")
        if answer_type == "list":
            return _verify_list(candidate, spec.get("expected", reference))
        if answer_type == "system":
            return _verify_system(candidate, spec)
        if answer_type in {"scalar", "expression"}:
            return verify_symbolic_equality(candidate, spec.get("expected", reference))
        return VerificationResult(False, "structured-spec",
                                  f"unknown verification type: {answer_type}",
                                  {"status": "unsupported_format"})
    candidate_list = _parse_list(candidate)
    reference_list = _parse_list(reference)
    if candidate_list is not None or reference_list is not None:
        return _verify_list(candidate, reference)
    return verify_symbolic_equality(candidate, reference)
