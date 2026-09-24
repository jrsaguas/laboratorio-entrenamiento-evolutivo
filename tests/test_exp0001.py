import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

RUNNER_PATH = Path(__file__).resolve().parents[1] / "experiments" / "exp-0001-math-verification" / "runner.py"
SPEC = importlib.util.spec_from_file_location("exp0001_runner", RUNNER_PATH)
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(runner)

from evaluation.metrics.metrics import summarize
from tools.math_verifier import verify_answer


class Exp0001Tests(unittest.TestCase):
    def test_semantic_equivalence(self):
        result = verify_answer(
            "1 + x",
            "x + 1",
            {"type": "expression", "expected": "x + 1"},
        )
        self.assertTrue(result.ok)

    def test_system_verification_uses_equations(self):
        result = verify_answer(
            "[6, 4]",
            None,
            {
                "type": "system",
                "variables": ["x", "y"],
                "expected": [6, 4],
                "equations": ["x+y-10", "x-y-2"],
                "ordered": True,
            },
        )
        self.assertTrue(result.ok)

    def test_false_rejection_uses_initial_oracle(self):
        rows = [{
            "id": "math-test",
            "condition": "verified_repair",
            "error": None,
            "exact_match": False,
            "contains_expected": False,
            "semantic_correct": True,
            "initial_semantic_correct": True,
            "verification_success": True,
            "first_verification_success": False,
            "repair_attempted": True,
            "latency_ms": 10,
            "verification_latency_ms": 1,
            "runtime": {},
        }]
        summary = summarize(rows)
        self.assertEqual(summary["verifier_false_rejection"], 1)

    def test_latency_components_exclude_oracle_from_condition_latency(self):
        rows = [{
            "id": "math-test",
            "condition": "baseline",
            "error": None,
            "exact_match": False,
            "contains_expected": True,
            "semantic_correct": True,
            "initial_semantic_correct": True,
            "verification_success": False,
            "first_verification_success": False,
            "repair_attempted": False,
            "generation_latency_ms": 100,
            "verification_latency_ms": 0,
            "repair_latency_ms": 0,
            "oracle_latency_ms": 900,
            "latency_ms": 100,
            "observed_latency_ms": 1000,
            "runtime": {},
        }]
        summary = summarize(rows)
        self.assertEqual(summary["average_latency_ms"], 100.0)
        self.assertEqual(summary["average_generation_latency_ms"], 100.0)
        self.assertEqual(summary["average_oracle_latency_ms"], 900.0)
        self.assertEqual(summary["average_observed_latency_ms"], 1000.0)

    def test_latency_components_include_intervention_cost(self):
        rows = [{
            "id": "math-test",
            "condition": "verified_repair",
            "error": None,
            "exact_match": False,
            "contains_expected": True,
            "semantic_correct": True,
            "initial_semantic_correct": False,
            "verification_success": True,
            "first_verification_success": False,
            "repair_attempted": True,
            "generation_latency_ms": 150,
            "verification_latency_ms": 20,
            "repair_latency_ms": 80,
            "oracle_latency_ms": 900,
            "latency_ms": 250,
            "observed_latency_ms": 1150,
            "runtime": {},
        }]
        summary = summarize(rows)
        self.assertEqual(summary["average_latency_ms"], 250.0)
        self.assertEqual(summary["average_generation_latency_ms"], 150.0)
        self.assertEqual(summary["average_verification_latency_ms"], 20.0)
        self.assertEqual(summary["average_repair_latency_ms"], 80.0)
        self.assertEqual(summary["average_oracle_latency_ms"], 900.0)
        self.assertEqual(summary["average_observed_latency_ms"], 1150.0)

    def test_runner_protocol_reuses_initial_response_and_repairs_only_after_failure(self):
        item = {
            "id": "math-test",
            "category": "algebra",
            "difficulty": 1,
            "prompt": "Resuelve 3x + 5 = 17.",
            "answer": "4",
            "verification_reference": "4",
            "verification_spec": {"type": "scalar", "expected": "4"},
        }
        calls = []

        def fake_ask(item, **kwargs):
            calls.append(kwargs.get("feedback"))
            return ("4" if kwargs.get("feedback") else "5"), 10.0, {"eval_count": 1}

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "run.json"
            rows = {"baseline": [], "verified": [], "verified_repair": []}
            existing = {"baseline": {}, "verified": {}, "verified_repair": {}}
            initial_cache = {}
            proto = {"protocol_version": "0.5", "run_id": "test-run"}

            with patch.object(runner, "ask", side_effect=fake_ask):
                runner.run_condition(
                    [item], "baseline", endpoint="", model="test", temperature=0,
                    max_tokens=1, timeout=None, seed=42, rows=rows,
                    existing=existing["baseline"], initial_cache=initial_cache,
                    output=output, proto=proto,
                )
                runner.run_condition(
                    [item], "verified", endpoint="", model="test", temperature=0,
                    max_tokens=1, timeout=None, seed=42, rows=rows,
                    existing=existing["verified"], initial_cache=initial_cache,
                    output=output, proto=proto,
                )
                runner.run_condition(
                    [item], "verified_repair", endpoint="", model="test", temperature=0,
                    max_tokens=1, timeout=None, seed=42, rows=rows,
                    existing=existing["verified_repair"], initial_cache=initial_cache,
                    output=output, proto=proto, repair=True,
                )

            self.assertEqual(calls, [None, "symbolic expressions differ"])
            self.assertEqual(rows["baseline"][0]["initial_response"], "5")
            self.assertEqual(rows["verified"][0]["initial_response"], "5")
            self.assertEqual(rows["verified_repair"][0]["initial_response"], "5")
            self.assertEqual(rows["verified_repair"][0]["response"], "4")
            self.assertEqual(rows["verified_repair"][0]["repair_response"], "4")
            self.assertTrue(rows["verified_repair"][0]["repair_attempted"])
            self.assertTrue(rows["verified_repair"][0]["semantic_correct"])
            self.assertGreaterEqual(rows["verified"][0]["oracle_latency_ms"], 0)
            self.assertEqual(
                rows["verified"][0]["verification_latency_ms"],
                rows["verified"][0]["latency_ms"] - rows["verified"][0]["generation_latency_ms"],
            )

    def test_baseline_has_semantic_accuracy(self):
        rows = [{
            "id": "math-test",
            "condition": "baseline",
            "error": None,
            "exact_match": False,
            "contains_expected": False,
            "semantic_correct": True,
            "initial_semantic_correct": True,
            "verification_success": False,
            "first_verification_success": False,
            "repair_attempted": False,
            "latency_ms": 10,
            "verification_latency_ms": 1,
            "runtime": {},
        }]
        summary = summarize(rows)
        self.assertEqual(summary["semantic_correct"], 1)
        self.assertEqual(summary["semantic_accuracy"], 1.0)


if __name__ == "__main__":
    unittest.main()
