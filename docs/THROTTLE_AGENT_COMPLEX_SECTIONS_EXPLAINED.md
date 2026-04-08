# 🔬 THROTTLE-AGENT: DETAILED COMPLEX SECTIONS EXPLAINED

**Detailed Analysis of Unclear/Complex Code**  
**Date**: March 19, 2026  
**Audience**: Developers extending or maintaining throttle-agent

---

## 📍 SECTION 1: LINEAR REGRESSION PREDICTION

**Location**: `_predict_ram_usage()` (Lines 366-398 in main.py)  
**Complexity Level**: ⚠️ MODERATE  
**Why Complex**: Requires understanding linear regression math

### The Problem

We want to predict RAM usage 5 minutes in the future to pause tiers proactively.

```
Current time: 12:00:00, RAM = 72%
History: [70, 71, 72, 73, 74]  (trending up)
Question: What will RAM be at 12:05:00?
```

### The Solution: Linear Regression

**Concept**: Fit a straight line through the data points, then extrapolate forward.

```
                    Extrapolate forward
                            ↓
Data points:    •  (actual measurements)
Regression line: __________→ (predicted trend)

If trending up 2% per measurement:
  Current: 74%
  +10 measurements: 74 + (2 * 10) = 94%
```

### Step-by-Step Explanation

**Step 1: Collect Recent Data**
```python
recent_values = list(ram_history)[-5:]  # Last 5 measurements
# Example: [70, 71, 72, 73, 74]
```

**Step 2: Create X-Axis (Time Points)**
```python
x_values = list(range(n))  # [0, 1, 2, 3, 4]
# Each index represents one measurement interval
```

**Step 3: Calculate Means**
```python
x_mean = sum(x_values) / n  # (0+1+2+3+4) / 5 = 2.0
y_mean = sum(recent_values) / n  # (70+71+72+73+74) / 5 = 72.0
```

**Step 4: Calculate Trend (Slope)**

The slope formula: `m = Σ((x - x_mean) * (y - y_mean)) / Σ((x - x_mean)²)`

```python
# Numerator calculation
numerator = sum((x_values[i] - x_mean) * (recent_values[i] - y_mean) for i in range(n))

# Breakdown:
# i=0: (0 - 2.0) * (70 - 72.0) = (-2.0) * (-2.0) = 4.0
# i=1: (1 - 2.0) * (71 - 72.0) = (-1.0) * (-1.0) = 1.0
# i=2: (2 - 2.0) * (72 - 72.0) = (0.0) * (0.0) = 0.0
# i=3: (3 - 2.0) * (73 - 72.0) = (1.0) * (1.0) = 1.0
# i=4: (4 - 2.0) * (74 - 72.0) = (2.0) * (2.0) = 4.0
# Sum = 4.0 + 1.0 + 0.0 + 1.0 + 4.0 = 10.0

# Denominator calculation
denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))

# Breakdown:
# (0-2.0)² = 4.0
# (1-2.0)² = 1.0
# (2-2.0)² = 0.0
# (3-2.0)² = 1.0
# (4-2.0)² = 4.0
# Sum = 10.0

slope = numerator / denominator  # 10.0 / 10.0 = 1.0
# Interpretation: RAM increases by 1% per measurement
```

**Step 5: Convert Time to Measurements**
```python
# User asked: predict 5 minutes ahead
# System polls every POLL_INTERVAL_SECONDS = 30
# 5 minutes = 300 seconds
# 300 seconds ÷ 30 seconds per poll = 10 measurements

steps_ahead = max(int(round((5 * 60) / 30)), 1)
# (5 * 60) = 300 seconds
# 300 / 30 = 10
```

**Step 6: Extrapolate**
```python
predicted = recent_values[-1] + (slope * steps_ahead)
# Current: 74%
# Slope: 1% per measurement
# Steps: 10
# Predicted: 74 + (1 * 10) = 84%
```

### Complete Example

```
Given:
  recent_values = [70, 71, 72, 73, 74]
  POLL_INTERVAL_SECONDS = 30
  minutes_ahead = 5

Process:
  1. x_values = [0, 1, 2, 3, 4]
  2. x_mean = 2.0
  3. y_mean = 72.0
  4. numerator = 10.0
  5. denominator = 10.0
  6. slope = 1.0 (% per measurement)
  7. steps_ahead = 10 (measurements in 5 minutes)
  8. predicted = 74 + (1.0 * 10) = 84%

Result: RAM will be ~84% in 5 minutes
Action: If threshold is 80%, this triggers warning!
```

