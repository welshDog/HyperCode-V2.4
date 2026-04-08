# Docker Bake file for building all HyperCode images efficiently
# Usage: docker buildx bake -f docker/docker-bake.hcl

variable "REGISTRY" {
  default = "hypercode"
}

variable "VERSION" {
  default = "latest"
}

variable "BUILD_DATE" {
  default = ""
}

variable "VCS_REF" {
  default = ""
}

group "default" {
  targets = ["core", "orchestrator", "agents"]
}

group "agents" {
  targets = [
    "frontend-specialist",
    "backend-specialist",
    "database-architect",
    "qa-engineer",
    "devops-engineer",
    "security-engineer",
    "system-architect",
    "project-strategist"
  ]
}

group "infrastructure" {
  targets = ["redis", "postgres"]
}

group "monitoring" {
  targets = ["prometheus", "grafana"]
}

# ==================== Core Services ====================

target "core" {
  context = "./HyperCode-V2.0/THE HYPERCODE/hypercode-core"
  dockerfile = "Dockerfile"
  tags = [
    "${REGISTRY}/hypercode-core:${VERSION}",
    "${REGISTRY}/hypercode-core:latest"
  ]
  labels = {
    "org.opencontainers.image.title" = "HyperCode Core"
    "org.opencontainers.image.description" = "Core service for HyperCode platform"
    "org.opencontainers.image.version" = "${VERSION}"
    "org.opencontainers.image.created" = "${BUILD_DATE}"
    "org.opencontainers.image.revision" = "${VCS_REF}"
  }
  platforms = ["linux/amd64", "linux/arm64"]
}

target "orchestrator" {
  context = "./agents/crew-orchestrator"
  dockerfile = "Dockerfile"
  tags = [
    "${REGISTRY}/crew-orchestrator:${VERSION}",
    "${REGISTRY}/crew-orchestrator:latest"
  ]
  labels = {
    "org.opencontainers.image.title" = "Crew Orchestrator"
    "org.opencontainers.image.version" = "${VERSION}"
  }
  platforms = ["linux/amd64", "linux/arm64"]
}

# ==================== Specialist Agents ====================

target "frontend-specialist" {
  context = "./agents/01-frontend-specialist"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/frontend-specialist:${VERSION}"]
  platforms = ["linux/amd64", "linux/arm64"]
}

target "backend-specialist" {
  context = "./agents/02-backend-specialist"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/backend-specialist:${VERSION}"]
  platforms = ["linux/amd64", "linux/arm64"]
}

target "database-architect" {
  context = "./agents/03-database-architect"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/database-architect:${VERSION}"]
  platforms = ["linux/amd64", "linux/arm64"]
}

target "qa-engineer" {
  context = "./agents/04-qa-engineer"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/qa-engineer:${VERSION}"]
  platforms = ["linux/amd64", "linux/arm64"]
}

target "devops-engineer" {
  context = "./agents/05-devops-engineer"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/devops-engineer:${VERSION}"]
  platforms = ["linux/amd64", "linux/arm64"]
}

target "security-engineer" {
  context = "./agents/06-security-engineer"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/security-engineer:${VERSION}"]
  platforms = ["linux/amd64", "linux/arm64"]
}

target "system-architect" {
  context = "./agents/07-system-architect"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/system-architect:${VERSION}"]
  platforms = ["linux/amd64", "linux/arm64"]
}

target "project-strategist" {
  context = "./agents/08-project-strategist"
  dockerfile = "Dockerfile"
  tags = ["${REGISTRY}/project-strategist:${VERSION}"]
  platforms = ["linux/amd64", "linux/arm64"]
}

# ==================== Development Images ====================

target "core-dev" {
  inherits = ["core"]
  dockerfile = "Dockerfile.dev"
  tags = ["${REGISTRY}/hypercode-core:dev"]
  platforms = ["linux/amd64"]
}

# ==================== Test Images ====================

target "test-runner" {
  context = "."
  dockerfile = "Dockerfile.builder"
  target = "testing"
  tags = ["${REGISTRY}/test-runner:${VERSION}"]
}
