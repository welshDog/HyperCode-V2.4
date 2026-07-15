#!/bin/bash
# ========================================
# TRAE IDE — Agent Training & Communication Bridge
# Connects Trae IDE to Docker agents for real-time training
# ========================================

"""
TRAE IDE Integration for HyperCode Agent Squad
═══════════════════════════════════════════════════════════════════

This system bridges Trae IDE with your running Docker agents,
enabling real-time conversation, training, and skill development.

Quick Start:
  1. npm install -g @trae/cli
  2. trae init hypercode-agents
  3. trae connect http://localhost:8080
  4. trae train frontend-specialist
"""

import asyncio
import json
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# AGENT REGISTRY — All Docker Agents
# ─────────────────────────────────────────────────────────────────────────────

AGENT_REGISTRY = {
    "frontend-specialist": {
        "port": 8012,
        "role": "Senior Frontend Engineer",
        "capabilities": ["React", "Next.js", "Tailwind CSS", "Web Components"],
        "model": "claude-3-5-sonnet"
    },
    "backend-specialist": {
        "port": 8003,
        "role": "Senior Backend Engineer",
        "capabilities": ["FastAPI", "Python", "PostgreSQL", "REST APIs"],
        "model": "claude-3-opus"
    },
    "database-architect": {
        "port": 8004,
        "role": "Data Systems Architect",
        "capabilities": ["Schema Design", "Query Optimization", "Data Modeling"],
        "model": "claude-3-opus"
    },
    "qa-engineer": {
        "port": 8005,
        "role": "QA & Testing Specialist",
        "capabilities": ["Test Automation", "Performance Testing", "E2E Testing"],
        "model": "claude-3-sonnet"
    },
    "devops-engineer": {
        "port": 8006,
        "role": "DevOps & Infrastructure Specialist",
        "capabilities": ["Docker", "Kubernetes", "CI/CD", "Terraform"],
        "model": "claude-3-sonnet"
    },
    "coder-agent": {
        "port": 8002,
        "role": "Code Generation Agent",
        "capabilities": ["Multi-language", "Architecture Design", "Refactoring"],
        "model": "claude-3-5-sonnet"
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# TRAE IDE AGENT CLIENT
# ─────────────────────────────────────────────────────────────────────────────

class TraeAgentClient:
    """Bridge between Trae IDE and Docker agents."""
    
    def __init__(self, agent_name: str, base_url: str = "http://localhost"):
        self.agent_name = agent_name
        self.agent_config = AGENT_REGISTRY.get(agent_name)
        
        if not self.agent_config:
            raise ValueError(f"Agent '{agent_name}' not found in registry")
        
        self.agent_url = f"{base_url}:{self.agent_config['port']}"
        self.client = httpx.AsyncClient(timeout=30.0)
        self.session_id = None
        self.history = []
    
    async def connect(self) -> bool:
        """Establish connection to running Docker agent."""
        try:
            response = await self.client.get(f"{self.agent_url}/health")
            if response.status_code == 200:
                logger.info(f"✓ Connected to {self.agent_name} at {self.agent_url}")
                self.session_id = datetime.now().isoformat()
                return True
        except Exception as e:
            logger.error(f"✗ Failed to connect to {self.agent_name}: {e}")
        return False
    
    async def send_message(self, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Send training/chat message to agent."""
        try:
            payload = {
                "message": message,
                "session_id": self.session_id,
                "context": context or {},
                "timestamp": datetime.now().isoformat()
            }
            
            response = await self.client.post(
                f"{self.agent_url}/chat",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                self.history.append({
                    "role": "user",
                    "content": message,
                    "timestamp": datetime.now().isoformat()
                })
                self.history.append({
                    "role": "assistant",
                    "content": result.get("response", ""),
                    "timestamp": datetime.now().isoformat()
                })
                return result
        except Exception as e:
            logger.error(f"✗ Error communicating with agent: {e}")
        
        return {"error": "Failed to get response"}
    
    async def train(self, training_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send training data to agent for skill development."""
        payload = {
            "action": "train",
            "training_data": training_data,
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            response = await self.client.post(
                f"{self.agent_url}/train",
                json=payload
            )
            return response.json() if response.status_code == 200 else {"error": "Training failed"}
        except Exception as e:
            logger.error(f"✗ Training error: {e}")
            return {"error": str(e)}
    
    async def get_status(self) -> Dict[str, Any]:
        """Get agent status and capabilities."""
        try:
            response = await self.client.get(f"{self.agent_url}/status")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"✗ Status check failed: {e}")
        return {}
    
    async def close(self):
        """Close connection."""
        await self.client.aclose()

# ─────────────────────────────────────────────────────────────────────────────
# TRAE IDE SESSION MANAGER
# ─────────────────────────────────────────────────────────────────────────────

class TraeSessionManager:
    """Manage multi-agent training sessions."""
    
    def __init__(self):
        self.sessions: Dict[str, TraeAgentClient] = {}
        self.training_log = []
    
    async def create_session(self, agent_name: str) -> Optional[TraeAgentClient]:
        """Create new agent session."""
        try:
            client = TraeAgentClient(agent_name)
            if await client.connect():
                self.sessions[agent_name] = client
                logger.info(f"✓ Session created for {agent_name}")
                return client
        except Exception as e:
            logger.error(f"✗ Failed to create session: {e}")
        return None
    
    async def multi_agent_chat(self, message: str, agents: List[str]) -> Dict[str, Any]:
        """Send message to multiple agents (collaborative training)."""
        results = {}
        
        for agent_name in agents:
            if agent_name not in self.sessions:
                await self.create_session(agent_name)
            
            client = self.sessions.get(agent_name)
            if client:
                response = await client.send_message(message)
                results[agent_name] = response
        
        return results
    
    async def record_training(self, agent_name: str, training_data: Dict) -> None:
        """Log training session for later review."""
        log_entry = {
            "agent": agent_name,
            "timestamp": datetime.now().isoformat(),
            "training_data": training_data
        }
        self.training_log.append(log_entry)
    
    async def close_all(self):
        """Close all agent sessions."""
        for client in self.sessions.values():
            await client.close()

# ─────────────────────────────────────────────────────────────────────────────
# TRAE IDE INTERACTIVE TERMINAL
# ─────────────────────────────────────────────────────────────────────────────

async def trae_interactive_session():
    """Interactive Trae IDE terminal for training agents."""
    
    manager = TraeSessionManager()
    
    print("\n" + "="*60)
    print("TRAE IDE — HyperCode Agent Training Interface")
    print("="*60)
    print("\nAvailable Agents:")
    for agent_name, config in AGENT_REGISTRY.items():
        print(f"  • {agent_name} ({config['role']})")
    
    print("\nCommands:")
    print("  chat <agent> <message>     — Chat with single agent")
    print("  train <agent> <skill>      — Train agent on skill")
    print("  team <message>             — Chat with all agents")
    print("  list                       — List all agents")
    print("  status <agent>             — Check agent status")
    print("  quit                       — Exit")
    
    try:
        while True:
            user_input = input("\ntrae> ").strip()
            
            if not user_input:
                continue
            
            parts = user_input.split(maxsplit=1)
            command = parts[0].lower()
            
            if command == "quit":
                break
            
            elif command == "list":
                print("\n📋 Registered Agents:")
                for agent_name, config in AGENT_REGISTRY.items():
                    print(f"  {agent_name}: {config['role']}")
            
            elif command == "chat" and len(parts) > 1:
                args = parts[1].split(maxsplit=1)
                if len(args) >= 2:
                    agent_name, message = args[0], args[1]
                    if agent_name in AGENT_REGISTRY:
                        client = await manager.create_session(agent_name)
                        if client:
                            print(f"\n💭 {agent_name}:")
                            response = await client.send_message(message)
                            print(f"   {response.get('response', 'No response')}")
                    else:
                        print(f"✗ Agent '{agent_name}' not found")
            
            elif command == "team" and len(parts) > 1:
                message = parts[1]
                print(f"\n🤝 Sending to all agents: '{message}'")
                results = await manager.multi_agent_chat(message, list(AGENT_REGISTRY.keys()))
                for agent_name, response in results.items():
                    print(f"  {agent_name}: {response.get('response', 'No response')[:100]}...")
            
            elif command == "status" and len(parts) > 1:
                agent_name = parts[1]
                if agent_name in AGENT_REGISTRY:
                    client = await manager.create_session(agent_name)
                    if client:
                        status = await client.get_status()
                        print(f"\n✓ {agent_name} Status:")
                        print(json.dumps(status, indent=2))
                else:
                    print(f"✗ Agent '{agent_name}' not found")
            
            elif command == "train" and len(parts) > 1:
                args = parts[1].split(maxsplit=1)
                if len(args) >= 2:
                    agent_name, skill = args[0], args[1]
                    if agent_name in AGENT_REGISTRY:
                        client = await manager.create_session(agent_name)
                        if client:
                            print(f"\n🎓 Training {agent_name} on: {skill}")
                            result = await client.train({"skill": skill})
                            print(f"   {result}")
                    else:
                        print(f"✗ Agent '{agent_name}' not found")
            
            else:
                print("✗ Unknown command. Type 'help' for commands.")
    
    finally:
        await manager.close_all()
        print("\n✓ Session closed")

# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    asyncio.run(trae_interactive_session())
