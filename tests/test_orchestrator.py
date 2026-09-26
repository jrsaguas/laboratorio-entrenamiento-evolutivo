import unittest

from orchestrator import Orchestrator, OrchestrationError


def request():
    return {
        "task_id": "orch-test-001",
        "objective": "Run a two-agent graph.",
        "input": "z = x^2 + y^2",
        "constraints": {},
        "depth_profile": {
            "rigor": 50, "prerequisites": 50, "formalism": 50, "proof": 50,
            "research": 0, "visualization": 80, "experimentation": 20,
            "generalization": 50,
        },
        "requested_artifacts": [],
        "verification_requirements": {
            "required": False, "verifiers": [], "on_failure": "fail",
            "max_retries": 0, "require_provenance": True,
        },
        "context_refs": [],
        "budget": {},
    }


def graph():
    return {
        "graph_id": "graph-001",
        "task_id": "orch-test-001",
        "nodes": [
            {
                "node_id": "math",
                "capability": "solve_math",
                "agent": "math-reasoning",
                "inputs": [],
                "dependencies": [],
                "constraints": {},
                "verification_policy": {},
                "retry_policy": {"max_retries": 0, "retry_on": []},
                "status": "pending",
                "artifacts": [],
            },
            {
                "node_id": "viz",
                "capability": "visualize_math_python",
                "agent": "python-visualization",
                "inputs": ["math"],
                "dependencies": ["math"],
                "constraints": {},
                "verification_policy": {},
                "retry_policy": {"max_retries": 0, "retry_on": []},
                "status": "pending",
                "artifacts": [],
            },
        ],
        "entry_nodes": ["math"],
        "terminal_nodes": ["viz"],
    }


class OrchestratorTests(unittest.TestCase):
    def test_executes_dependencies_in_order(self):
        result = Orchestrator().execute(request(), graph())
        self.assertEqual(result["status"], "partial")
        self.assertEqual([x["node_id"] for x in result["trace"]], ["math", "viz"])
        self.assertEqual(result["trace"][1]["dependencies"], ["math"])
        self.assertEqual(result["provenance"]["node_count"], 2)

    def test_dependency_result_is_forwarded(self):
        result = Orchestrator().execute(request(), graph())
        viz_input = result["results"]["viz"]["result"]
        self.assertEqual(viz_input["method"], "python_visualization_adapter")

    def test_unknown_capability_is_explicit(self):
        bad = graph()
        bad["nodes"][0]["capability"] = "does_not_exist"
        with self.assertRaises(KeyError):
            Orchestrator().execute(request(), bad)

    def test_cycle_is_rejected(self):
        bad = graph()
        bad["nodes"][0]["dependencies"] = ["viz"]
        with self.assertRaises(OrchestrationError):
            Orchestrator().execute(request(), bad)


if __name__ == "__main__":
    unittest.main()
