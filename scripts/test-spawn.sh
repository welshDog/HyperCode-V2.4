#!/bin/bash
# Test spawn triggering via Redis pubsub

AGENT_NAME="${1:-coder-agent}"
REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"

echo "📢 Triggering spawn for: $AGENT_NAME"

# Publish to Redis channel
redis-cli -u "$REDIS_URL" PUBLISH "agent:spawn:$AGENT_NAME" '{"task":"test-spawn","priority":"high"}'

# Wait 5 seconds and check if spawned
sleep 5

# Check if container is running
docker ps --filter "name=$AGENT_NAME" --format "table {{.Names}}\t{{.Status}}"

if [ $? -eq 0 ]; then
    echo "✅ $AGENT_NAME spawned successfully"
else
    echo "❌ Failed to spawn $AGENT_NAME"
fi
