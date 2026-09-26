from .base import Agent, AgentContext


class HTMLCanvasAgent(Agent):
    agent_id = "html-canvas"

    def run(self, context: AgentContext) -> dict:
        return {
            "task_id": context.request["task_id"],
            "agent_id": self.agent_id,
            "status": "partial",
            "result": {"method": "html_canvas_adapter"},
            "artifacts": [],
            "claims": [],
            "evidence": [],
            "verification": {"status": "not_run"},
            "uncertainties": ["No HTML/JS execution backend is bound to this adapter yet."],
            "actions": [{"type": "capability", "name": "build_canvas"}],
            "metrics": {},
            "provenance": {"agent_id": self.agent_id, "adapter_version": "0.1"},
        }
