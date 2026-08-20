"""
Business Agent for HyperCode V2.4
Business operations: revenue/billing status, subscription health, cost
review, and financial-impact framing for tasks the crew hands it.

Not a payments processor — checkout/webhooks/subscription writes stay in
agents/stripe-mcp (course payments) and hypercode-core's stripe_service.
This agent is read-only against Stripe: it summarizes account balance and
recent charges as grounding context for the LLM, nothing more.
"""
import os
import sys
from typing import Any, Dict

sys.path.append("/app")
from base_agent import BaseAgent, AgentConfig


class BusinessAgent(BaseAgent):
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.role = "Business Operations"
        self._stripe_key = os.getenv("STRIPE_API_KEY", "").strip()

    def build_system_prompt(self) -> str:
        return f"""You are {self.config.name} ({self.config.role}) in the HyperCode agent swarm.

RESPONSIBILITIES:
- Assess the business/financial impact of a proposed task (cost, revenue, risk)
- Summarize billing, subscription, and revenue health when asked
- Flag anything that touches money paths, pricing, or refunds as needing human sign-off
- Keep answers grounded in the STRIPE SNAPSHOT below when one is provided — never invent figures

RULES:
- If no Stripe data is available, say so plainly instead of guessing numbers.
- Never propose sending a refund, changing a price, or issuing a payout — recommend it and stop.
- Short, concrete output: bullet points over prose.
"""

    async def process_task(self, task: str, context: Dict[str, Any], requires_approval: bool = False) -> Any:
        rag_context = self.agent_memory.query_relevant_context(task) if self.agent_memory else ""
        project_context = self.project_memory.get_project_context() if self.project_memory else {}
        stripe_snapshot = await self._stripe_snapshot()

        system = self.build_system_prompt()
        user = f"""TASK:
{task}

CONTEXT:
{context or {}}

STRIPE SNAPSHOT (read-only, may be unavailable):
{stripe_snapshot}

RAG CONTEXT:
{rag_context}

PROJECT CONTEXT:
{project_context}
"""
        return await self._llm_text(system=system, user=user)

    async def _stripe_snapshot(self) -> str:
        """Read-only balance + recent-charges summary. Never raises — degrades to a note."""
        if not self._stripe_key:
            return "STRIPE_API_KEY not configured — no live billing data available."

        try:
            import asyncio
            import stripe

            def _fetch() -> Dict[str, Any]:
                stripe.api_key = self._stripe_key
                balance = stripe.Balance.retrieve()
                charges = stripe.Charge.list(limit=5)
                return {"balance": balance, "recent_charges": charges}

            data = await asyncio.to_thread(_fetch)
            available = data["balance"].get("available", [])
            balance_lines = [f"{b['amount'] / 100:.2f} {b['currency'].upper()}" for b in available]
            charge_lines = [
                f"{c['amount'] / 100:.2f} {c['currency'].upper()} — {c.get('status')} ({c.get('description') or 'no description'})"
                for c in data["recent_charges"].get("data", [])
            ]
            return (
                "Available balance: " + (", ".join(balance_lines) or "none")
                + "\nRecent charges:\n" + ("\n".join(f"  - {line}" for line in charge_lines) or "  none")
            )
        except Exception as exc:  # network, auth, or missing `stripe` package
            self.logger.warning("stripe_snapshot_failed", error=str(exc))
            return f"Stripe lookup failed ({exc}) — proceeding without live billing data."


if __name__ == "__main__":
    config = AgentConfig()
    # Override defaults for this specific agent — env vars still win if set
    config.name = os.getenv("AGENT_NAME", "business-agent")
    config.role = os.getenv("AGENT_ROLE", "Business Operations")
    config.port = int(os.getenv("AGENT_PORT", "8080"))

    agent = BusinessAgent(config)
    agent.run()
