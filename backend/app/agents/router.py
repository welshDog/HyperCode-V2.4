import logging
from app.agents.brain import brain
from app.agents.researcher import researcher
from app.agents.translator import translator
from app.agents.pulse import pulse
from app.agents.architect import architect

logger = logging.getLogger(__name__)

# Keywords that trigger the planning pipeline
_PLAN_KEYWORDS = (
    "generate plan",
    "create plan",
    "planning",
    "build plan",
    "make a plan",
    "coding plan",
    "produce plan",
)


class AgentRouter:
    """
    The Conductor: Routes tasks to the appropriate specialist agent.
    """
    def __init__(self):
        self.routes = {
            "research": researcher,
            "translate": translator,
            "health": pulse,
            "build": architect,
            "architect": architect
        }

    async def route_task(self, task_type: str, payload: str, context: dict = None) -> str:
        """
        Routes the task to the correct agent.
        Includes plan-keyword detection: if the payload requests a plan,
        PlanGenerator is invoked and the result returned directly.
        """
        context = context or {}
        conversation_id = context.get("conversation_id")
        if not conversation_id and context.get("task_id") is not None:
            conversation_id = f"task-{context.get('task_id')}"

        lower_payload = payload.lower()

        # ---- Plan keyword detection (before existing routing logic) ----
        if any(kw in lower_payload for kw in _PLAN_KEYWORDS) or task_type == "planning":
            logger.info("[Router] Plan keywords detected — invoking PlanGenerator.")
            try:
                from app.services.document_parser import document_parser
                from app.services.plan_generator import plan_generator
                from app.services.plan_formatter import format_plan_markdown
                from app.schemas.planning import DocumentInput, DocumentType

                doc_input = DocumentInput(
                    content=payload,
                    document_type=DocumentType.GENERIC,
                    metadata=context,
                )
                parsed_doc = await document_parser.parse(doc_input)
                plan = await plan_generator.generate_plan(parsed_doc, context=context)
                return format_plan_markdown(plan)
            except Exception as exc:
                logger.error(f"[Router] PlanGenerator failed: {exc}")
                return f"Error generating plan: {exc}"

        agent = self.routes.get(task_type)

        # Simple keyword detection if task_type is generic
        if not agent or task_type == "general":
            if "research" in lower_payload or "find" in lower_payload:
                agent = researcher
                task_type = "research"
            elif "translate" in lower_payload or "explain" in lower_payload:
                agent = translator
                task_type = "translate"
            elif "health" in lower_payload or "metrics" in lower_payload:
                agent = pulse
                task_type = "health"
            elif "build" in lower_payload or "create" in lower_payload or "design" in lower_payload:
                agent = architect
                task_type = "build"
            else:
                # Default behavior: Use the Brain with Context Recall
                logger.info(f"[Router] No specific agent found for '{task_type}', defaulting to HyperBrain.")
                return await brain.think(
                    "HyperBrain Specialist",
                    payload,
                    use_memory=True,
                    conversation_id=conversation_id,
                    agent_id="router",
                    memory_mode="shared" if conversation_id else "none",
                )

        logger.info(f"[Router] Routing task to {agent.__class__.__name__}...")

        # Dispatch based on agent interface
        if agent == researcher:
            return await researcher.process(payload, context, conversation_id=conversation_id)
        elif agent == architect:
            return await architect.process(payload, context, conversation_id=conversation_id)
        elif agent == translator:
            return await translator.process(payload, conversation_id=conversation_id)
        elif agent == pulse:
            return await pulse.process(payload, conversation_id=conversation_id)
        else:
            return await brain.think(
                "HyperBrain Specialist",
                payload,
                use_memory=True,
                conversation_id=conversation_id,
                agent_id="router",
                memory_mode="shared" if conversation_id else "none",
            )


# Global instance
router = AgentRouter()