### Common Issues & Fixes

**Issue 1: Not Enough History**
```python
if len(ram_history) < 3:
    return None  # Need minimum data for trend
```

**Issue 2: Flat Data (No Trend)**
```python
if denominator == 0:  # All x values are the same (shouldn't happen)
    return recent_values[-1]  # Return current value, no trend
```

**Issue 3: Negative Prediction (RAM dropped)**
```python
return round(max(0, predicted), 2)  # Clamp to 0% minimum
```

### Real-World Scenarios

**Scenario 1: Steady Growth**
```
History: [60, 65, 70, 75, 80]
Slope: 5% per measurement
Predict 10 measurements: 80 + (5 * 10) = 130% → clamped to 100%
Action: Emergency throttle tier 4!
```

**Scenario 2: Stable System**
```
History: [75, 75, 75, 75, 75]
Slope: 0% per measurement (flat)
Predict 10 measurements: 75 + (0 * 10) = 75%
Action: No change needed
```

**Scenario 3: Memory Leak**
```
History: [50, 60, 70, 80, 90]
Slope: 10% per measurement
Predict 5 measurements: 90 + (10 * 5) = 140% → clamped to 100%
Action: Critical! Pause tier 4
```

---

## 📍 SECTION 2: CPU PERCENTAGE CALCULATION

**Location**: `_record_container_advanced_stats()` (Lines 400-418)  
**Complexity Level**: ⚠️ MODERATE  
**Why Complex**: Docker stats API formula not intuitive

### The Problem

Docker provides raw CPU tick counters, but we need a human-readable percentage.

```
Container stats include:
  - cpu_stats.cpu_usage.total_usage (container's total CPU ticks)
  - precpu_stats.cpu_usage.total_usage (previous measurement)
  - cpu_stats.system_cpu_usage (system's total CPU ticks)
  - precpu_stats.system_cpu_usage (previous measurement)

Question: How do we convert these to a percentage?
```

### Docker's CPU Formula

