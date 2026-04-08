#!/bin/bash
# HyperCode V2.0 Launch Verification Script

echo "🚀 Initiating Launch Verification Sequence..."

# 1. Verify Core API
echo -n "Checking Core API... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ "$HTTP_CODE" == "200" ]; then
    echo "✅ ONLINE"
else
    echo "❌ FAILED (HTTP $HTTP_CODE)"
fi

# 2. Verify AI Module
echo -n "Checking AI Module... "
AI_STATUS=$(curl -s http://localhost:8000/orchestrator/llm/health | grep -o "healthy")
if [ "$AI_STATUS" == "healthy" ]; then
    echo "✅ ONLINE (Ollama Connected)"
else
    echo "❌ FAILED"
fi

# 3. Verify Agents
echo "Checking Agent Swarm..."
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(specialist|engineer|architect|strategist|orchestrator)"

# 4. Database Check
echo -n "Checking Database... "
docker exec hypercode-postgres pg_isready -U postgres > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ ONLINE"
else
    echo "❌ FAILED"
fi

echo "🏁 Verification Complete."
