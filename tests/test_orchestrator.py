import tempfile
import unittest
from pathlib import Path

from orchestrator import Orchestrator, OrchestrationError


def request():
    return {
        "task_id": "orch-test-001",
        "objective": "Construye una visualización matemática.",
        "input": "z = x² + y²",
        "constraints": {"artifact_dir": str(Path(tempfile.gettempdir()) / "laboratorio-evolutivo-tests")},
        "depth_profile": {
            "rigor": 50, "prerequisites": 50, "formalism": 50, "proof": 50,
            "research": 0, "visualization": 80, "experimentation": 20,
            "generalization": 50,
        },
        "requested_artifacts": ["surface-z-x2-y2.svg"],
        "verification_requirements": {
            "required": True, "verifiers": [], "on_failure": "fail",
            "max_retries": 0, "require_provenance": True,
        },
        "context_refs": [],
        "budget": {},
    }


