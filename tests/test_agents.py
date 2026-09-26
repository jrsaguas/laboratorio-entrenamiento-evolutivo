import tempfile
import unittest
from pathlib import Path

from agents import (
    CodeAgent,
    HTMLCanvasAgent,
    MathReasoningAgent,
    OllamaMathReasoningAgent,
    PythonVisualizationAgent,
)


def request(input_value="x^2 + 1"):
    return {
        "task_id": "agent-test-001",
        "objective": "Test agent contract.",
        "input": input_value,
        "constraints": {},
        "depth_profile": {
            "rigor": 50, "prerequisites": 50, "formalism": 50, "proof": 50,
            "research": 0, "visualization": 0, "experimentation": 0,
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


class AgentContractTests(unittest.TestCase):
    def test_all_initial_agents_return_common_contract(self):
        for agent in (
            MathReasoningAgent(), CodeAgent(), HTMLCanvasAgent(),
            PythonVisualizationAgent(),
        ):
            result = agent.execute(request())
            self.assertEqual(result["task_id"], "agent-test-001")
            self.assertEqual(result["agent_id"], agent.agent_id)
            self.assertIn(result["status"], {"completed", "partial", "failed", "blocked"})
            self.assertIsInstance(result["provenance"], dict)
            self.assertIn("agent_id", result["provenance"])

    def test_real_math_agent_verifies_surface(self):
        result = MathReasoningAgent().execute(request("z = x² + y²"))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["result"]["expression"], "x**2 + y**2")
        self.assertEqual(result["result"]["partial_derivatives"]["fx"], "2*x")
        self.assertEqual(result["verification"]["status"], "passed")

    def test_real_visualization_agent_writes_svg(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = request()
            payload["input"] = {
                "original": "z = x² + y²",
                "dependencies": {
                    "math": MathReasoningAgent().execute(request("z = x² + y²"))["result"]
                },
            }
            payload["constraints"] = {"artifact_dir": tmp}
            result = PythonVisualizationAgent().execute(payload)
            self.assertEqual(result["status"], "completed")
            artifact = Path(result["artifacts"][0]["path"])
            self.assertTrue(artifact.exists())
            self.assertGreater(artifact.stat().st_size, 1000)
            self.assertEqual(result["verification"]["status"], "passed")


    def test_ollama_math_adapter_preserves_backend_provenance(self):
        import agents.ollama_math as ollama_math

        original = ollama_math.generate

        class FakeResponse:
            text = "2"
            model = "qwen2-math:7b"
            thinking = None
            extraction = {"method": "fake"}

        ollama_math.generate = lambda *args, **kwargs: FakeResponse()
        try:
            result = OllamaMathReasoningAgent(model="qwen2-math:7b").execute(
                request("1 + 1")
            )
        finally:
            ollama_math.generate = original

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["result"]["answer"], "2")
        self.assertEqual(result["provenance"]["backend"], "ollama")
        self.assertEqual(result["provenance"]["model"], "qwen2-math:7b")
        self.assertEqual(result["verification"]["status"], "not_run")

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
