#!/usr/bin/env python3
import sys

def main():
    compose_file = "docker-compose.agents-full.yml"

    with open(compose_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find the line where networks starts
    networks_line = None
    for i, line in enumerate(lines):
        if line.strip() == "networks:":
            networks_line = i
            break

    if networks_line is None:
        print("Could not find networks section")
        sys.exit(1)

    # Find the end of the mission-executor block (look for the line before networks that is not indented)
    # Actually, we want to insert before networks, so we take lines[:networks_line]
    # But we need to make sure we don't include any trailing blank lines? We'll keep as is.

    # Define the new service block
    new_service = [
        "# ═════════════════════════════════════════════════════════════════════════════════\n",
        "  # META-RESEARCH ARCHITECT — Self-evolving research agent that sits above HyperCode\n",
        "  # Combines academic research, GitHub intelligence, orchestration tuning, and\n",
        "  # neurodivergent tutoring to continuously improve the HyperCode ecosystem.\n",
        "  # Integrates with MCP-GitHub, observability stack, and research databases.\n",
        "  # Implements self-evolving planner with MOSS-style capabilities.\n",
        "  # ═════════════════════════════════════════════════════════════════════════════════\n",
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
        "\n"
    ]

    # Insert the new service before the networks section
    new_lines = lines[:networks_line] + new_service + lines[networks_line:]

    with open(compose_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"Updated {compose_file} with meta-research-architect service")

if __name__ == "__main__":
    main()