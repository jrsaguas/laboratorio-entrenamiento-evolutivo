import tempfile
import unittest
from pathlib import Path

from agents import MathReasoningAgent
from orchestrator import ImplementationSpec, Orchestrator


def request():
    return {
        "task_id": "planner-test",
        "objective": "Construye una visualización matemática.",
        "input": "z = x² + y²",
        "constraints": {"artifact_dir": str(Path(tempfile.gettempdir()) / "lab-tests")},
        "depth_profile": {
            "rigor": 50, "prerequisites": 50, "formalism": 50, "proof": 50,
            "research": 0, "visualization": 80, "experimentation": 20, "generalization": 50,
        },
        "requested_artifacts": ["surface.svg"],
        "verification_requirements": {
            "required": True, "verifiers": ["sympy_symbolic", "svg_integrity"],
            "on_failure": "fail", "max_retries": 0, "require_provenance": True,
        },
        "context_refs": [], "budget": {},
    }


class PlannerTests(unittest.TestCase):
    def test_selects_math_then_visualization(self):
        result = Orchestrator().execute_auto(request())
        self.assertEqual(result["status"], "completed")
        self.assertEqual([x["capability"] for x in result["trace"]], [
            "solve_math", "visualize_math_python"
        ])
        self.assertTrue(result["provenance"]["planning"])

    def test_requirements_are_explicit(self):
        plan = Orchestrator().plan(request())
        req = plan["requirements"]
        self.assertTrue(req["needs_math"])
        self.assertTrue(req["needs_visualization"])
        self.assertIn("surface.svg", req["required_artifacts"])
        self.assertEqual(req["required_verifiers"], ["sympy_symbolic", "svg_integrity"])

    def test_rejects_incompatible_verifier(self):
        bad = request()
        bad["verification_requirements"] = dict(bad["verification_requirements"])
        bad["verification_requirements"]["verifiers"] = ["unknown_verifier"]
        with self.assertRaises(ValueError):
            Orchestrator().plan(bad)

    def test_capability_metadata_is_explicit(self):
        registry = Orchestrator().registry
        math = registry.describe("solve_math")
        visual = registry.describe("visualize_math_python")
        self.assertIn("math_expression", math.accepts)
        self.assertIn("math_result", visual.accepts)
        self.assertIn("svg", visual.produces)

    def test_rejects_ambiguous_request(self):
        bad = request()
        bad["objective"] = "Haz algo."
        bad["input"] = "texto"
        bad["requested_artifacts"] = []
        bad["verification_requirements"] = dict(bad["verification_requirements"])
        bad["verification_requirements"]["verifiers"] = []
        with self.assertRaises(ValueError):
            Orchestrator().plan(bad)

    def test_capability_supports_multiple_implementations(self):
        registry = Orchestrator().registry
        registry.register_implementation(ImplementationSpec(
            implementation_id="test.alternate-math",
            capability="solve_math",
            agent_type=MathReasoningAgent,
            provider="test",
            execution_mode="test",
            cost_class="low",
            deterministic=True,
        ))
        self.assertEqual(
            registry.implementations("solve_math"),
            ("builtin.sympy", "ollama.qwen2-math", "test.alternate-math"),
        )
        self.assertEqual(
            registry.describe_implementation(
                "solve_math", "test.alternate-math"
            ).provider,
            "test",
        )


    def test_ollama_implementation_resolves_parameterized_agent(self):
        registry = Orchestrator().registry
        agent = registry.resolve("solve_math", "ollama.qwen2-math")
        self.assertEqual(agent.agent_id, "ollama-math-reasoning")
        self.assertEqual(agent.model, "qwen2-math:7b")

    def test_execution_records_default_implementation(self):
        result = Orchestrator().execute_auto(request())
        self.assertEqual(
            result["trace"][0]["implementation_id"],
            "builtin.sympy",
        )
        self.assertEqual(result["trace"][0]["provider"], "builtin")


if __name__ == "__main__":

    unittest.main()
