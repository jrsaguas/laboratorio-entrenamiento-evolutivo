from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Type

from agents import (
    Agent,
    CodeAgent,
    HTMLCanvasAgent,
    MathReasoningAgent,
    OllamaMathReasoningAgent,
    PythonVisualizationAgent,
)


@dataclass(frozen=True)
class CapabilitySpec:
    capability: str
    accepts: tuple[str, ...]
    produces: tuple[str, ...]
    verifiers: tuple[str, ...]
    requires: tuple[str, ...] = ()
    min_depth: tuple[tuple[str, int], ...] = ()
    cost_class: str = "standard"


@dataclass(frozen=True)
class ImplementationSpec:
    implementation_id: str
    capability: str
    agent_type: Type[Agent]
    provider: str
    model: str | None = None
    execution_mode: str = "builtin"
    cost_class: str = "standard"
    deterministic: bool = True
    available: bool = True
    factory: Callable[[], Agent] | None = None


class CapabilityRegistry:
    DEFAULT_OLLAMA_MODEL = "qwen2-math:7b"

    DEFAULT_IMPLEMENTATIONS = {
        "solve_math": "builtin.sympy",
        "implement_code": "builtin.code",
        "build_canvas": "builtin.html_canvas",
        "visualize_math_python": "builtin.python_svg",
    }

    SPECS = {
        "solve_math": CapabilitySpec(
            "solve_math",
            accepts=("problem", "math_expression", "text"),
            produces=("math_result",),
            verifiers=("sympy_symbolic",),
            min_depth=(("rigor", 40), ("formalism", 40)),
            cost_class="low",
        ),
        "implement_code": CapabilitySpec(
            "implement_code",
            accepts=("text", "code_request"),
            produces=("code",),
            verifiers=("syntax",),
            cost_class="standard",
        ),
        "build_canvas": CapabilitySpec(
            "build_canvas",
            accepts=("math_result", "text"),
            produces=("html", "canvas"),
            verifiers=("html_structure",),
            requires=("math_result",),
            min_depth=(("visualization", 40),),
            cost_class="standard",
        ),
        "visualize_math_python": CapabilitySpec(
            "visualize_math_python",
            accepts=("math_result", "text"),
            produces=("svg", "visualization"),
            verifiers=("svg_integrity",),
            requires=("math_result",),
            min_depth=(("visualization", 60),),
            cost_class="low",
        ),
    }

    DEFAULTS = {
        "solve_math": MathReasoningAgent,
        "implement_code": CodeAgent,
        "build_canvas": HTMLCanvasAgent,
        "visualize_math_python": PythonVisualizationAgent,
    }
    def __init__(self, registrations=None, implementations=None):
        self._specs = dict(self.SPECS)
        self._implementations: dict[str, dict[str, ImplementationSpec]] = {
            capability: {} for capability in self._specs
        }
        self._defaults = dict(self.DEFAULT_IMPLEMENTATIONS)
        for capability, agent_type in self.DEFAULTS.items():
            self.register_implementation(
                ImplementationSpec(
                    implementation_id=self.DEFAULT_IMPLEMENTATIONS[capability],
                    capability=capability,
                    agent_type=agent_type,
                    provider="builtin",
                    execution_mode="builtin",
                    cost_class=self._specs[capability].cost_class,
                )
            )
        self.register_implementation(ImplementationSpec(
            implementation_id="ollama.qwen2-math",
            capability="solve_math",
            agent_type=OllamaMathReasoningAgent,
            provider="ollama",
            model=self.DEFAULT_OLLAMA_MODEL,
            execution_mode="ollama_api",
            cost_class="model",
            deterministic=True,
            factory=lambda: OllamaMathReasoningAgent(model=self.DEFAULT_OLLAMA_MODEL),
        ))
        if registrations:
            for capability, agent_type in registrations.items():
                self.register(capability, agent_type)
        if implementations:
            for spec in implementations:
                self.register_implementation(spec)

    def register(self, capability: str, agent_type: Type[Agent], spec: CapabilitySpec | None = None) -> None:
        if not capability:
            raise ValueError("capability must be non-empty")
        if not isinstance(agent_type, type) or not issubclass(agent_type, Agent):
            raise TypeError("agent_type must be an Agent subclass")
        if spec is not None:
            if spec.capability != capability:
                raise ValueError("spec capability must match registration")
            self._specs[capability] = spec
        implementation_id = f"builtin.{capability}"
        self.register_implementation(ImplementationSpec(
            implementation_id=implementation_id,
            capability=capability,
            agent_type=agent_type,
            provider="builtin",
            execution_mode="builtin",
            cost_class=self._specs.get(capability, CapabilitySpec(
                capability, (), (), ()
            )).cost_class,
        ), make_default=True)

    def register_implementation(self, spec: ImplementationSpec, *, make_default: bool = False) -> None:
        if spec.capability not in self._specs:
            raise KeyError(f"unknown capability: {spec.capability}")
        if not spec.implementation_id:
            raise ValueError("implementation_id must be non-empty")
        if not isinstance(spec.agent_type, type) or not issubclass(spec.agent_type, Agent):
            raise TypeError("agent_type must be an Agent subclass")
        bucket = self._implementations.setdefault(spec.capability, {})
        bucket[spec.implementation_id] = spec
        if make_default:
            self._defaults[spec.capability] = spec.implementation_id

    def resolve(self, capability: str, implementation_id: str | None = None) -> Agent:
        spec = self.describe_implementation(capability, implementation_id)
        if not spec.available:
            raise RuntimeError(f"implementation unavailable: {spec.implementation_id}")
        return spec.factory() if spec.factory is not None else spec.agent_type()

    def describe(self, capability: str) -> CapabilitySpec:
        try:
            return self._specs[capability]
        except KeyError as exc:
            raise KeyError(f"unknown capability metadata: {capability}") from exc

    def describe_implementation(self, capability: str, implementation_id: str | None = None) -> ImplementationSpec:
        if capability not in self._implementations:
            raise KeyError(f"unknown capability: {capability}")
        selected = implementation_id or self._defaults[capability]
        try:
            return self._implementations[capability][selected]
        except KeyError as exc:
            raise KeyError(f"unknown implementation: {selected}") from exc

    def implementations(self, capability: str) -> tuple[str, ...]:
        if capability not in self._implementations:
            raise KeyError(f"unknown capability: {capability}")
        return tuple(sorted(self._implementations[capability]))

    def default_implementation(self, capability: str) -> str:
        self.describe(capability)
        return self._defaults[capability]

    def capabilities(self) -> tuple[str, ...]:
        return tuple(sorted(self._specs))
