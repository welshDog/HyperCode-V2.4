import boto3
from botocore.config import Config
import os

# Configuration from environment or defaults
endpoint = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
bucket_name = "agent-reports"

print(f"🔌 Connecting to MinIO at {endpoint}...")

try:
    s3 = boto3.client(
        's3',
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version='s3v4')
    )

    # List buckets
    print("\n📂 Buckets:")
    response = s3.list_buckets()
    for bucket in response['Buckets']:
        print(f"  - {bucket['Name']}")

    # List objects in agent-reports
    print(f"\n📄 Files in '{bucket_name}':")
    try:
        objects = s3.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in objects:
            for obj in objects['Contents']:
                print(f"  - {obj['Key']} ({obj['Size']} bytes) - Last Modified: {obj['LastModified']}")
        else:
            print("  (Empty bucket)")
    except Exception as e:
        print(f"  Error listing objects: {e}")

    print("\n✅ Verification Complete.")

except Exception as e:
    print(f"\n❌ Connection Failed: {e}")