From [Docker API Documentation](https://docs.docker.com/engine/api/v1.43/#operation/ContainerStats):

```
cpu_percent = (cpu_delta / system_delta) * 100.0 * number_cpus

Where:
  cpu_delta = change in container's total CPU ticks
  system_delta = change in system's total CPU ticks
  number_cpus = number of CPUs the container can use
```

### Understanding the Formula

**Analogy: Gas Tank Gauge**

Imagine the system as a gas tank with 4 tanks (4 CPUs):
- Each CPU generates tick events at a constant rate
- Container consumes some ticks
- We measure: how many ticks did the container consume vs. how many were available?

```
System 10ms of time:
  Each CPU generates ~10,000,000 ticks
  Total across 4 CPUs: 40,000,000 ticks (system_delta)

Container in same 10ms:
  Consumed 10,000,000 ticks (cpu_delta)
  
CPU% = (10,000,000 / 40,000,000) * 100 * 4
      = 0.25 * 100 * 4
      = 100%
      (Full consumption on 4-core system = 100%)
```

### Step-by-Step Calculation

**Step 1: Extract Stats**
```python
stats = container.stats(stream=False)  # Single snapshot

cpu_stats = stats.get("cpu_stats", {})
# {
#   "cpu_usage": {"total_usage": 1234567890},
#   "system_cpu_usage": 9876543210,
#   "online_cpus": 4
# }

prev_cpu_stats = stats.get("precpu_stats", {})
# {
#   "cpu_usage": {"total_usage": 1234567800},
#   "system_cpu_usage": 9876543100
# }
```

**Step 2: Calculate Deltas**
```python
# How much CPU did the container use since last measurement?
cpu_delta = 1234567890 - 1234567800 = 90 ticks

# How much CPU was available in the system?
system_delta = 9876543210 - 9876543100 = 110 ticks
```

**Step 3: Get CPU Count**
```python
cpu_count = cpu_stats.get("online_cpus", 1) or len(cpu_stats.get("cpus", [0]))

# Fallback logic (if online_cpus not available):
# Try to count CPUs from the "cpus" list
# Default to 1 if all else fails
```

**Step 4: Calculate Percentage**
```python
if system_delta > 0:
    cpu_percent = (cpu_delta / system_delta) * 100.0 * cpu_count
    # (90 / 110) * 100 * 4
    # = 0.818 * 100 * 4
    # = 327.3%
    # (Can exceed 100% on multi-core systems!)

CONTAINER_CPU_PERCENT.labels(name=container_name).set(round(cpu_percent, 2))
# Result: 327.3% CPU on 4-core system
```

### Real-World Examples

**Example 1: Container Using 1 Core on 4-Core System**
```
cpu_delta = 100,000 ticks
system_delta = 400,000 ticks (available across 4 cores)
cpu_count = 4

cpu_percent = (100,000 / 400,000) * 100 * 4
            = 0.25 * 100 * 4
            = 100%
```

**Example 2: Container Using 2 Cores on 4-Core System**
```
cpu_delta = 200,000 ticks
system_delta = 400,000 ticks
cpu_count = 4

cpu_percent = (200,000 / 400,000) * 100 * 4
            = 0.5 * 100 * 4
            = 200%
```

**Example 3: Container Using Less Than 1 Core**
```
cpu_delta = 50,000 ticks
system_delta = 400,000 ticks
cpu_count = 4

cpu_percent = (50,000 / 400,000) * 100 * 4
            = 0.125 * 100 * 4
            = 50%
```

### Common Misconceptions

**Q: Why can CPU% exceed 100%?**
A: Because a multi-core system has multiple CPUs. 100% on a 4-core system means 1 full core.

**Q: What if system_delta is 0?**
A: Docker stats are identical (very rare). Skip this measurement and use previous value.

**Q: Why use ticks instead of time?**
A: Ticks are more accurate than wall-clock time (immune to clock adjustments).

### Network Stats (Simpler)

```python
# Network stats are straightforward byte counts
networks = stats.get("networks", {})
# {
#   "eth0": {"rx_bytes": 1000000, "tx_bytes": 500000},
#   "eth1": {"rx_bytes": 2000000, "tx_bytes": 1000000}
# }

# Sum bytes across all networks
rx_bytes = sum(net.get("rx_bytes", 0) for net in networks.values())
# 1000000 + 2000000 = 3000000

tx_bytes = sum(net.get("tx_bytes", 0) for net in networks.values())
# 500000 + 1000000 = 1500000
```

---

## 📍 SECTION 3: AUTOPILOT STATE MACHINE

**Location**: `_autopilot_cycle_sync()` (Lines 485-560)  
**Complexity Level**: ⚠️ MODERATE  
**Why Complex**: 5 state transitions with timing logic

### The State Machine

```
                    ┌─────────────┐
                    │   RUNNING   │ (Initial state)
                    └──────┬──────┘
                           │ Autopilot loop invokes
                           ▼
                    ┌─────────────┐
                    │   POLLING   │ (Measure RAM%)
                    └──────┬──────┘
                           │ Measurement complete
                           ▼
                    ┌─────────────┐
                    │  ANALYZING  │ (Determine desired pause set)
                    └──────┬──────┘
                           │ Analysis complete
                           ▼
                    ┌─────────────┐
                    │  EXECUTING  │ (Pause/resume tiers)
                    └──────┬──────┘
                           │ Execution complete
                           ▼
                    ┌─────────────┐
              ┌────►│   WAITING   │◄────┐ (Async sleep)
              │     └──────┬──────┘     │
              │            │            │
              └────────────┴────────────┘
                 (Loop every 30s)
```

### Global State Variables

```python
_autopilot_paused_tiers: set[int] = set()      # Which tiers are paused
_autopilot_below_since: float | None = None    # When RAM dropped below 75%
_paused_since: dict[str, float] = {}           # When each container was paused
_last_ram_pct: float | None = None             # Current RAM%
```

### State: RAM Measurement

**Code**:
```python
_last_ram_pct = _estimate_system_ram_pct(client, tiers_cfg)
if _last_ram_pct is not None:
    SYSTEM_RAM_USAGE_PCT.set(_last_ram_pct)
    ram_history.append(_last_ram_pct)  # Add to history for predictions
```

**Outcome**: `_last_ram_pct` = current system RAM percentage

### State: Decision Making

**Decision Tree**:
```
if RAM >= 95%:
    desired_pause = [6, 5, 4]  # EMERGENCY
elif RAM >= 90%:
    desired_pause = [6, 5]     # HIGH
elif RAM >= 80%:
    desired_pause = [6]        # WARN
else:
    desired_pause = []         # NORMAL

# Apply observability keep rule
if THROTTLE_KEEP_OBSERVABILITY and RAM < 90%:
    desired_pause = [t for t in desired_pause if t != 5]
```

**Example Scenarios**:
```
Scenario 1: RAM = 82%
  - Initial desired: [6]
  - Keep observability enabled, RAM < 90%: no change
  - Final desired: [6]

Scenario 2: RAM = 92%
  - Initial desired: [6, 5]
  - Keep observability enabled, RAM < 90%: False (skip keep rule)
  - Final desired: [6, 5]

Scenario 3: RAM = 98%
  - Initial desired: [6, 5, 4]
  - Keep observability enabled, RAM < 90%: False
  - Final desired: [6, 5, 4]
```

### State: Pause Execution

**Code**:
```python
for tier in desired_pause:
    if tier in THROTTLE_PROTECT_TIERS:      # Skip tier 1-3 (always protected)
        continue
    if tier in _autopilot_paused_tiers:     # Already paused
        continue
    
    _pause_tier_sync(client, tier)           # Actually pause
    _autopilot_paused_tiers.add(tier)        # Remember we paused this
    logger.info(f"Paused tier {tier}")
```

**Transition**: `_autopilot_paused_tiers` updated to reflect paused tiers

### State: Resume Waiting

**Core Logic**: "Wait 5 minutes with RAM below 75% before resuming"

```python
if ram_pct < THROTTLE_RESUME_BELOW:  # 75%
    if _autopilot_below_since is None:
        _autopilot_below_since = time.time()  # Start timer
        logger.info(f"Resume timer started")
else:
    _autopilot_below_since = None  # Reset timer if RAM goes back up
```

**State Transitions**:
```
Cycle 1: RAM = 82%
  └─ Above 75%, _autopilot_below_since = None

Cycle 2: RAM = 78%
  └─ Still above 75%, _autopilot_below_since = None

Cycle 3: RAM = 72% (drops below 75%)
  └─ Below 75%, _autopilot_below_since = time.time() (mark time)

Cycle 4-10: RAM stays 70-74%
  └─ Below 75%, timer still running

Cycle 11: RAM = 71%, timer >= 5 minutes
  └─ Below 75% AND held long enough, RESUME all tiers!

Cycle 12: RAM = 72%
  └─ Now above 75%, _autopilot_below_since = None
```

### State: Resume Execution

**Code**:
```python
if _autopilot_paused_tiers and _autopilot_below_since is not None:
    hold_seconds = max(THROTTLE_RESUME_HOLD_MINUTES, 1) * 60  # 300 seconds
    elapsed = time.time() - _autopilot_below_since
    
    if elapsed >= hold_seconds:  # 5 minutes passed?
        for tier in [4, 5, 6]:  # Resume in order
            if tier in _autopilot_paused_tiers:
                _resume_tier_sync(client, tier)
                _autopilot_paused_tiers.remove(tier)
        
        if not _autopilot_paused_tiers:
            _autopilot_below_since = None  # Reset timer
```

### Why 5-Minute Hold?

**Problem without hold (thrashing)**:
```
Cycle 1: RAM 85% → Pause tier 6 (-2%)
Cycle 2: RAM 83% → Still paused
Cycle 3: RAM 72% → Resume tier 6 (+4%)
Cycle 4: RAM 83% → Pause again (THRASHING!)
```

**Solution with 5-minute hold**:
```
Cycle 1: RAM 85% → Pause tier 6
Cycles 2-10: Wait 5 minutes...
  RAM stays 75-80% while paused
  After 5 min stable: Resume
Cycles 11+: RAM stays stable at 75% (no thrashing)
```

**Key Insight**: Hold time allows system to stabilize after pause.

---

## 📍 SECTION 4: HEALER CIRCUIT BREAKER INTEGRATION

**Location**: `_healer_allows_resume()` (Lines 464-475)  
**Complexity Level**: ⚠️ LOW-MODERATE  
**Why Complex**: Interaction with external service state

### The Problem

When we want to resume a container, we need to know:
- Is the container in a failure state?
- Is there an active incident preventing resumption?

We can't just unpause it blindly.

### Circuit Breaker Pattern

The **Circuit Breaker** pattern prevents repeatedly calling a broken service:

```
         ┌──────────────┐
         │    CLOSED    │ (Working normally)
         │  (Service OK)│
         └──────┬───────┘
                │ Failures detected
                ▼
         ┌──────────────┐
         │    OPEN      │ (Failing, block calls)
         │  (Service    │
         │  Down/Error) │
         └──────┬───────┘
                │ Timeout (e.g., 60 sec)
                ▼
         ┌──────────────┐
         │ HALF-OPEN    │ (Testing recovery)
         │ (Trial calls)│
         └──────┬───────┘
                │ Success: Close circuit
                │ Failure: Reopen circuit
```

### How throttle-agent Uses It

**Step 1: Check Circuit State**
```python
def _healer_allows_resume(container: str) -> bool:
    """Ask healer: is it safe to resume this container?"""
    try:
        r = httpx.get(
            f"{HEALER_URL}/circuit-breaker/{container}",
            timeout=2.0
        )
        if r.status_code != 200:
            return True  # Can't reach healer, assume OK
        
        data = r.json()  # {"state": "open|closed|half-open"}
        return data.get("state") != "open"  # False if circuit open
    except Exception:
        return True  # Network error, assume OK
```

**Step 2: Use in Resume Decision**
```python
def _resume_tier_sync(client, tier):
    for name in targets:
        if not _healer_allows_resume(name):  # Check circuit!
            skipped.append(name)  # Don't resume if circuit open
            continue
        
        container.unpause()  # Safe to resume
        changed.append(name)
```

**Step 3: Return Skipped List**
```python
return {
    "tier": tier,
    "action": "resume",
    "changed": changed,           # Successfully resumed
    "skipped": skipped,           # Skipped due to circuit breaker
    "failed": failed              # Failed to unpause
}
```

### Example Scenario

```
Container: redis (in tier 5)
Time: 12:00:00

Cycle 1: Docker crash detected by healer-agent
  healer-agent: redis circuit → OPEN (stop trying to fix it)
  healer-agent: log incident

Cycle 2: Throttle-agent pauses tier 5 due to high RAM
  throttle: redis paused ✓

Cycle 3: RAM drops, throttle wants to resume redis
  throttle: check healer, is redis circuit OPEN?
  healer: YES, circuit OPEN (Docker crash not fixed)
  throttle: SKIP resume for redis
  throttle: redis stays paused

Cycles 4-10: Healer works on fixing Docker issue...

Cycle 20: Docker restored by healer-agent
  healer-agent: redis circuit → CLOSED (recovered!)

Cycle 21: Throttle wants to resume
  throttle: check healer, is redis circuit OPEN?
  healer: NO, circuit CLOSED (recovered!)
  throttle: Resume redis ✓
  redis: UNPAUSED
```

### Key Safety Properties

1. **Never Resume a Broken Service**
   - Circuit breaker prevents resuming if service down
   - Avoids cascading failures

2. **Graceful Degradation**
   - If healer unreachable: assume circuit is closed (safe default)
   - Service continues working even if healer down

3. **Clear Audit Trail**
   - `skipped` list shows which containers were held
   - Logged for incident investigation

---

## 📍 SECTION 5: PROTECT RULES INTERACTION

**Location**: Multiple locations (Lines 180-206, 568-633)  
**Complexity Level**: ⚠️ LOW  
**Why Complex**: Multiple protection layers can interact confusingly

### Protection Layers

**Layer 1: Protect Tiers** (Never pause these tiers)
```python
THROTTLE_PROTECT_TIERS = {1, 2, 3}  # Tiers 1, 2, 3 never paused
```

**Layer 2: Protect Containers** (Never pause these containers)
```python
THROTTLE_PROTECT_CONTAINERS = {
    "throttle-agent",      # Can't pause self
    "healer-agent",        # Can't pause healer
    "hypercode-core",      # Critical service
    "postgres",            # Database
    "redis",               # Cache
}
```

**Layer 3: Prevent Circular Dependency**
```python
# If container is in THROTTLE_PROTECT_CONTAINERS,
# it's automatically added to protection
```

### How They Interact

**Decision Flow During Pause**:
```
for each container in tier:
    ├─ Check: is container in THROTTLE_PROTECT_CONTAINERS?
    │  └─ YES: Skip this container, don't pause
    │  └─ NO: Continue
    ├─ Try to pause container
    └─ Record result (changed/failed)
```

**Example 1: Tier 2 (has protected container)**
```
Desired pause: [6, 5, 2]
Processing tier 2:
  ├─ crew-orchestrator: not protected → pause ✓
  └─ hypercode-dashboard: not protected → pause ✓
```

**Example 2: Tier 1 (always protected)**
```
Desired pause: [6, 5, 1]
Before processing:
  ├─ Check: is tier 1 in THROTTLE_PROTECT_TIERS?
  │  └─ YES: Skip entire tier 1
  └─ Never even check containers in tier 1
```

**Example 3: healer-agent in tier 5**
```
Desired pause: [6, 5]
Processing tier 5:
  ├─ prometheus: not protected → pause ✓
  ├─ tempo: not protected → pause ✓
  ├─ loki: not protected → pause ✓
  ├─ grafana: not protected → pause ✓
  └─ healer-agent: IN THROTTLE_PROTECT_CONTAINERS → skip
```

### Protection is Hardcoded

**Current Configuration** (in docker-compose.yml):
```yaml
environment:
  - THROTTLE_PROTECT_TIERS=1,2,3
  - THROTTLE_PROTECT_CONTAINERS=throttle-agent,healer-agent,hypercode-core,postgres,redis
```

**Why This List?**
- `throttle-agent`: Can't pause yourself (circular)
- `healer-agent`: Can't pause healer (who would fix problems?)
- `hypercode-core`: Business logic (critical)
- `postgres`: Database (data loss risk)
- `redis`: Cache (performance critical)

---

## 📍 SECTION 6: TIER CONFIGURATION

**Location**: Lines 148-176 in main.py  
**Complexity Level**: ⚠️ LOW  
**Why Complex**: Hardcoded, but system depends on it

### Current Tier Structure

```python
DEFAULT_TIERS: dict[int, list[str]] = {
    1: ["postgres", "redis", "hypercode-core", "hypercode-ollama"],
    2: ["crew-orchestrator", "hypercode-dashboard"],
    3: ["celery-worker"],
    4: ["test-agent"],
    5: ["prometheus", "tempo", "loki", "grafana"],
    6: ["minio", "cadvisor", "node-exporter", "security-scanner"],
}
```

### Tier Meanings

| Tier | Purpose | Pause? | Reason |
|------|---------|--------|--------|
| **1** | Core DB & Cache | Never | Data loss, database corruption |
| **2** | Business Logic | Never | Service unavailability |
| **3** | Background Workers | Never | Job queue fallback |
| **4** | Test/Demo | Optional | Development/staging |
| **5** | Observability | Optional | Monitoring can be sacrificed |
| **6** | Low Priority | First | Least critical |

### Pause Strategy

```
RAM Usage → Action
──────────────────
  <80%    → Nothing
  80%     → Pause tier 6
  90%     → Pause tiers 6, 5
  95%     → EMERGENCY: pause tiers 6, 5, 4
```

### Why This Order?

**Tier 6 First** (minio, cadvisor):
- Minio: object storage (can restart)
- cadvisor: metrics only
- node-exporter: metrics only
- security-scanner: optional scanning

**Tier 5 Second** (prometheus, loki):
- Monitoring stack
- Can stop temporarily
- But try to keep (THROTTLE_KEEP_OBSERVABILITY)

**Tier 4 Third** (test-agent):
- Test/demo container
- Not production critical

**Tiers 1-3 Protected**:
- Never pause
- If these run out of memory → system crashes

---

## 💡 KEY TAKEAWAYS

### For Developers

1. **Linear Regression** is used for predictive throttling
   - Fits line through recent RAM measurements
   - Projects forward to anticipate exhaustion

2. **CPU Calculation** follows Docker's official formula
   - Requires understanding tick-based measurements
   - Can exceed 100% on multi-core systems

3. **State Machine** manages pause/resume lifecycle
   - Prevents thrashing with 5-minute hold
   - Circuit breaker prevents resuming broken services

4. **Protection Rules** ensure critical services never pause
   - Tier-based (always protect tiers 1-3)
   - Container-based (specific services)

5. **Healer Integration** is crucial for safety
   - Respects circuit breaker state
   - Prevents cascading failures

### For Operators

1. **Thresholds Control Behavior**
   - Conservative (80/90/95): pause late, safer but more thrashing
   - Aggressive (70/80/90): pause early, proactive but false positives

2. **Hold Time Prevents Oscillation**
   - 5 minutes by default
   - Longer for unstable systems

3. **Observability Stack** can be sacrificed
   - THROTTLE_KEEP_OBSERVABILITY flag
   - Automatic monitoring degradation when needed

4. **Protection List** is critical
   - Add any new critical service here
   - Default list covers core infrastructure

---

*Detailed Explanation Complete*  
*Generated by Gordon — Docker AI Assistant*  
*March 19, 2026*
