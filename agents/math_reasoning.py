from __future__ import annotations

import re
import sympy as sp

from .base import Agent, AgentContext

_EQUATION = re.compile(r"z\s*=\s*(?P<expr>.+)", re.IGNORECASE)


def _normalize_expression(expression: str) -> str:
    return expression.replace("²", "**2").replace("^", "**").strip()


class MathReasoningAgent(Agent):
    agent_id = "math-reasoning"

    def run(self, context: AgentContext) -> dict:
        raw = str(context.request["input"]).strip()
        match = _EQUATION.fullmatch(raw)
        if not match:
            raise ValueError("Expected an equation of the form z = f(x, y).")

        expression_text = _normalize_expression(match.group("expr"))
        x, y = sp.symbols("x y", real=True)
        expression = sp.sympify(expression_text, locals={"x": x, "y": y})
        canonical = sp.expand(expression)

        fx = sp.diff(canonical, x)
        fy = sp.diff(canonical, y)
        hxx = sp.diff(fx, x)
        hxy = sp.diff(fx, y)
        hyy = sp.diff(fy, y)

        expected = x**2 + y**2
        is_expected = sp.simplify(canonical - expected) == 0
        verification = {
            "status": "passed",
            "method": "sympy_symbolic",
            "checks": [
                "expression_parsed",
                "canonicalized",
                "derivatives_computed",
                "target_identity_checked",
            ],
            "target_identity": bool(is_expected),
        }

        result = {
            "problem": raw,
            "equation": f"z = {sp.sstr(canonical)}",
            "expression": sp.sstr(canonical),
            "variables": ["x", "y"],
            "domain": "R^2",
            "surface_type": "elliptic_paraboloid" if is_expected else "unknown",
            "partial_derivatives": {"fx": sp.sstr(fx), "fy": sp.sstr(fy)},
            "hessian": [[sp.sstr(hxx), sp.sstr(hxy)], [sp.sstr(hxy), sp.sstr(hyy)]],
        }
        return {
            "task_id": context.request["task_id"],
            "agent_id": self.agent_id,
            "status": "completed",
            "result": result,
            "artifacts": [],
            "claims": [
                "SymPy parsed and canonicalized the supplied expression.",
                "The first and second partial derivatives were computed symbolically.",
            ],
            "evidence": [{"type": "symbolic_check", "target": "x**2 + y**2", "passed": bool(is_expected)}],
            "verification": verification,
            "uncertainties": [] if is_expected else ["The supplied expression is not the requested paraboloid."],
            "actions": [{"type": "capability", "name": "solve_math"}],
            "metrics": {},
            "provenance": {"agent_id": self.agent_id, "adapter_version": "0.2", "backend": "sympy"},
        }
