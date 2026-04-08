# HyperCode CLI Manual

The **HyperCode CLI** is your command center for controlling the Agent Swarm. It allows you to translate code, check system health, and conduct research directly from your terminal.

## Installation

The CLI is included in the root of the project. Ensure you have Python installed.

1.  Navigate to the project root:
    ```powershell
    cd HyperCode-V2.0
    ```
2.  (Optional) Add the directory to your PATH or use the `hypercode.bat` wrapper.

## Authentication

The CLI automatically looks for a `token.txt` file in the same directory. This token is generated during the seed data process.

*   **Missing Token?** Run `python seed_data.py` (if available) or ensure you have logged in via the backend to generate one.

## Commands

### 1. Translate Code (`translate`)
Converts a raw code file into **HyperCode Spatial Logic**—a visual, emoji-enhanced explanation.

**Usage:**
```bash
hypercode translate <filename.py>
```

**Example:**
```bash
hypercode translate messy_code.py
```

**Output:**
*   A markdown file in `docs/outputs/translate_{task_id}.md`.

---

### 2. System Health Check (`pulse`)
Summons **The Medic (Pulse Agent)** to check the heartbeat of your Docker swarm via Prometheus.

**Usage:**
```bash
hypercode pulse
```

**Output:**
*   A plain-English health report in `docs/outputs/health_{task_id}.md`.
*   Console confirmation of queued task.

---

### 3. Technical Research (`research`)
Wakes **The Archivist (Research Agent)** to conduct deep-dive technical research on any topic.

**Usage:**
```bash
hypercode research "Your topic here"
```

**Example:**
```bash
hypercode research "How does DNA computing map to spatial logic?"
```

**Output:**
*   A structured research brief in `docs/outputs/research_{task_id}.md`.

## Interactive Dashboard

While the CLI is powerful, you can also visualize the agent swarm in real-time.

*   **URL**: `http://localhost:8088`
*   **Features**:
    *   **Mission Control**: Monitor live logs and system status.
    *   **HyperFlow Editor**: Visual drag-and-drop agent orchestration.
    *   **Neural Net**: Visualize agent memory connections.

## Troubleshooting

*   **"Backend offline?"**: Ensure your Docker containers are running (`docker ps`).
*   **"Missing auth token!"**: Check if `token.txt` exists in the root directory.
