
"""
Tips & Tricks Writer Agent for HyperCode V2.0
Specializes in generating neurodivergent-friendly development guides.
"""
import os
import sys
from typing import Dict, Any

# Add project root to path for shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import BaseAgent and necessary classes
# Note: In the container, /app will be the project root
sys.path.append('/app')
try:
    from agents.base_agent.agent import BaseAgent, AgentConfig
except ImportError:
    # Local development fallback
    from base_agent.agent import BaseAgent, AgentConfig

class TipsTricksWriterAgent(BaseAgent):
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.role = "Tips & Tricks Architect"
        self.backstory = "Expert in technical writing and neurodivergent-friendly UX. Built by Lyndz to fill the documentation gap."

    async def process_task(self, task: str, context: Dict[str, Any], requires_approval: bool):
        """
        Specialized logic for generating Tips & Tricks guides.
        """
        self.logger.info("generating_tips_tricks", task=task)
        
        # 1. Gather context
        rag_context = ""
        if self.agent_memory:
            rag_context = await self.agent_memory.query_relevant_context(task)
            
        # 2. Project context
        project_context = {}
        if self.project_memory:
            project_context = await self.project_memory.get_project_context()

        # 3. Generate the Guide
        guide_content = await self.generate_neurodivergent_guide(task, rag_context, project_context)
        
        # 4. Save the guide to a file (optional, but good for persistence)
        # We'll return it as the result for now
        
        return {
            "title": f"Tips & Tricks: {task}",
            "content": guide_content,
            "format": "neurodivergent-friendly",
            "status": "draft"
        }

    async def generate_neurodivergent_guide(self, topic: str, rag_context: str, project_context: Dict[str, Any]):
        """
        Uses the LLM to generate a chunked, bulleted, bolded guide.
        """
        if not self.client:
            return "No LLM client configured. Bro, check your API keys!"

        system_prompt = f"""
        You are the {self.config.name}, a specialist in the HyperCode V2.0 ecosystem.
        Your soul is dedicated to making complex tech easy for neurodivergent brains (ADHD/Dyslexia).

        RULES FOR OUTPUT:
        1. Chunked output - no walls of text.
        2. Bullet points + numbered steps always.
        3. Code in code blocks only.
        4. Bold the key concept in every bullet.
        5. Keep tone casual and mate-style ("bro, let's go").
        6. Use emoji visual cues (🟢🟡🔴).
        7. Short sentences (<20 words).
        8. Clear headings every 3-5 lines.
        9. No jargon without definitions.
        10. Generous whitespace.

        TOPIC: {topic}
        """

        prompt = f"""
        BRO, we need a legendary "Tips & Tricks" guide for: {topic}.
        
        CONTEXT FROM BIBLE:
        {rag_context}
        
        PROJECT STATUS:
        {project_context}
        
        Write the guide now. Make it pure signal, no noise.
        """

        response = await self.client.messages.create(
            model=self.config.model,
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text

if __name__ == "__main__":
    config = AgentConfig()
    # Override defaults for this specific agent
    config.name = "tips-tricks-writer"
    config.role = "Tips & Tricks Writer"
    config.port = 8009
    
    agent = TipsTricksWriterAgent(config)
    agent.run()
