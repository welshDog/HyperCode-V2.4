# ════════════════════════════════════════════════════════════════════════════════
# docker-bake.hcl — BUILDX BAKE FOR 25 AGENTS + CORE
# Build all services in PARALLEL using Docker Build Cloud
# Usage: docker buildx bake agents --push
# Generated: May 21, 2026
# ════════════════════════════════════════════════════════════════════════════════

variable "REGISTRY" {
  default = "docker.io"
}

variable "IMAGE_PREFIX" {
  default = "w3lshdog"
}

variable "TAG" {
  default = "latest"
}

variable "PLATFORMS" {
  default = ["linux/amd64", "linux/arm64"]
}

# ══════════════════════════════════════════════════════════════════════════════
# GROUP: ALL AGENTS
# ══════════════════════════════════════════════════════════════════════════════

group "agents" {
  targets = [
    # TIER 1: CORE
    "crew-orchestrator",
    "agent-x",
    "brain-agent",
    "coder-agent",
    "tips-tricks-writer",
    # TIER 2: SPECIALISTS
    "frontend-specialist",
    "backend-specialist",
    "database-architect",
    "qa-engineer",
    "devops-engineer",
    "security-engineer",
    "system-architect",
    "project-strategist",
    # TIER 3: INFRASTRUCTURE
    "hyper-architect",
    "hyper-observer",
    "hyper-worker",
    "goal-keeper",
    "throttle-agent",
    "super-hyper-broski-agent",
    "test-agent",
    "hypercode-mcp-server",
    # TIER 4: UTILITY
    "session-snapshot",
    "hyper-split-agent",
    "coderabbit-webhook",
    "business-agent",
    # CORE SERVICE
    "hypercode-core",
  ]
}

group "agents-dev" {
  targets = ["crew-orchestrator", "agent-x", "brain-agent", "coder-agent"]
}

group "agents-push" {
  targets = ["agents"]
}

# ══════════════════════════════════════════════════════════════════════════════
# TIER 1: CORE CREW
# ══════════════════════════════════════════════════════════════════════════════

target "crew-orchestrator" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/crew-orchestrator"
  args = {
    BUILDKIT_INLINE_CACHE = "1"
  }
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-crew-orchestrator:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-crew-orchestrator:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

target "agent-x" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/agent-x"
  args = {
    BUILDKIT_INLINE_CACHE = "1"
  }
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-agent-x:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-agent-x:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

target "brain-agent" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/brain"
  args = {
    BUILDKIT_INLINE_CACHE = "1"
  }
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-brain-agent:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-brain-agent:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

target "coder-agent" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/coder"
  args = {
    BUILDKIT_INLINE_CACHE = "1"
  }
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-coder-agent:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-coder-agent:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

target "tips-tricks-writer" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/09-tips-tricks-writer"
  args = {
    BUILDKIT_INLINE_CACHE = "1"
  }
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-tips-tricks-agent:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-tips-tricks-agent:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

# ══════════════════════════════════════════════════════════════════════════════
# TIER 2: SPECIALISTS (8 agents)
# ══════════════════════════════════════════════════════════════════════════════

target "frontend-specialist" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/01-frontend-specialist"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-frontend-specialist:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-frontend-specialist:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

target "backend-specialist" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/02-backend-specialist"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-backend-specialist:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-backend-specialist:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

target "database-architect" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/03-database-architect"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-database-architect:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-database-architect:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

target "qa-engineer" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/04-qa-engineer"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-qa-engineer:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-qa-engineer:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

target "devops-engineer" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/05-devops-engineer"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-devops-engineer:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-devops-engineer:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

target "security-engineer" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/06-security-engineer"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-security-engineer:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-security-engineer:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

target "system-architect" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/07-system-architect"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-system-architect:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-system-architect:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

target "project-strategist" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/08-project-strategist"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-project-strategist:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-project-strategist:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

# ══════════════════════════════════════════════════════════════════════════════
# TIER 3: INFRASTRUCTURE (8 agents)
# ══════════════════════════════════════════════════════════════════════════════

target "hyper-architect" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/architect"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-hyper-architect:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-hyper-architect:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

target "hyper-observer" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/hyper-agents"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-hyper-observer:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-hyper-observer:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

target "hyper-worker" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/hyper-agents"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-hyper-worker:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-hyper-worker:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

target "goal-keeper" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/goal_keeper"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-goal-keeper:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-goal-keeper:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

target "throttle-agent" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/throttle-agent"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-throttle-agent:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-throttle-agent:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

target "super-hyper-broski-agent" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/super-hyper-broski-agent"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-super-hyper-broski-agent:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-super-hyper-broski-agent:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

target "test-agent" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/test-agent"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-test-agent:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-test-agent:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

target "hypercode-mcp-server" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/hypercode-mcp-server"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-mcp-server:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-mcp-server:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

# ══════════════════════════════════════════════════════════════════════════════
# TIER 4: UTILITY (4 agents)
# ══════════════════════════════════════════════════════════════════════════════

target "session-snapshot" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/session-snapshot"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-session-snapshot:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-session-snapshot:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

target "hyper-split-agent" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/hyper-split-agent"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-hyper-split-agent:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-hyper-split-agent:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

target "coderabbit-webhook" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/coderabbit-webhook"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-coderabbit-webhook:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-coderabbit-webhook:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

target "business-agent" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "agents/business"
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-business-agent:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-business-agent:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}

# ══════════════════════════════════════════════════════════════════════════════
# CORE SERVICE
# ══════════════════════════════════════════════════════════════════════════════

target "hypercode-core" {
  dockerfile = "Dockerfile.template-hardened"
  context    = "."
  tags = [
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-core:${TAG}",
    "${REGISTRY}/${IMAGE_PREFIX}/hypercode-core:v2.4.2",
  ]
  platforms = PLATFORMS
  cache-to  = ["type=gha,mode=max"]
  cache-from = ["type=gha"]
}
