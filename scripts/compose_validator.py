import sys
import yaml
import subprocess
import re
from collections import defaultdict

file = sys.argv[1] if len(sys.argv) > 1 else None

if not file:
    print("⚠️  No file passed to compose_validator.py")
    sys.exit(0)

print(f"\n🐳 Validating: {file}")

# --- Step 1: YAML syntax check ---
try:
    with open(file, "r") as f:
        data = yaml.safe_load(f)
    print("✅ YAML syntax — valid")
except yaml.YAMLError as e:
    print(f"❌ YAML SYNTAX ERROR in {file}:")
    print(f"   {e}")
    sys.exit(1)

if not data:
    print("⚠️  Empty compose file — nothing to validate")
    sys.exit(0)

# --- Step 2: Port conflict check ---
services = data.get("services", {})
port_map = defaultdict(list)
warnings = []

for service_name, service_cfg in services.items():
    if not service_cfg:
        continue
    ports = service_cfg.get("ports", [])
    for port_entry in ports:
        # Handle both "8080:80" and {target: 80, published: 8080}
        if isinstance(port_entry, str):
            match = re.match(r"(?:.*:)?(\d+):", port_entry)
            if match:
                host_port = int(match.group(1))
                port_map[host_port].append(service_name)
        elif isinstance(port_entry, dict):
            published = port_entry.get("published")
            if published:
                port_map[int(published)].append(service_name)

conflicts = {port: svcs for port, svcs in port_map.items() if len(svcs) > 1}

if conflicts:
    print(f"\n⚠️  PORT CONFLICTS DETECTED in {file}:")
    for port, svcs in conflicts.items():
        print(f"   Port {port} → claimed by: {', '.join(svcs)}")
    warnings.append("port_conflicts")
else:
    print("✅ Port map — no conflicts")

# --- Step 3: Redis DB isolation check ---
for service_name, service_cfg in services.items():
    if not service_cfg:
        continue
    env = service_cfg.get("environment", {})
    if isinstance(env, dict):
        redis_db = env.get("REDIS_DB") or env.get("CACHE_DB")
        if redis_db is not None:
            db_num = int(str(redis_db))
            # Sacred Rule: DB1=cache, DB2=rate_limits
            if db_num not in [0, 1, 2]:
                print(f"⚠️  {service_name} uses Redis DB{db_num} — check Sacred Rules (DB1=cache, DB2=rate limits)")

# --- Step 4: docker.io socket check ---
compose_text = open(file).read()
if "docker.io" in compose_text:
    print(f"\n🚨 SACRED RULE VIOLATION in {file}:")
    print(f"   ❌ 'docker.io' found — use docker-ce-cli ONLY!")
    sys.exit(1)

if warnings:
    print(f"\n⚠️  {file} has warnings — review before deploying!")
else:
    print(f"✅ {file} — all checks passed! Safe to deploy 🚀")
