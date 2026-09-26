import tempfile
import unittest
from pathlib import Path

from orchestrator import Orchestrator


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
            "required": True, "verifiers": [], "on_failure": "fail",
            "max_retries": 0, "require_provenance": True,
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

    def test_rejects_ambiguous_request(self):
        bad = request()
        bad["objective"] = "Haz algo."
        bad["input"] = "texto"
        bad["requested_artifacts"] = []
        with self.assertRaises(ValueError):
            Orchestrator().plan(bad)


if __name__ == "__main__":
    unittest.main()
