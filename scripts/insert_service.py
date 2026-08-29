#!/usr/bin/env python3
import sys

def main():
    compose_file = "docker-compose.agents-full.yml"

    with open(compose_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # We know the mission-executor block ends at line 50 (0-indexed) which is the labels line.
    # We want to insert after that line.
    insert_idx = 51  # after the labels line

    # Define the service block to insert
    service_block = [
        "\n",  # blank line before service
        "# ════════════════════════════════════════════════════════════════════════════════\n",
        "  # META-RESEARCH ARCHITECT — Self-evolving research agent that sits above HyperCode\n",
        "  # Combines academic research, GitHub intelligence, orchestration tuning, and\n",
        "  # neurodivergent tutoring to continuously improve the HyperCode ecosystem.\n",
        "  # Integrates with MCP-GitHub, observability stack, and research databases.\n",
        "  # Implements self-evolving planner with MOSS-style capabilities.\n",
        "  # ════════════════════════════════════════════════════════════════════════════════\n",
        "  meta-research-architect:\n",
        "    image: hypercode-meta-research-architect:latest\n",
        "    build:\n",
        "      context: ./services/meta-research-architect\n",
        "      dockerfile: Dockerfile\n",
        "    container_name: meta-research-architect\n",
        "    ports:\n",
        "      - \"127.0.0.1:8095:8095\"\n",
        "    environment:\n",
        "      - AGENT_NAME=meta-research-architect\n",
        "      - LOG_LEVEL=INFO\n",
        "      - REDIS_URL=redis://${REDIS_HOST:-redis}:6379/0\n",
        "      - RESEARCH_UPDATE_INTERVAL=${RESEARCH_UPDATE_INTERVAL:-300}  # 5 minutes\n",
        "      - GITHUB_SCAN_INTERVAL=${GITHUB_SCAN_INTERVAL:-600}        # 10 minutes\n",
        "      - ORCHESTRATION_ANALYSIS_INTERVAL=${ORCHESTRATION_ANALYSIS_INTERVAL:-120}  # 2 minutes\n",
        "      - TUTORING_UPDATE_INTERVAL=${TUTORING_UPDATE_INTERVAL:-1800}  # 30 minutes\n",
        "    networks:\n",
        "      - agents-net\n",
        "      - data-net\n",
        "    depends_on:\n",
        "      redis:\n",
        "        condition: service_healthy\n",
        "      crew-orchestrator:\n",
        "        condition: service_healthy\n",
        "    deploy:\n",
        "      resources:\n",
        "        limits:\n",
        "          cpus: \"1.0\"\n",
        "          memory: 512MB\n",
        "        reservations:\n",
        "          cpus: \"0.5\"\n",
        "          memory: 256MB\n",
        "    healthcheck:\n",
        "      test: [\"CMD\", \"curl\", \"-f\", \"http://localhost:8095/health\"]\n",
        "      interval: 30s\n",
        "      timeout: 3s\n",
        "      retries: 3\n",
        "      start_period: 10s\n",
        "    restart: unless-stopped\n",
        "    labels:\n",
        "      - \"com.hypercode.tier=research\"\n",
        "      - \"com.hypercode.role=meta-architect\"\n",
        "\n"  # blank line after service
    ]

    # Insert the service block
    new_lines = lines[:insert_idx] + service_block + lines[insert_idx:]

    with open(compose_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"Inserted meta-research-architect service at line {insert_idx}")

if __name__ == "__main__":
    main()