import io
import os
import time
from minio import Minio
from minio.error import S3Error

# Configuration
MINIO_HOST = os.getenv("MINIO_ENDPOINT", "minio:9000").replace("http://", "")
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
        print("🔍 Verifying artifact integrity...")
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
