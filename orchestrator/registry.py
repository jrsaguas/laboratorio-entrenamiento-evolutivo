from __future__ import annotations

from typing import Type

from agents import (
    Agent,
    CodeAgent,
    HTMLCanvasAgent,
    MathReasoningAgent,
    PythonVisualizationAgent,
)


class CapabilityRegistry:
    DEFAULTS = {
        "solve_math": MathReasoningAgent,
        "implement_code": CodeAgent,
        "build_canvas": HTMLCanvasAgent,
        "visualize_math_python": PythonVisualizationAgent,
    }

    def __init__(self, registrations=None):
        self._agents = dict(self.DEFAULTS)
        if registrations:
            self._agents.update(registrations)

    def register(self, capability: str, agent_type: Type[Agent]) -> None:
        if not capability:
            raise ValueError("capability must be non-empty")
        if not isinstance(agent_type, type) or not issubclass(agent_type, Agent):
            raise TypeError("agent_type must be an Agent subclass")
        self._agents[capability] = agent_type

    def resolve(self, capability: str) -> Agent:
        try:
            return self._agents[capability]()
        except KeyError as exc:
            raise KeyError(f"unknown capability: {capability}") from exc

    def capabilities(self) -> tuple[str, ...]:
        return tuple(sorted(self._agents))
