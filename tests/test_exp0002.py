"""Protocol tests for EXP-0002."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "experiments" / "exp-0002-model-comparison" / "runner.py"

spec = importlib.util.spec_from_file_location("exp0002_runner", RUNNER_PATH)
assert spec and spec.loader
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class Exp0002ProtocolTests(unittest.TestCase):
    def test_protocol_identity(self) -> None:
        class Args:
            temperature = 0.0
            max_tokens = -1
            seed = None
            timeout = 0

        proto = runner.protocol(Args(), "run-test", ["model-a", "model-b"])
        self.assertEqual(proto["protocol_version"], "0.1")
        self.assertEqual(proto["dataset_version"], "0.1")
        self.assertEqual(proto["experiment_version"], "0.1")
        self.assertEqual(proto["models"], ["model-a", "model-b"])
        self.assertTrue(proto["same_prompt"])
        self.assertTrue(proto["same_generation_parameters"])
        self.assertTrue(proto["deterministic_verification"])
        self.assertFalse(proto["repair"])

    def test_row_preserves_model_and_semantic_result(self) -> None:
        item = {
            "id": "t-001",
            "category": "algebra",
            "difficulty": 1,
            "answer": "5",
        }
        verification = {
            "ok": True,
            "method": "scalar-extraction+sympy",
            "details": "symbolic equality verified",
            "metadata": {"status": "verified"},
        }
        row = runner.make_row(item, "model-a", "5", 10.0, {"eval_count": 2}, verification, 0.5)
        self.assertEqual(row["model"], "model-a")
        self.assertTrue(row["semantic_correct"])
        self.assertTrue(row["verification_success"])
        self.assertEqual(row["generation_latency_ms"], 10.0)
        self.assertEqual(row["verification_latency_ms"], 0.5)

    def test_model_list_deduplicates_without_changing_order(self) -> None:
        models = list(dict.fromkeys(x.strip() for x in "qwen2-math:7b,llama3.2:3b,qwen2-math:7b".split(",") if x.strip()))
        self.assertEqual(models, ["qwen2-math:7b", "llama3.2:3b"])

    def test_default_artifact_path_is_unique_per_run(self) -> None:
        first = runner.default_output_path("run-20260924T100000Z")
        second = runner.default_output_path("run-20260924T100001Z")
        self.assertNotEqual(first, second)
        self.assertEqual(first.parent, second.parent)
        self.assertEqual(first.name, "run-20260924T100000Z.json")
        self.assertEqual(second.name, "run-20260924T100001Z.json")



if __name__ == "__main__":
    unittest.main()
