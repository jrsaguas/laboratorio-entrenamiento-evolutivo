from .base import Agent, AgentContext


class MathReasoningAgent(Agent):
    agent_id = "math-reasoning"

    def run(self, context: AgentContext) -> dict:
        request = context.request
        result = {
            "problem": request["input"],
            "method": "reasoning_adapter",
            "message": "Math reasoning execution point established; solver not yet bound.",
        }
        return {
            "task_id": request["task_id"],
            "agent_id": self.agent_id,
            "status": "partial",
            "result": result,
            "artifacts": [],
            "claims": [],
            "evidence": [],
            "verification": {"status": "not_run"},
            "uncertainties": ["No mathematical solver is bound to this adapter yet."],
            "actions": [{"type": "capability", "name": "solve_math"}],
            "metrics": {},
            "provenance": {"agent_id": self.agent_id, "adapter_version": "0.1"},
        }
