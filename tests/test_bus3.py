import asyncio, uuid, sys, types

# Set up fake package so relative imports work
sys.path.insert(0, '/tmp')
pkg = types.ModuleType("agents")
sub = types.ModuleType("agents.shared")
sys.modules["agents"] = pkg
sys.modules["agents.shared"] = sub

import importlib.util, os

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "agents.shared"
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

am = load("agents.shared.agent_message", "/tmp/agent_message.py")
eb = load("agents.shared.event_bus",     "/tmp/event_bus.py")

HealEvent   = am.HealEvent
xp_to_level = am.xp_to_level
AgentEventBus = eb.AgentEventBus

async def test():
    bus = AgentEventBus("redis://redis:6379/0")
    await bus.connect()
    print("OK Redis connection: LIVE")

    heal = HealEvent(
        agent_id="healer-01",
        task_id=uuid.uuid4(),
        status="healing_success",
        healed_agent_id="hypercode-dashboard",
        heal_pattern="oom_restart",
        recurrence_count=1
    )
    subs = await bus.publish(heal)
    print(f"OK Published HealEvent | subscribers: {subs}")

    totals = await bus.award_xp("healer-01", xp=50, coins=10.0)
    level = xp_to_level(int(totals["xp_total"]))
    print(f"OK XP awarded | Total: {totals['xp_total']} XP | Level: {level}")

    history = await bus.get_event_history(agent_type="healer", limit=1)
    print(f"OK Event log: {history[0]['status']} from {history[0]['agent_id']}")
    print(f"OK Summary: {heal.summary()}")

    await bus.disconnect()
    print("")
    print("ALL TESTS PASSED - Event Bus is LIVE!")

asyncio.run(test())
