import logging
from app.agents.brain import brain

logger = logging.getLogger(__name__)

class TranslatorAgent:
    """
    The Visualizer: Translates standard code into HyperCode's spatial, chunked logic.
    """
    def __init__(self):
        self.role = "Translator Specialist"
    
    async def process(self, code_payload: str, conversation_id: str | None = None) -> str:
        """
        Translates code into a more accessible format using HyperCode Spatial Logic.
        """
        logger.info(f"[{self.role}] 🎨 Synthesizing code into HyperCode Spatial Logic...")
        
        prompt = f"""
        You are the HyperCode Translator Agent. Your job is to translate standard code into 'HyperCode Spatial Logic', specifically designed for neurodivergent (ADHD/Dyslexic) brains.

        RULES FOR YOUR OUTPUT:
        1. 🎨 Visual Anchors: Use emojis for functions (⚙️), loops (🔄), variables (📦), and logic gates (🔀).
        2. 🧱 Chunking: Break the code into small, isolated blocks with clear headings.
        3. 🚫 Zero Noise: Strip out 90% of syntax jargon. Tell me what it *does* in plain, punchy English.
        4. 🗺️ Spatial Flow: Explain the flow as a visual journey (e.g., "Block A ➡️ passes data to ➡️ Block B").

        Here is the neurotypical code to translate:
        
        {code_payload}
        """
        
        return await brain.think(
            self.role,
            prompt,
            conversation_id=conversation_id,
            agent_id="translator",
            memory_mode="self" if conversation_id else "none",
        )

# Global instance
translator = TranslatorAgent()
