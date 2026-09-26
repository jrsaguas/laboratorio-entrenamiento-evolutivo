from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PlanDecision:
    capability: str
    reason: str
    depends_on: tuple[str, ...] = ()


class TaskPlanner:
    """Deterministic capability planner.

    It selects capabilities from explicit request signals before execution.
    This is intentionally rule-based: the first milestone is observable,
    reproducible planning, not opaque model-driven planning.
    """

    VERSION = "0.1"

    def plan(self, request: dict[str, Any]) -> dict[str, Any]:
        objective = str(request["objective"]).lower()
        input_text = str(request["input"]).lower()
        requested = " ".join(str(x).lower() for x in request["requested_artifacts"])

        decisions: list[PlanDecision] = []
        is_math = any(token in (objective + " " + input_text) for token in (
            "z =", "x²", "math", "matem", "deriv", "integral", "ecuación", "equation",
            "surface", "superficie",
        ))
        wants_python_visual = any(token in objective + " " + requested for token in (
            "visual", "gráfic", "plot", "svg", "python",
        ))
        wants_canvas = any(token in objective + " " + requested for token in (
            "canvas", "html", "web interact",
        ))
        wants_code = any(token in objective + " " + requested for token in (
            "implement", "program", "código", "code",
        ))

        if is_math:
            decisions.append(PlanDecision("solve_math", "mathematical structure is required"))
        if wants_python_visual:
            if not is_math:
                decisions.append(PlanDecision(
                    "visualize_math_python", "visualization requested without a math dependency"
                ))
            else:
                decisions.append(PlanDecision(
                    "visualize_math_python", "visualization requested; consume verified math result",
                    ("math",),
                ))
        elif wants_canvas:
            decisions.append(PlanDecision(
                "build_canvas", "interactive web/canvas artifact requested",
                ("math",) if is_math else (),
            ))
        elif wants_code:
            decisions.append(PlanDecision("implement_code", "code artifact requested"))

        if not decisions:
            raise ValueError(
                "planner could not select a capability from the request; "
                "make the objective or requested_artifacts explicit"
            )

        nodes = []
        for index, decision in enumerate(decisions):
            node_id = "math" if decision.capability == "solve_math" else decision.capability.replace("_", "-")
            if any(n["node_id"] == node_id for n in nodes):
                continue
            deps = list(decision.depends_on)
            policy = dict(request["verification_requirements"])
            nodes.append({
                "node_id": node_id,
                "capability": decision.capability,
                "agent": "",
                "inputs": ["dependency_results"] if deps else [],
                "dependencies": deps,
                "constraints": {},
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
            "decisions": [
                {"capability": d.capability, "reason": d.reason, "depends_on": list(d.depends_on)}
                for d in decisions
            ],
            "graph": {
                "graph_id": f"{request['task_id']}:planned",
                "task_id": request["task_id"],
                "nodes": nodes,
                "entry_nodes": [nodes[0]["node_id"]],
                "terminal_nodes": [nodes[-1]["node_id"]],
            },
        }
