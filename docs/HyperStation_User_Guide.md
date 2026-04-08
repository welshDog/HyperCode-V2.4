# Hyper Station - Mission Control & Startup Guide

## Overview

**Hyper Station** provides a centralized, "one-button" interface to launch the entire HyperCode V2.0 ecosystem. It orchestrates the startup of core services (Orchestrator, Database, Redis), specialized agents (Healer, Frontend, Backend), and the Dashboard UI.

## Components

The system is controlled via scripts located in the `scripts/` directory:

1.  **`hyper-station-start.bat`**: The master launch sequence.
    *   Verifies Docker is running.
    *   Starts all containers via `docker compose`.
    *   Waits for health checks (Dashboard & Orchestrator).
    *   Launches the Dashboard in your default browser.
    *   Opens a multi-pane Windows Terminal (if installed) with logs for `healer-agent` and `crew-orchestrator`.
2.  **`hyper-station-stop.bat`**: The safe shutdown sequence.
    *   Stops all containers gracefully.
    *   Cleans up resources.
3.  **`install_shortcuts.ps1`**: Setup utility.
    *   Creates desktop shortcuts for Start/Stop scripts.

## Installation

1.  Open a PowerShell terminal in the project root:
    ```powershell
    cd "C:\Users\Lyndz\Downloads\HYPERCODE 2.O\HyperCode-V2.0"
    ```
2.  Run the installation script:
    ```powershell
    .\scripts\install_shortcuts.ps1
    ```
3.  Look for two new icons on your Desktop:
    *   🚀 **HYPER STATION START**
    *   🛑 **HYPER STATION STOP**

## Usage

### Starting the Mission

Double-click the **HYPER STATION START** icon.

**What happens next:**
1.  A terminal window opens showing the initialization progress.
2.  "Igniting Core Services..." -> Docker containers start.
3.  "Verifying System Vitals..." -> The script polls `http://localhost:8088` (Dashboard) and `http://localhost:8081` (Orchestrator).
4.  Once healthy:
    *   Your web browser opens to the **HyperCode Dashboard**.
    *   **Windows Terminal** launches with split panes:
        *   **Left**: Interactive shell in project root.
        *   **Top Right**: Live logs from `healer-agent` (watch for self-healing actions).
        *   **Bottom Right**: Live logs from `crew-orchestrator` (watch for task execution).

### Ending the Mission

Double-click the **HYPER STATION STOP** icon.

**What happens next:**
1.  All Docker containers are stopped.
2.  The terminal closes automatically upon completion.

## Troubleshooting

*   **"Docker is not running"**: Ensure Docker Desktop is started before running the script.
*   **Startup Timeout**: If the script says "Startup timed out", it means services took longer than 60 seconds to respond. The UI will still launch, but you may see errors until containers fully initialize.
*   **Windows Terminal not opening**: Install "Windows Terminal" from the Microsoft Store for the best experience. If not found, the script falls back to a standard command prompt.
