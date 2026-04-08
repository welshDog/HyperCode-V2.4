#!/bin/bash
# ============================================================================
# MCP GATEWAY + MODEL RUNNER QUICK START
# ============================================================================
# Usage:
#   ./scripts/mcp-gateway-start.sh          # Start MCP profile
#   ./scripts/mcp-gateway-start.sh --check  # Health check
#   ./scripts/mcp-gateway-start.sh --logs   # Tail logs
#
# ============================================================================

set -e

MCP_PROFILE="docker-compose.mcp-gateway.yml"
ACTION="${1:-start}"

case "$ACTION" in
  start)
    echo "🚀 Starting MCP Gateway + Model Runner Profile..."
    docker compose -f docker-compose.yml -f "$MCP_PROFILE" up -d
    echo "✅ Profile started"
    echo ""
    echo "📋 Services starting (wait 30s for health checks):"
    echo "   • MCP Gateway:     http://localhost:8820"
    echo "   • Model Runner:    http://localhost:11434"
    echo "   • GitHub Tool:     http://localhost:3001"
    echo "   • Postgres Tool:   http://localhost:3002"
    echo "   • FileSystem Tool: http://localhost:3003"
    echo "   • VectorDB Tool:   http://localhost:3004"
    echo ""
    echo "Run: ./scripts/mcp-gateway-start.sh check"
    ;;
  
  stop)
    echo "🛑 Stopping MCP Gateway + Model Runner..."
    docker compose -f "$MCP_PROFILE" down
    echo "✅ Stopped"
    ;;
  
  check)
    echo "🔍 Health Check:"
    
    services=(
      "mcp-gateway:8820"
      "model-runner:11434"
      "mcp-github:3001"
      "mcp-postgres:3002"
      "mcp-filesystem:3003"
      "mcp-vectordb:3004"
    )
    
    for service in "${services[@]}"; do
      IFS=':' read -r name port <<< "$service"
      if curl -s "http://localhost:${port}/health" > /dev/null 2>&1; then
        echo "   ✅ $name"
      else
        echo "   ❌ $name (not responding)"
      fi
    done
    ;;
  
  logs)
    echo "📜 Tailing MCP Gateway logs..."
    docker compose -f "$MCP_PROFILE" logs -f mcp-gateway
    ;;
  
  test-gateway)
    echo "🧪 Testing MCP Gateway..."
    echo ""
    echo "Step 1: Discover tools"
    curl -s -H "Authorization: Bearer agent-key-001" \
      http://localhost:8820/tools/discover | jq '.'
    echo ""
    echo "Step 2: Test GitHub tool"
    curl -s -X POST \
      -H "Authorization: Bearer agent-key-001" \
      -H "Content-Type: application/json" \
      -d '{"tool": "github:list_repos", "params": {"owner": "welshDog"}}' \
      http://localhost:8820/tools/call | jq '.'
    ;;
  
  model-download)
    MODEL="${2:-mistral:7b-instruct}"
    echo "⬇️  Downloading model: $MODEL"
    docker exec model-runner ollama pull "$MODEL"
    ;;
  
  shell-mcp)
    echo "🐚 Opening MCP Gateway shell..."
    docker exec -it mcp-gateway /bin/sh
    ;;
  
  *)
    echo "Usage: $0 {start|stop|check|logs|test-gateway|model-download|shell-mcp}"
    echo ""
    echo "Examples:"
    echo "  $0 start                              # Start MCP profile"
    echo "  $0 check                              # Health check"
    echo "  $0 logs                               # Tail logs"
    echo "  $0 test-gateway                       # Test gateway endpoints"
    echo "  $0 model-download mistral:7b-instruct # Download model"
    ;;
esac
