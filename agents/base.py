from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from time import perf_counter
from typing import Any

VALID_STATUSES = {"completed", "partial", "failed", "blocked"}


@dataclass(frozen=True)
class AgentContext:
    request: dict[str, Any]


class Agent(ABC):
    agent_id: str = "agent"

    def execute(self, request: dict[str, Any]) -> dict[str, Any]:
        started = perf_counter()
        self._validate_request(request)
        context = AgentContext(request=request)
        try:
            result = self.run(context)
        except Exception as exc:
            result = self._failure_result(request, exc)
        elapsed_ms = round((perf_counter() - started) * 1000, 3)
        result.setdefault("metrics", {})
        result["metrics"].setdefault("latency_ms", elapsed_ms)
        self._validate_result(result, request)
        return result

    @abstractmethod
    def run(self, context: AgentContext) -> dict[str, Any]:
        raise NotImplementedError

    def _validate_request(self, request: dict[str, Any]) -> None:
        required = {
            "task_id", "objective", "input", "constraints",
            "depth_profile", "requested_artifacts",
            "verification_requirements", "context_refs", "budget",
        }
        missing = required - request.keys()
        if missing:
            raise ValueError(f"missing request fields: {sorted(missing)}")
        if not isinstance(request["task_id"], str) or not request["task_id"]:
            raise ValueError("task_id must be a non-empty string")

    def _validate_result(self, result: dict[str, Any], request: dict[str, Any]) -> None:
        required = {
            "task_id", "agent_id", "status", "result", "artifacts",
            "claims", "evidence", "verification", "uncertainties",
            "actions", "metrics", "provenance",
        }
        missing = required - result.keys()
        if missing:
            raise ValueError(f"missing result fields: {sorted(missing)}")
        if result["task_id"] != request["task_id"]:
            raise ValueError("result task_id does not match request")
        if result["agent_id"] != self.agent_id:
            raise ValueError("result agent_id does not match agent")
        if result["status"] not in VALID_STATUSES:
            raise ValueError(f"invalid status: {result['status']!r}")
        if not isinstance(result["provenance"], dict):
            raise ValueError("provenance must be an object")

    def _failure_result(self, request: dict[str, Any], exc: Exception) -> dict[str, Any]:
        return {
            "task_id": request["task_id"],
            "agent_id": self.agent_id,
            "status": "failed",
            "result": None,
            "artifacts": [],
            "claims": [],
            "evidence": [],
            "verification": {"status": "not_run", "reason": "agent_failure"},
            "uncertainties": [str(exc)],
            "actions": [{"type": "agent_failure", "error": type(exc).__name__}],
            "metrics": {},
            "provenance": {"agent_id": self.agent_id},
        }


def base_result(context: AgentContext, result: Any, *, claims=None, artifacts=None) -> dict[str, Any]:
    return {
        "task_id": context.request["task_id"],
        "agent_id": "unset",
        "status": "completed",
        "result": result,
        "artifacts": artifacts or [],
        "claims": claims or [],
        "evidence": [],
        "verification": {"status": "not_run"},
        "uncertainties": [],
        "actions": [],
        "metrics": {},
        "provenance": {},
    }
