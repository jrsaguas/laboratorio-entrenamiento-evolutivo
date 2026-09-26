from __future__ import annotations

from time import perf_counter
from typing import Any

from .registry import CapabilityRegistry


class OrchestrationError(RuntimeError):
    pass


class Orchestrator:
    def __init__(self, registry=None):
        self.registry = registry or CapabilityRegistry()

    def execute(self, request: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any]:
        started = perf_counter()
        nodes = {node["node_id"]: node for node in graph["nodes"]}
        results = {}
        trace = []

        if not graph["entry_nodes"] or not graph["terminal_nodes"]:
            raise OrchestrationError("graph must have entry and terminal nodes")

        pending = set(nodes)
        while pending:
            runnable = [
                nodes[node_id] for node_id in pending
                if all(dep in results for dep in nodes[node_id]["dependencies"])
            ]
            if not runnable:
                raise OrchestrationError("graph has unresolved dependencies or a cycle")

            for node in sorted(runnable, key=lambda n: n["node_id"]):
                agent = self.registry.resolve(node["capability"])
                node_request = dict(request)
                node_request["task_id"] = f'{request["task_id"]}:{node["node_id"]}'
                node_request["input"] = self._resolve_inputs(
                    request["input"], node, results
                )
                started_node = perf_counter()
                result = agent.execute(node_request)
                elapsed_ms = round((perf_counter() - started_node) * 1000, 3)
                results[node["node_id"]] = result
                trace.append({
                    "node_id": node["node_id"],
                    "agent_id": result["agent_id"],
                    "capability": node["capability"],
                    "status": result["status"],
                    "latency_ms": elapsed_ms,
                    "dependencies": list(node["dependencies"]),
                })
                pending.remove(node["node_id"])

        return {
            "task_id": request["task_id"],
            "status": self._aggregate_status(results),
            "results": results,
            "trace": trace,
            "provenance": {
                "orchestrator": "0.1",
                "graph_id": graph["graph_id"],
                "node_count": len(nodes),
            },
            "metrics": {
                "latency_ms": round((perf_counter() - started) * 1000, 3)
            },
        }

    @staticmethod
    def _resolve_inputs(original_input, node, results):
        if not node["inputs"]:
            return original_input
        return {
            "original": original_input,
            "dependencies": {
                dep: results[dep]["result"] for dep in node["dependencies"]
            },
        }

    @staticmethod
    def _aggregate_status(results):
        statuses = [item["status"] for item in results.values()]
        if any(status == "failed" for status in statuses):
            return "failed"
        if any(status == "blocked" for status in statuses):
            return "blocked"
        if any(status == "partial" for status in statuses):
            return "partial"
        return "completed"
