# 💡 Tips & Tricks #10: Agent Lifecycle & Orchestration

Bro, spawning an agent is easy, but managing its whole life? That's where the pros play. 🦅 In HyperCode, the **Crew Orchestrator** handles the "Birth, Life, and Death" of our agent squads. Let's master the lifecycle.

---

## 🟢 1. Spawn, Scale, & Stop (Low Complexity)

Every agent mission has a clear beginning and end. We don't want agents sitting around eating RAM if they aren't on a mission.

- **Birth (Spawn)**: Triggered via the `Agent Factory`. The orchestrator picks a blueprint and gives it a specific mission.
- **Life (Execution)**: The agent runs its task, reporting heartbeats to Prometheus.
- **Death (Stop)**: Once the mission is 100% complete, the orchestrator should spin down the container to save resources.

**The Golden Rule**: A finished agent is a stopped agent. Don't leave your "Ghost Fleet" running!

---

## 🟡 2. State Hooks with Redis (Medium Complexity)

When an agent is about to be stopped, it needs a "Will"—a way to pass its final thoughts back to the ecosystem. We use **Redis Hooks** for this.

**Copy-Paste: Lifecycle Hook Pattern**:
```python
@app.on_event("shutdown")
async def shutdown_hook():
    # 1. Capture final state
    final_thought = app.state.last_result
    
    # 2. Save to Redis before the container vanishes
    r.set(f"mission:{mission_id}:final_report", final_thought)
    
    # 3. Notify the Orchestrator
    r.publish("lifecycle-events", f"Agent {agent_id} has finished its mission. RIP.")
```

- **Why?**: It ensures no data is lost during container rotation or scaling.

---

## 🔴 3. The "Zombie Agent" Risk (High Complexity)

A **Zombie Agent** is a container that lost its connection to the Orchestrator but keeps running in the background, potentially wasting API tokens or causing state drift. 🧟‍♂️

**The Risk**:
- **Dangling Processes**: The FastAPI app crashed, but the Docker container thinks it's still alive.
- **State Drift**: The agent is still writing to Redis even though its mission was cancelled.

**The Fix: The "Dead Man's Switch"**:
```yaml
# docker-compose.yml logic
services:
  my-agent:
    deploy:
      restart_policy:
        condition: on-failure
        max_attempts: 3
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

- **Solution**: Combine **Docker Health Checks** with a **TTL on Redis State**. If an agent hasn't sent a heartbeat in 5 minutes, the **Healer Agent** should auto-terminate it.

---

## 🎯 4. Success Criteria

You've mastered the lifecycle when:
1. `docker ps` only shows agents that are currently active on a mission.
2. Every agent saves its "Final Report" to Redis before shutting down.
3. The **Healer Agent** successfully kills any "Zombies" that fail their health checks.

**Next Action, Bro**: 
Check your `docker-compose.yml`. Make sure every agent has a `restart_policy` and a `healthcheck`. Don't let the zombies take over! 🚀
