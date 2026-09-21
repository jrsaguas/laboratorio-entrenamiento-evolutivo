"""Deterministic mathematical verification primitives for laboratory experiments.

The verifier is intentionally independent of an LLM. It should receive a
candidate answer and a reference expression/problem specification, then return
structured evidence that can be consumed by the evaluation layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    method: str
    details: str
    metadata: dict[str, Any]


def verify_symbolic_equality(lhs: Any, rhs: Any) -> VerificationResult:
    """Verify symbolic equality using SymPy.

    Imports SymPy lazily so the laboratory can run metadata/configuration tests
    without requiring the dependency until this tool is actually executed.
    """
    try:
        import sympy as sp
    except ImportError:
        return VerificationResult(
            ok=False,
            method="sympy",
            details="SymPy is not installed.",
            metadata={"error": "missing_dependency"},
        )

    try:
        difference = sp.simplify(sp.sympify(lhs) - sp.sympify(rhs))
        ok = bool(difference == 0)
        return VerificationResult(
            ok=ok,
            method="sympy.simplify",
            details="symbolic equality verified" if ok else "symbolic expressions differ",
            metadata={"difference": str(difference)},
        )
    except Exception as exc:
        return VerificationResult(
            ok=False,
            method="sympy.simplify",
            details="verification failed",
            metadata={"error": type(exc).__name__, "message": str(exc)},
        )


if __name__ == "__main__":
    result = verify_symbolic_equality("3*x**2 + 2", "2 + 3*x**2")
    print(result)
