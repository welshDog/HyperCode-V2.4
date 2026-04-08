# 📦 Storage Architecture: Where does the data go?

## 1. The Volume You Found
`hypercode-v20_minio_data`
*   **What it is:** The internal persistence layer for the **MinIO** service (your local S3).
*   **Current State:** 🟢 **Active but Empty**.
*   **Why?**: The MinIO container is running, but the `ResearchAgent` is currently configured to write files to the **Disk** (`docs/outputs`), not to **Object Storage**.

## 2. The Output Folder
`docs/outputs/` (Bind Mount)
*   **What it is:** A direct link between your Windows filesystem and the Docker container.
*   **Current State:** 🔥 **Active**.
*   **Evidence:** The `research_22.md` file appeared here because we mapped it in `docker-compose.yml`:
    ```yaml
    volumes:
      - ./docs/outputs:/app/outputs
    ```

## 3. The Database
`postgres-data` (Volume)
*   **What it is:** Stores the Task ID, Status, and Logs.
*   **Current State:** 🟢 **Active**.

## 🚀 Recommendation: Activate MinIO
To make the system "Cloud Native" (and truly autonomous), we should connect the **Research Agent** to **MinIO**.

**Proposed Change:**
1.  Agent finishes research.
2.  Agent saves markdown to `docs/outputs` (for you).
3.  **AND** Agent uploads artifacts to MinIO bucket `agent-memory`.
4.  **Benefit:** This allows other agents (running on different machines/pods) to download the research without needing access to your laptop's hard drive.

*Shall I wire up the Research Agent to MinIO now?*
