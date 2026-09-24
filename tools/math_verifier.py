"""Deterministic mathematical verification primitives for laboratory experiments."""

from __future__ import annotations

import ast
import re
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application, convert_xor

_MATH_TRANSFORMATIONS = standard_transformations + (convert_xor, implicit_multiplication_application)
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
    text = re.sub(
        r"^(?:answer|final answer|respuesta|resultado)\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    if text.startswith(chr(58)):
        text = text[1:].strip()
    return text


def _parse_list(value: Any) -> list[Any] | None:
    if isinstance(value, (list, tuple)):
        return list(value)
    text = _clean_candidate(value)
    if not (text.startswith("[") or text.startswith("(")):
        assignments = re.findall(
            r"(?:^|\b)(?:[A-Za-z_]\w*)\s*=\s*([^=,;]+?)(?=\s+(?:o|or|and|y)\s+[A-Za-z_]\w*\s*=|$)",
            text,
            flags=re.IGNORECASE,
        )
        if len(assignments) >= 2:
            return [item.strip().rstrip(".") for item in assignments]
        return None
    try:
        parsed = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return None
    return list(parsed) if isinstance(parsed, (list, tuple)) else None


def _extract_scalar_candidate(value: Any) -> tuple[str | None, dict[str, Any]]:
    """Extract a scalar answer from common answer/assignment formats."""
    text = _clean_candidate(value)
    if not text:
        return None, {"status": "extraction_failed", "reason": "empty_candidate"}

    boxed = re.fullmatch(r"\\boxed\{(.+)\}", text, flags=re.DOTALL)
    if boxed:
        text = boxed.group(1).strip()

    assignment = re.search(
        r"(?:^|[\s:])(?:[A-Za-z_]\w*)\s*=\s*(.+)$",
        text,
        flags=re.DOTALL,
    )
    if assignment:
        extracted = assignment.group(1).strip().rstrip(".")
        if extracted:
            return extracted, {
                "status": "extracted",
                "source": "assignment",
                "original": str(value),
            }

    natural_scalar = re.search(
        r"\b(?:es|is|equals)\s*[:=]?\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)\b",
        text,
        flags=re.IGNORECASE,
    )
    if natural_scalar:
        return natural_scalar.group(1), {
            "status": "extracted",
            "source": "natural_language_scalar",
            "original": str(value),
        }

    if re.fullmatch(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", text):
        return text, {
            "status": "extracted",
            "source": "standalone_scalar",
            "original": str(value),
        }

    return None, {
        "status": "extraction_failed",
        "reason": "unsupported_scalar_format",
        "original": str(value),
    }


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
            parse_expr(_clean_candidate(lhs), transformations=_MATH_TRANSFORMATIONS) - parse_expr(_clean_candidate(rhs), transformations=_MATH_TRANSFORMATIONS)
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


def _strip_latex_delimiters(text: str) -> str:
    text = text.replace(r"\(", "").replace(r"\)", "")
    text = text.replace(r"\$", "")
    text = text.replace("$", "")
    return text.strip()


def _normalize_latex_expression(text: str) -> str:
    """Normalize a small, deterministic subset of LaTeX used in model answers."""
    previous = None
    while text != previous:
        previous = text
        text = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)", text)
    text = re.sub(r"\\(?:sin|cos|tan|exp|log|ln|sinh|cosh|tanh)\b", lambda m: m.group(0)[1:], text)
    text = text.replace(r"\cdot", "*").replace(r"\times", "*")
    text = re.sub(r"\be\^\s*([A-Za-z_][A-Za-z0-9_]*(?:\([^)]*\))?)", r"exp(\1)", text)
    text = text.replace("{", "(").replace("}", ")")
    return text.strip()


def _strip_integration_constant(text: str) -> str:
    return re.sub(r"\s*(?:\+\s*C|\+\s*const(?:ant)?|\+\s*constante)\s*$", "", text, flags=re.IGNORECASE).strip()


def _is_derivative_label(text: str) -> bool:
    normalized = text.replace(" ", "")
    return bool(re.fullmatch(r"[A-Za-z_]\w*(?:'{1,3})?\(x\)", normalized))


def _extract_expression_candidate(candidate: Any) -> tuple[str | None, dict[str, Any]]:
    text = str(candidate).strip()
    original = text

    prefix_pattern = r"^(?:la\s+respuesta\s+es|respuesta|resultado)\s*:?\s*"
    text = re.sub(prefix_pattern, "", text, flags=re.IGNORECASE).strip()
    text = _strip_latex_delimiters(text)

    if text.startswith(r"\boxed{") and text.endswith("}"):
        text = text[len(r"\boxed{"):-1].strip()

    text = _normalize_latex_expression(text)

    if text.startswith(":"):
        text = text[1:].strip()

    if not text:
        return None, {
            "status": "empty_expression",
            "original": original,
        }

    # Common natural-language integral form: "... = expression + C".
    integral_match = re.search(r"(?:∫|\\int).*\=\s*([^=]+)$", text, flags=re.DOTALL)
    if integral_match:
        text = _strip_integration_constant(integral_match.group(1).strip().rstrip("."))
    elif text.count("=") > 1:
        # Natural-language derivations may omit the integral symbol. The final
        # equality payload is the answer expression.
        text = _strip_integration_constant(text.rsplit("=", 1)[1].strip().rstrip("."))

    return text, {
        "status": "extracted" if text != original else "unchanged",
        "original": original,
        "candidate": text,
    }


def _verify_expression_candidate(candidate: Any, expected: Any) -> VerificationResult:
    text, extraction_metadata = _extract_expression_candidate(candidate)
    if text is None:
        return VerificationResult(
            False,
            "expression-extraction",
            "could not extract an expression from candidate",
            extraction_metadata,
        )

    if text.count("=") != 1:
        return verify_symbolic_equality(text, expected)

    lhs, rhs = (part.strip() for part in text.split("=", 1))

    # A derivative label is metadata about the requested operation, not a
    # symbolic expression to compare with the expected result.
    if _is_derivative_label(lhs):
        rhs = _strip_integration_constant(rhs)
        payload = verify_symbolic_equality(rhs, expected)
        return VerificationResult(
            payload.ok,
            "expression-label+sympy",
            "labeled expression verified" if payload.ok else "labeled expression differs from expected",
            {**payload.metadata, "label": lhs, "status": "verified" if payload.ok else "reference_mismatch"},
        )

    equality = verify_symbolic_equality(lhs, rhs)
    if not equality.ok:
        return VerificationResult(
            False,
            "sympy.simplify",
            "verification failed",
            {
                **equality.metadata,
                "status": "invalid_equality",
                "equality_details": equality.details,
            },
        )

    left_matches = verify_symbolic_equality(lhs, expected)
    right_matches = verify_symbolic_equality(rhs, expected)

    if left_matches.ok or right_matches.ok:
        matching_side = "left" if left_matches.ok else "right"
        return VerificationResult(
            True,
            "sympy.simplify+equality",
            "symbolic equality verified",
            {
                "status": "verified",
                "equality": True,
                "reference_side": matching_side,
            },
        )

    return VerificationResult(
        False,
        "sympy.simplify+equality",
        "equality is valid but neither side matches the expected expression",
        {
            "status": "reference_mismatch",
            "equality": True,
        },
    )


def verify_answer(candidate: Any, reference: Any = None,
                  spec: dict[str, Any] | None = None) -> VerificationResult:
    if spec:
        answer_type = spec.get("type")
        if answer_type == "list":
            return _verify_list(candidate, spec.get("expected", reference))
        if answer_type == "system":
            return _verify_system(candidate, spec)
        if answer_type == "scalar":
            extracted, extraction_metadata = _extract_scalar_candidate(candidate)
            if extracted is None:
                return VerificationResult(
                    False,
                    "scalar-extraction",
                    "could not extract a scalar value from candidate",
                    extraction_metadata,
                )
            result = verify_symbolic_equality(
                extracted, spec.get("expected", reference)
            )
            return VerificationResult(
                result.ok,
                "scalar-extraction+sympy",
                result.details,
                {**result.metadata, "extraction": extraction_metadata},
            )
        if answer_type == "expression":
            return _verify_expression_candidate(
                candidate, spec.get("expected", reference)
            )
        return VerificationResult(False, "structured-spec",
                                  f"unknown verification type: {answer_type}",
                                  {"status": "unsupported_format"})
    candidate_list = _parse_list(candidate)
    reference_list = _parse_list(reference)
    if candidate_list is not None or reference_list is not None:
        return _verify_list(candidate, reference)
    return verify_symbolic_equality(candidate, reference)
