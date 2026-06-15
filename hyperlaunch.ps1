#!/usr/bin/env pwsh
# hyperlaunch.ps1 — canonical docker compose wrapper for HyperCode V2.4
#
# Always uses the correct 4-file set. Pass any docker compose args after the script name.
#
# Examples:
#   .\hyperlaunch.ps1 up -d                                  # always-on services
#   .\hyperlaunch.ps1 --profile agents up -d                 # + agents
#   .\hyperlaunch.ps1 --profile agents up -d hypercode-core  # single service
#   .\hyperlaunch.ps1 ps                                      # status
#   .\hyperlaunch.ps1 logs -f hypercode-mcp-server           # logs

Set-Location $PSScriptRoot

docker compose `
  -f docker-compose.yml `
  -f docker-compose.secrets.yml `
  -f docker-compose.registry.yml `
  -f docker-compose.hyperhealth.yml `
  @args
