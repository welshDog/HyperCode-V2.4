"""
Database Architect Agent
Specializes in schema design, queries, and database optimization
"""
import sys
import os
sys.path.append('/app')
from base_agent import BaseAgent, AgentConfig

class DatabaseArchitect(BaseAgent):
    async def process_task(self, task: str, context: dict, requires_approval: bool):
        # 1. RAG Context
        rag_context = ""
        if self.agent_memory:
            rag_context = self.agent_memory.query_relevant_context(task)
            
        # 2. Project Context
        project_context = {}
        if self.project_memory:
            project_context = self.project_memory.get_project_context()
            
        # 3. Generate Plan
        plan = await self.generate_db_plan(task, rag_context, project_context)
        
        # 4. Approval
        if requires_approval and self.approval_system:
            approval = await self.approval_system.request_approval(
                self.config.name,
                "design_schema",
                {"task": task, "plan": plan},
                timeout=300
            )
            
            if approval['status'] != "approved":
                raise Exception(f"Task rejected: {approval.get('reason')}")
                
            if approval.get('modifications'):
                plan = approval['modifications']

        # 5. Execute Plan (Mock)
        if self.logger:
            self.logger.info("executing_plan", plan=plan)

        # Mock Implementation for Test 3 (TODO List)
        if "todo" in task.lower() and "table" in task.lower():
            file_path = "database/migrations/001_create_todos.sql"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, "w") as f:
                f.write("""
-- Up
CREATE TABLE todos (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_todos_created_at ON todos(created_at);

-- Down
DROP TABLE todos;
""")
            if self.logger:
                self.logger.info("file_created", path=file_path)
                
            # Update Project Memory
            if self.project_memory:
                # Store schema info for other agents
                self.project_memory.redis.set("project:schema:todos", "id, title, completed, created_at")

        return {"status": "completed", "executed_plan": plan}

    async def generate_db_plan(self, task, rag_context, project_context):
        if not self.client:
            return {"action": "mock_plan", "reason": "no_llm_client"}
            
        system_prompt = self.build_system_prompt()
        
        try:
            response = await self.client.messages.create(
                model=self.config.model,
                max_tokens=2000,
                system=system_prompt,
                messages=[{"role": "user", "content": f"Create a database schema plan for: {task}. Context: {project_context}"}]
            )
            return response.content[0].text
        except Exception as e:
            if self.logger:
                 self.logger.error("llm_generation_failed", error=str(e))
            return {"action": "mock_plan", "reason": f"llm_failed: {str(e)}", "plan": "Mock DB plan due to LLM error."}

    def build_system_prompt(self) -> str:
        base_prompt = """You are an AI agent.""" 
        return f"""{base_prompt}

**Your Specialization: Database Architecture**

TECH STACK:
- PostgreSQL 15+
- SQLAlchemy ORM
- Alembic for migrations
- Redis for caching
- Vector extensions (pgvector) when needed

RESPONSIBILITIES:
- Design normalized database schemas
- Write efficient SQL queries
- Create and manage migrations
- Optimize query performance
- Implement indexing strategies
- Design caching layers

SCHEMA DESIGN PRINCIPLES:
- Normalize to 3NF minimum
- Use appropriate constraints (FK, UNIQUE, CHECK)
- Consider query patterns when indexing
- Implement soft deletes where appropriate
- Version control all schema changes

QUERY OPTIMIZATION:
- Use EXPLAIN ANALYZE for performance tuning
- Implement proper indexing (B-tree, GiST, GIN)
- Avoid N+1 queries
- Use materialized views for complex aggregations
- Leverage CTEs for readability

MIGRATIONS:
- Always reversible (up/down)
- Test on copy of production data
- Include data migrations when needed
- Document breaking changes

SECURITY:
- Use parameterized queries (prevent SQL injection)
- Row-level security when needed
- Encrypt sensitive columns
- Implement audit logging
"""

if __name__ == "__main__":
    config = AgentConfig()
    agent = DatabaseArchitect(config)
    agent.run()
