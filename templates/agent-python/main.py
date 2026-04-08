
import asyncio
import aiohttp
import os
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("agent")

CORE_URL = os.getenv("CORE_URL", "http://hypercode-core:8000")
AGENT_NAME = os.getenv("AGENT_NAME", "generic-agent")
AGENT_DESCRIPTION = os.getenv("AGENT_DESCRIPTION", "A generic agent")
AGENT_TAGS = os.getenv("AGENT_TAGS", "generic").split(",")

class Agent:
    def __init__(self):
        self.id = None
        self.ws = None
        self.session = None

    async def register(self):
        """Register the agent with the Core."""
        payload = {
            "name": AGENT_NAME,
            "description": AGENT_DESCRIPTION,
            "version": "0.1.0",
            "endpoint": "http://localhost", # Placeholder
            "tags": AGENT_TAGS,
            "capabilities": []
        }
        
        async with self.session.post(f"{CORE_URL}/agents/register", json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                self.id = data["id"]
                logger.info(f"Registered with ID: {self.id}")
                return True
            else:
                logger.error(f"Registration failed: {resp.status} - {await resp.text()}")
                return False

    async def connect_ws(self):
        """Connect to the Core WebSocket channel."""
        if not self.id:
            return

        ws_url = f"{CORE_URL}/agents/{self.id}/channel".replace("http", "ws")
        try:
            async with self.session.ws_connect(ws_url) as ws:
                self.ws = ws
                logger.info("WebSocket connected")
                
                # Heartbeat loop
                while True:
                    await ws.send_str("ping")
                    msg = await ws.receive()
                    
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        if msg.data == "pong":
                            logger.debug("Heartbeat pong received")
                        else:
                            await self.on_message(msg.data)
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        break
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        break
                    
                    await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")

    async def on_message(self, message):
        """Handle incoming messages."""
        logger.info(f"Received message: {message}")

    async def start(self):
        """Main entry point."""
        async with aiohttp.ClientSession() as session:
            self.session = session
            if await self.register():
                while True:
                    await self.connect_ws()
                    logger.warning("WebSocket disconnected, reconnecting in 5s...")
                    await asyncio.sleep(5)

if __name__ == "__main__":
    agent = Agent()
    try:
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        sys.exit(0)
