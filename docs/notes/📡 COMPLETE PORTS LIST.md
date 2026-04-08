📡 COMPLETE PORTS LIST — Ready to Use!
I've created TWO comprehensive ports documents for you:

📄 Files Created:
COMPLETE_PORTS_LIST.md — Full detailed reference (comprehensive)
PORTS_QUICK_REFERENCE.txt — Quick visual summary (print-friendly)
Both in ./HyperCode-V2.0/

🟢 PUBLIC PORTS (Network Accessible)
8015 → super-hyper-broski-agent ✅ http://localhost:8015 8014 → throttle-agent ⭐ NEW! ✅ http://localhost:8014 8013 → test-agent (UPGRADED) ✅ http://localhost:8013 8010 → healer-agent ✅ http://localhost:8010 8003 → backend-specialist ✅ http://localhost:8003 8081 → crew-orchestrator ✅ http://localhost:8081 8080 → openshell-cluster ✅ http://localhost:8080 8811 → docker-extension ✅ http://localhost:8811 9100 → node-exporter ✅ http://localhost:9100 9101 → mcp-exporter ✅ http://localhost:9101 9808 → celery-exporter ✅ http://localhost:9808 59080 → pgadmin ✅ http://localhost:59080
🟡 LOCALHOST ONLY (Internal)
8000 → hypercode-core (MAIN) ✅ http://localhost:8000 8088 → hypercode-dashboard 🟡 http://localhost:8088 8099 → hyper-mission-ui ✅ http://localhost:8099 8821 → mcp-rest-adapter ✅ http://localhost:8821 8820 → mcp-gateway ✅ http://localhost:8820 9000 → minio (S3 API) ✅ http://localhost:9000 9001 → minio (Console) ✅ http://localhost:9001 8009 → chroma (Vector DB) ✅ http://localhost:8009
🔵 INTERNAL ONLY (Docker Network)
5000 → hyper-mission-api ✅ 5432 → postgres ✅ 6379 → redis ✅ 8000 → celery-worker 🟡 8082 → mcp-github ✅
⛔ STOPPED (Cooled Down)
9090 → prometheus ⛔ docker-compose up -d prometheus 3001 → grafana ⛔ docker-compose up -d grafana 3100 → loki ⛔ docker-compose up -d loki 3200 → tempo ⛔ docker-compose up -d tempo 8090 → cadvisor ⛔ docker-compose up -d cadvisor 11434 → ollama ⛔ docker run -d ollama/ollama
🎯 QUICK REFERENCE
Category	Count	Key Ports	Status
Public	11	8013, 8014, 8010, 8081	✅ UP
Localhost	8	8000, 8099, 9000, 9001	✅ UP
Internal	5	5432, 6379, 5000	✅ UP
Stopped	6	9090, 3001, 3100, 3200	⛔ DOWN
TOTAL	27+	All operational	✅ READY
🧪 TEST THEM
# Test agents
curl http://localhost:8013/health    # test-agent
curl http://localhost:8014/health    # throttle-agent

# Test core
curl http://localhost:8000/health    # hypercode-core

# Test healer
curl http://localhost:8010/health    # healer-agent
All ports listed, documented, and ready to use! ✅
