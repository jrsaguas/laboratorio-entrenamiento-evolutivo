from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .registry import CapabilityRegistry, CapabilitySpec


@dataclass(frozen=True)
class PlanDecision:
    capability: str
    reason: str
    depends_on: tuple[str, ...] = ()


class TaskPlanner:
    """Deterministic planner based on explicit requirements and capability metadata."""

    VERSION = "0.3"

    def __init__(self, registry: CapabilityRegistry | None = None):
        self.registry = registry or CapabilityRegistry()

    def plan(self, request: dict[str, Any]) -> dict[str, Any]:
        requirements = self._requirements(request)
        decisions: list[PlanDecision] = []
        rejected: dict[str, list[str]] = {}
        known_verifiers = {"sympy_symbolic", "svg_integrity", "html_structure", "syntax"}
        unknown_verifiers = sorted(set(requirements["required_verifiers"]) - known_verifiers)
        if unknown_verifiers:
            raise ValueError("unknown verification requirements: " + str(unknown_verifiers))

        if requirements["needs_math"]:
            decision, reasons = self._select("solve_math", requirements, terminal=False)
            if decision is None:
                raise ValueError(f"no compatible math capability: {reasons}")
            decisions.append(PlanDecision("solve_math", decision, ()))
            rejected["solve_math"] = reasons

        visualization_cap = self._choose_capability(("visualize_math_python", "build_canvas"), requirements, {"math_result"} if requirements["needs_math"] else set())
        if visualization_cap:
            decision, reasons = self._select(
                visualization_cap, requirements,
                produced_before={"math_result"} if requirements["needs_math"] else set(),
                terminal=True,
            )
            if decision is None:
                raise ValueError(f"no compatible visualization capability: {reasons}")
            decisions.append(
                PlanDecision(
                    visualization_cap,
                    decision,
                    ("math",) if requirements["needs_math"] else (),
                )
            )
            rejected[visualization_cap] = reasons

        if requirements["needs_code"] and not visualization_cap:
            decision, reasons = self._select("implement_code", requirements, terminal=True)
            if decision is None:
                raise ValueError(f"no compatible code capability: {reasons}")
            decisions.append(PlanDecision("implement_code", decision, ()))
            rejected["implement_code"] = reasons

        if requirements["needs_canvas"] and not visualization_cap:
            decision, reasons = self._select(
                "build_canvas", requirements,
                produced_before={"math_result"} if requirements["needs_math"] else set(),
                terminal=True,
            )
            if decision is None:
                raise ValueError(f"no compatible canvas capability: {reasons}")
            decisions.append(
                PlanDecision(
                    "build_canvas",
                    decision,
                    ("math",) if requirements["needs_math"] else (),
                )
            )
            rejected["build_canvas"] = reasons

        if not decisions:
            raise ValueError(
                "planner could not derive explicit requirements; "
                "make objective, input, or requested_artifacts more specific"
            )

        nodes = []
        for index, decision in enumerate(decisions):
            node_id = "math" if decision.capability == "solve_math" else decision.capability.replace("_", "-")
            policy = dict(request["verification_requirements"])
            nodes.append({
                "node_id": node_id,
                "capability": decision.capability,
                "agent": "",
                "inputs": ["dependency_results"] if decision.depends_on else [],
                "dependencies": list(decision.depends_on),
                "constraints": dict(request["constraints"]),
                "verification_policy": policy,
                "retry_policy": {
                    "max_retries": int(request["verification_requirements"].get("max_retries", 0)),
                    "retry_on": ["failed"],
                },
                "status": "pending",
                "artifacts": list(request["requested_artifacts"]) if index == len(decisions) - 1 else [],
            })

        return {
            "planner_version": self.VERSION,
            "requirements": requirements,
            "decisions": [
                {
                    "capability": d.capability,
                    "reason": d.reason,
                    "depends_on": list(d.depends_on),
                }
                for d in decisions
            ],
            "candidate_evaluation": {
                capability: {"rejected": reasons}
                for capability, reasons in rejected.items()
            },
            "graph": {
                "graph_id": f"{request['task_id']}:planned",
                "task_id": request["task_id"],
                "nodes": nodes,
                "entry_nodes": [nodes[0]["node_id"]],
                "terminal_nodes": [nodes[-1]["node_id"]],
            },
        }

    def _requirements(self, request: dict[str, Any]) -> dict[str, Any]:
        text = " ".join([
            str(request.get("objective", "")),
            str(request.get("input", "")),
            " ".join(str(x) for x in request.get("requested_artifacts", [])),
        ]).lower()
        artifacts = [str(x).lower() for x in request.get("requested_artifacts", [])]
        depth = request.get("depth_profile", {})

        needs_math = any(token in text for token in (
            "z =", "xÂ²", "x**2", "math", "matem", "deriv", "integral",
            "ecuaciÃ³n", "equation", "surface", "superficie",
        ))
        wants_visual = any(token in text for token in (
            "visual", "grÃ¡fic", "plot", "svg", "python",
        )) or any(a.endswith(".svg") or "visual" in a for a in artifacts)
        needs_canvas = any(token in text for token in ("canvas", "html", "web interact"))
        needs_code = any(token in text for token in ("implement", "program", "cÃ³digo", "code"))
        if depth.get("visualization", 0) >= 60 and artifacts:
            wants_visual = True

        required_verifiers = list(request.get("verification_requirements", {}).get("verifiers", []))
        required_artifacts = artifacts

        return {
            "needs_math": needs_math,
            "needs_visualization": wants_visual,
            "needs_canvas": needs_canvas,
            "needs_code": needs_code,
            "required_artifacts": required_artifacts,
            "required_verifiers": required_verifiers,
            "depth_profile": depth,
            "budget": dict(request.get("budget", {})),
        }

    def _choose_capability(self, candidates, requirements, produced_before=None):
        evaluations = []
        for capability in candidates:
            reason, reasons = self._select(capability, requirements, produced_before, terminal=True)
            evaluations.append((capability, reason, reasons))
        compatible = [x for x in evaluations if x[1] is not None]
        if not compatible:
            return None
        return sorted(compatible, key=lambda x: (self.registry.describe(x[0]).cost_class, x[0]))[0][0]

    def _select(
        self,
        capability: str,
        requirements: dict[str, Any],
        produced_before: set[str] | None = None,
        terminal: bool = False,
    ) -> tuple[str | None, list[str]]:
        spec: CapabilitySpec = self.registry.describe(capability)
        reasons: list[str] = []
        produced_before = produced_before or set()

        missing = [x for x in spec.requires if x not in produced_before]
        if missing:
            reasons.append(f"missing produced inputs: {missing}")

        for dimension, minimum in spec.min_depth:
            actual = int(requirements["depth_profile"].get(dimension, 0))
            if actual < minimum:
                reasons.append(f"depth {dimension}={actual} < required {minimum}")

        required_verifiers = set(requirements["required_verifiers"])
        if terminal:
            unsupported = sorted(v for v in required_verifiers if {"sympy_symbolic":"math_result","svg_integrity":"svg","html_structure":"html","syntax":"code"}.get(v) in spec.produces and v not in spec.verifiers)
            if unsupported:
                reasons.append(f"unsupported verifiers: {unsupported}")

        artifact_match = self._artifact_match(spec, requirements["required_artifacts"]) if terminal else True
        if not artifact_match:
            reasons.append("capability does not produce the requested artifact")

        if reasons:
            return None, reasons

        reason = (
            f"selected by capability metadata; produces={list(spec.produces)}, "
            f"verifiers={list(spec.verifiers)}, cost_class={spec.cost_class}"
        )
        return reason, []

    @staticmethod
    def _artifact_match(spec: CapabilitySpec, required: list[str]) -> bool:
        if not required:
            return True
        produced = set(spec.produces)
        for artifact in required:
            if artifact.endswith(".svg") and "svg" in produced:
                continue
            if artifact.endswith(".html") and "html" in produced:
                continue
            if artifact.endswith(".py") and "code" in produced:
                continue
            if artifact in produced:
                continue
            return False
        return True

