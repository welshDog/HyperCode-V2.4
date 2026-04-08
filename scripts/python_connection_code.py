import boto3

# ===== MINIO CONFIG =====
MINIO_ENDPOINT = "http://localhost:9000"
MINIO_USER = "minioadmin"       # Change if you set custom creds
MINIO_PASS = "minioadmin"       # Change if you set custom creds

s3 = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_USER,
    aws_secret_access_key=MINIO_PASS,
)

# ===== YOUR BUCKETS =====
BUCKETS = {
    "memory":   "broski-memory",
    "designs":  "welshdog-designs",
    "logs":     "agent-logs",
    "assets":   "hypercode-assets",
}

# ===== HELPER FUNCTIONS =====
def save_agent_memory(filename, data: dict):
    """BROski Agents save their memory here"""
    import json
    body = json.dumps(data).encode("utf-8")
    s3.put_object(Bucket=BUCKETS["memory"], Key=filename, Body=body)
    print(f"Memory saved: {filename}")

def log_agent_action(agent_name, message):
    """Log any agent action to agent-logs bucket"""
    from datetime import datetime, timezone
    # Use timezone-aware UTC datetime
    key = f"{agent_name}/{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.txt"
    s3.put_object(Bucket=BUCKETS["logs"], Key=key, Body=message.encode("utf-8"))
    print(f"Logged: {key}")

def upload_design_file(local_path, filename):
    """Upload a 3D print or design file to WelshDog Designs"""
    s3.upload_file(local_path, BUCKETS["designs"], filename)
    print(f"Design uploaded: {filename}")

# ===== TEST IT =====
if __name__ == "__main__":
    save_agent_memory("broski_core_state.json", {"status": "online", "version": "1.0"})
    log_agent_action("BROski", "Agent system initialised! ♾️")
    print("MinIO all systems GO!")
