import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"


class SchemaContractTests(unittest.TestCase):
    def load(self, name):
        with (SCHEMA_DIR / name).open(encoding="utf-8") as handle:
            return json.load(handle)

    def test_all_agent_schemas_are_valid_json_schema_documents(self):
        names = [
            "depth_profile.json",
            "verification_policy.json",
            "agent_request.json",
            "agent_result.json",
            "task_node.json",
            "task_graph.json",
        ]
        for name in names:
            schema = self.load(name)
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertEqual(schema["type"], "object")
            self.assertIn("properties", schema)
            self.assertIn("required", schema)

    def test_depth_profile_has_exact_dimensions_and_bounds(self):
        schema = self.load("depth_profile.json")
        dimensions = {
            "rigor", "prerequisites", "formalism", "proof",
            "research", "visualization", "experimentation", "generalization",
        }
        self.assertEqual(set(schema["properties"]), dimensions)
        self.assertEqual(set(schema["required"]), dimensions)
        for prop in schema["properties"].values():
            self.assertEqual(prop["type"], "integer")
            self.assertEqual(prop["minimum"], 0)
            self.assertEqual(prop["maximum"], 100)

    def test_request_result_and_graph_contract_fields(self):
        request = self.load("agent_request.json")
        result = self.load("agent_result.json")
        node = self.load("task_node.json")
        graph = self.load("task_graph.json")
        self.assertEqual(set(request["required"]), {
            "task_id", "objective", "input", "constraints", "depth_profile",
            "requested_artifacts", "verification_requirements", "context_refs", "budget",
        })
        self.assertEqual(set(result["required"]), {
            "task_id", "agent_id", "status", "result", "artifacts", "claims",
            "evidence", "verification", "uncertainties", "actions", "metrics", "provenance",
        })
        self.assertIn("verification_policy.json", json.dumps(node))
        self.assertIn("task_node.json", json.dumps(graph))

    def test_status_and_failure_policy_enums_are_frozen(self):
        result = self.load("agent_result.json")
        node = self.load("task_node.json")
        policy = self.load("verification_policy.json")
        self.assertEqual(
            result["properties"]["status"]["enum"],
            ["completed", "partial", "failed", "blocked"],
        )
        self.assertEqual(
            node["properties"]["status"]["enum"],
            ["pending", "running", "completed", "partial", "failed", "blocked"],
        )
        self.assertEqual(
            policy["properties"]["on_failure"]["enum"],
            ["fail", "critique", "repair", "block"],
        )


if __name__ == "__main__":
    unittest.main()
