import unittest

from agents import (
    CodeAgent,
    HTMLCanvasAgent,
    MathReasoningAgent,
    PythonVisualizationAgent,
)


def request():
    return {
        "task_id": "agent-test-001",
        "objective": "Test agent contract.",
        "input": "x^2 + 1",
        "constraints": {},
        "depth_profile": {
            "rigor": 50, "prerequisites": 50, "formalism": 50, "proof": 50,
            "research": 0, "visualization": 0, "experimentation": 0,
            "generalization": 50,
        },
        "requested_artifacts": [],
        "verification_requirements": {
            "required": False,
            "verifiers": [],
            "on_failure": "fail",
            "max_retries": 0,
            "require_provenance": True,
        },
        "context_refs": [],
        "budget": {},
    }


class AgentContractTests(unittest.TestCase):
    def test_all_initial_agents_return_common_contract(self):
        for agent in (
            MathReasoningAgent(),
            CodeAgent(),
            HTMLCanvasAgent(),
            PythonVisualizationAgent(),
        ):
            result = agent.execute(request())
            self.assertEqual(result["task_id"], "agent-test-001")
            self.assertEqual(result["agent_id"], agent.agent_id)
            self.assertIn(result["status"], {"completed", "partial", "failed", "blocked"})
            self.assertIsInstance(result["provenance"], dict)
            self.assertIn("agent_id", result["provenance"])

    def test_initial_adapters_are_explicitly_partial(self):
        agents = (
            MathReasoningAgent(),
            CodeAgent(),
            HTMLCanvasAgent(),
            PythonVisualizationAgent(),
        )
        for agent in agents:
            self.assertEqual(agent.execute(request())["status"], "partial")

    def test_missing_request_field_is_rejected(self):
        payload = request()
        del payload["task_id"]
        with self.assertRaises(ValueError):
            MathReasoningAgent().execute(payload)

    def test_agent_failure_is_explicit(self):
        class BrokenAgent(MathReasoningAgent):
            agent_id = "broken-math"

            def run(self, context):
                raise RuntimeError("backend unavailable")

        result = BrokenAgent().execute(request())
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["verification"]["status"], "not_run")
        self.assertIn("backend unavailable", result["uncertainties"][0])


if __name__ == "__main__":
    unittest.main()
