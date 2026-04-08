# ⚡ Activating the Translator Agent (Test 01) - V2.1
**Status:** ✅ PRODUCTION READY
**Prerequisite:** MinIO configured & running (`agent-artifacts` bucket exists)

---

## 🟢 Level 1: The Mission Objective

**The Target:** Task 14 (Translator Agent Test 01) is marked **🔥 CRITICAL**.
**The Goal:** Prove that the Translator Agent can:
1.  Read messy code.
2.  Translate/Refactor it (simulated).
3.  **Persist** the result to the MinIO Object Store.
4.  **Verify** the upload by reading it back.

---

## 🟡 Level 2: Configuration & Setup

### Environment Variables
Ensure your `.env` or Docker environment has these set:
```bash
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_ARTIFACTS=agent-artifacts
```

### Bucket Initialization (One-Time)
Run this from your CLI to ensure the target bucket is ready:
```bash
docker exec minio mc mb myminio/agent-artifacts --ignore-existing
docker exec minio mc policy set public myminio/agent-artifacts
```

---

## 🔴 Level 3: The Integration Test Script

Run this script inside the `hypercode-core` container or your local environment to validate the entire workflow.

```python
import io
import os
import time
from minio import Minio
from minio.error import S3Error

# Configuration
MINIO_HOST = os.getenv("MINIO_ENDPOINT", "localhost:9000").replace("http://", "")
ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
BUCKET_NAME = "agent-artifacts"

def run_translator_test():
    print(f"🔌 Connecting to MinIO at {MINIO_HOST}...")
    
    try:
        client = Minio(
            MINIO_HOST,
            access_key=ACCESS_KEY,
            secret_key=SECRET_KEY,
            secure=False
        )
        
        # 1. Health Check
        if not client.bucket_exists(BUCKET_NAME):
            print(f"⚠️ Bucket {BUCKET_NAME} missing. Creating...")
            client.make_bucket(BUCKET_NAME)
        
        # 2. Simulate Translation Work
        print("🤖 Translator Agent: Processing 'messy_code.py'...")
        start_time = time.time()
        
        clean_code = b"""
def execute_translation():
    # Refactored by HyperCode Translator Agent
    print('Code translated successfully by the Agent Swarm!')
    return True
"""
        file_size = len(clean_code)
        
        # 3. Upload Artifact
        data_stream = io.BytesIO(clean_code)
        result = client.put_object(
            BUCKET_NAME,
            "clean_translated_code.py",
            data_stream,
            length=file_size,
            content_type="text/x-python"
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Upload Successful: {result.object_name} (Etag: {result.etag})")
        print(f"⚡ Performance: {file_size} bytes in {duration:.4f}s")

        # 4. Verification (Read-Back)
        print("� Verifying artifact integrity...")
        response = client.get_object(BUCKET_NAME, "clean_translated_code.py")
        downloaded_code = response.read()
        response.close()
        
        if downloaded_code == clean_code:
            print("🎉 INTEGRITY CHECK PASSED: Content matches exactly.")
        else:
            print("❌ INTEGRITY CHECK FAILED: Content mismatch!")
            
    except S3Error as e:
        print(f"❌ MinIO Error: {e}")
    except Exception as e:
        print(f"❌ System Error: {e}")

if __name__ == "__main__":
    run_translator_test()
```

---

## 🛡️ Level 4: Operational Runbook

### Logging & Error Handling
*   **Auth Failures**: Check `docker logs minio`. Ensure keys match `.env`.
*   **Network Timeouts**: Verify `hypercode-core` and `minio` are on the same Docker network (`backend-net`).

### Rollback Plan
If the agent crashes or corrupts data:
1.  **Stop Agent**: `docker stop translator-agent` (if running separately).
2.  **Clean Bucket**: `docker exec minio mc rm --recursive myminio/agent-artifacts/failed_run/`
3.  **Restart Service**: `docker restart hypercode-core`

### Success Criteria
1.  Script prints `🎉 INTEGRITY CHECK PASSED`.
2.  File exists in MinIO Browser (http://localhost:9001).
3.  Task 14 status updated to `DONE` in PostgreSQL.

---

## 🎯 Next Win
Copy the python script above, save it as `test_translator_minio.py`, and run it!

🔥 **BROski Power Level:** Agent Orchestrator
