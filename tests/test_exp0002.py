"""Protocol tests for EXP-0002."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "experiments" / "exp-0002-model-comparison" / "runner.py"
REEVALUATE_PATH = ROOT / "experiments" / "exp-0002-model-comparison" / "reevaluate.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load_module("exp0002_runner", RUNNER_PATH)
reevaluator = load_module("exp0002_reevaluate", REEVALUATE_PATH)


class Exp0002ProtocolTests(unittest.TestCase):
    def test_protocol_identity(self) -> None:
        class Args:
            temperature = 0.0
            max_tokens = -1
            seed = None
            timeout = 0

        proto = runner.protocol(Args(), "run-test", ["model-a", "model-b"])
        self.assertEqual(proto["protocol_version"], "0.2")
        self.assertEqual(proto["dataset_version"], "0.1")
        self.assertEqual(proto["experiment_version"], "0.2")
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
        row = runner.make_row(
            item, "model-a", "5", 10.0, {"eval_count": 2}, verification, 0.5
        )
        self.assertEqual(row["model"], "model-a")
        self.assertTrue(row["semantic_correct"])
        self.assertTrue(row["verification_success"])
        self.assertEqual(row["generation_latency_ms"], 10.0)
        self.assertEqual(row["verification_latency_ms"], 0.5)

    def test_model_list_deduplicates_without_changing_order(self) -> None:
        models = list(
            dict.fromkeys(
                x.strip()
                for x in "qwen2-math:7b,llama3.2:3b,qwen2-math:7b".split(",")
                if x.strip()
            )
        )
        self.assertEqual(models, ["qwen2-math:7b", "llama3.2:3b"])

    def test_default_artifact_path_is_unique_per_run(self) -> None:
        first = runner.default_output_path("run-20260924T100000Z")
        second = runner.default_output_path("run-20260924T100001Z")
        self.assertNotEqual(first, second)
        self.assertEqual(first.parent, second.parent)
        self.assertEqual(first.name, "run-20260924T100000Z.json")
        self.assertEqual(second.name, "run-20260924T100001Z.json")

    def test_reevaluation_preserves_source_and_records_verdict_change(self) -> None:
        dataset = (
            '{"id":"math-001","category":"algebra","difficulty":1,'
            '"prompt":"Calcula 2+3","answer":"5",'
            '"verification_reference":"5",'
            '"verification_spec":{"type":"scalar","expected":"5"}}\n'
        )
        artifact = {
            "experiment": "exp-0002",
            "protocol": {"run_id": "run-test", "dataset_version": "0.1"},
            "models": {
                "model-a": {
                    "summary": {},
                    "results": [{
                        "id": "math-001",
                        "model": "model-a",
                        "response": "La respuesta es x = 5",
                        "verification_success": False,
                        "semantic_correct": False,
                    }],
                }
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset_path = root / "dataset.jsonl"
            source_path = root / "source.json"
            output_path = root / "reevaluated.json"
            dataset_path.write_text(dataset, encoding="utf-8")
            source_path.write_text(
                __import__("json").dumps(artifact), encoding="utf-8"
            )

            result = reevaluator.reevaluate(
                source_path, dataset_path, output_path
            )
            row = result["models"]["model-a"]["results"][0]

            self.assertFalse(row["original_semantic_correct"])
            self.assertTrue(row["verifier_accepts"])
            self.assertTrue(row["reevaluated_semantic_correct"])
            self.assertEqual(row["verification_status"], "verified")
            self.assertTrue(row["verdict_changed"])
            self.assertEqual(
                result["summary"]["verdict_changed"], 1
            )
            self.assertEqual(result["summary"]["original_semantic_correct"], 0)
            self.assertEqual(result["summary"]["reevaluated_semantic_correct"], 1)
            self.assertEqual(result["source_artifact"]["sha256"],
                             reevaluator.file_sha256(source_path))
            self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
