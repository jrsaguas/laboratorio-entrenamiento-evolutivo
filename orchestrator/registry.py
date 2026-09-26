from __future__ import annotations

from dataclasses import dataclass
from typing import Type

from agents import (
    Agent,
    CodeAgent,
    HTMLCanvasAgent,
    MathReasoningAgent,
    PythonVisualizationAgent,
)


@dataclass(frozen=True)
class CapabilitySpec:
    capability: str
    agent_type: Type[Agent]
    produces: tuple[str, ...]
    verifiers: tuple[str, ...]
    requires: tuple[str, ...] = ()
    min_depth: tuple[tuple[str, int], ...] = ()
    cost_class: str = "standard"


class CapabilityRegistry:
    DEFAULTS = {
        "solve_math": MathReasoningAgent,
        "implement_code": CodeAgent,
        "build_canvas": HTMLCanvasAgent,
        "visualize_math_python": PythonVisualizationAgent,
    }

    SPECS = {
        "solve_math": CapabilitySpec(
            "solve_math", MathReasoningAgent,
            produces=("math_result",),
            verifiers=("sympy_symbolic",),
            min_depth=(("rigor", 40), ("formalism", 40)),
            cost_class="low",
        ),
        "implement_code": CapabilitySpec(
            "implement_code", CodeAgent,
            produces=("code",),
            verifiers=("syntax",),
            cost_class="standard",
        ),
        "build_canvas": CapabilitySpec(
            "build_canvas", HTMLCanvasAgent,
            produces=("html", "canvas"),
            verifiers=("html_structure",),
            requires=("math_result",),
            min_depth=(("visualization", 40),),
            cost_class="standard",
        ),
        "visualize_math_python": CapabilitySpec(
            "visualize_math_python", PythonVisualizationAgent,
            produces=("svg", "visualization"),
            verifiers=("svg_integrity",),
            requires=("math_result",),
            min_depth=(("visualization", 60),),
            cost_class="low",
        ),
    }

    def __init__(self, registrations=None):
        self._agents = dict(self.DEFAULTS)
        self._specs = dict(self.SPECS)
        if registrations:
            for capability, agent_type in registrations.items():
                self.register(capability, agent_type)

    def register(self, capability: str, agent_type: Type[Agent], spec: CapabilitySpec | None = None) -> None:
        if not capability:
            raise ValueError("capability must be non-empty")
        if not isinstance(agent_type, type) or not issubclass(agent_type, Agent):
            raise TypeError("agent_type must be an Agent subclass")
        self._agents[capability] = agent_type
        if spec is not None:
            if spec.capability != capability:
                raise ValueError("spec capability must match registration")
            self._specs[capability] = spec

    def resolve(self, capability: str) -> Agent:
        try:
            return self._agents[capability]()
        except KeyError as exc:
            raise KeyError(f"unknown capability: {capability}") from exc

    def describe(self, capability: str) -> CapabilitySpec:
        try:
            return self._specs[capability]
        except KeyError as exc:
            raise KeyError(f"unknown capability metadata: {capability}") from exc

    def capabilities(self) -> tuple[str, ...]:
        return tuple(sorted(self._agents))
