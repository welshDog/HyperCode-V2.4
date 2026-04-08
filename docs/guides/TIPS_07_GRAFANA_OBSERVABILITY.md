# 💡 Tips & Tricks #7: Grafana & Full-Stack Observability

Bro, if you can't see it, you can't fix it. 👁️ To keep the HyperCode ecosystem healthy, we use **Grafana** to visualize the pulse of our agents, Docker containers, and Redis bus. Let's get that dashboard glowing.

---

## 🟢 1. The Observability Stack (Low Complexity)

In HyperCode, we don't just "check logs." We use a specialized trio:
1. **Prometheus**: The data collector (scrapes metrics from your agents).
2. **Grafana**: The visualizer (the beautiful dashboard you see on `localhost:3001`).
3. **cAdvisor**: The container watcher (tells you how much CPU your Docker containers are eating).

- **Why?**: It gives you a "Bird's Eye View" of the entire system.
- **Access**: Hit `http://localhost:3001` to see your mission control.

---

## 🟡 2. Essential Queries & Panels (Medium Complexity)

You don't need to be a math genius to write queries. We use **PromQL**. Here are the "Big Three" queries every HyperCode dev needs.

**Copy-Paste these into Grafana Panels**:

**1. Agent Latency (FastAPI)**:
```promql
# Shows how long your agent takes to respond (95th percentile)
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, handler))
```

**2. Container CPU Usage**:
```promql
# Find out which agent is acting up and eating CPU
sum(rate(container_cpu_usage_seconds_total{name=~".+"}[5m])) by (name) * 100
```

**3. Redis Memory Usage**:
```promql
# Make sure your Redis cache isn't hitting the limit
redis_memory_used_bytes / redis_memory_max_bytes * 100
```

---

## 🔴 3. Setting Up Smart Alerts (High Complexity)

Don't stare at the screen all day. Let Grafana tell you when something's wrong. 🚨

**The Risk**: 
- **Alert Fatigue**: If you set alerts too sensitive, you'll start ignoring them. 
- **The "Dead Man's Switch"**: If Prometheus stops scraping, you won't get alerts. Always have a "Prometheus is Down" alert.

**Recommended Alert Strategy**:
1. **The "Unhealthy" Pulse**: Trigger if a container status = `unhealthy` for > 2 minutes.
2. **The "Memory Leak"**: Trigger if an agent's RAM usage > 80% for > 5 minutes.
3. **The "Slow Bro"**: Trigger if API latency > 2 seconds for 10% of requests.

---

## 🎯 4. Success Criteria

You've mastered the dashboard when:
1. You can see real-time CPU spikes when an agent starts a heavy mission.
2. Your panels are color-coded (Green = Good, Red = Problem).
3. You get a notification (Discord/Slack/Email) *before* you even notice a service is down.

**Next Action, Bro**: 
Open your dashboard at `localhost:3001`. Create one new "Stat" panel using the **Container CPU** query above. Watch it move! 🚀
