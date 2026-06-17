#!/usr/bin/env pwsh
# hyperlaunch.ps1 — canonical docker compose wrapper for HyperCode V2.4
#
# Always uses the correct 4-file set. Pass any docker compose args after the script name.
#
# The always-on BROski$ economy consumer (docker-compose.broski-economy.yml) is
# brought up/down ALONGSIDE the main stack on `up` / `down`. It runs as its OWN
# compose project (-p broski-economy) so it stays isolated — --remove-orphans on
# the main stack can never touch it, and vice versa.
#
# Examples:
#   .\hyperlaunch.ps1 up -d                                  # always-on services (+ economy consumer)
#   .\hyperlaunch.ps1 --profile agents up -d                 # + agents
#   .\hyperlaunch.ps1 --profile agents up -d hypercode-core  # single service
#   .\hyperlaunch.ps1 ps                                      # status
#   .\hyperlaunch.ps1 logs -f hypercode-mcp-server           # logs

Set-Location $PSScriptRoot

$mainFiles = @(
  '-f', 'docker-compose.yml',
  '-f', 'docker-compose.secrets.yml',
  '-f', 'docker-compose.registry.yml',
  '-f', 'docker-compose.hyperhealth.yml'
)
# own project + profile -> isolated, never an orphan of the main stack
$consumer = @(
  '-p', 'broski-economy',
  '-f', 'docker-compose.broski-economy.yml',
  '--profile', 'broski-economy'
)

if ($args -contains 'down') {
    # consumer first (release the shared data-net), then the main stack
    docker compose @consumer down
    docker compose @mainFiles @args
}
elseif ($args -contains 'up') {
    # main stack first (creates data-net), then the always-on economy consumer
    docker compose @mainFiles @args
    docker compose @consumer up -d
}
else {
    docker compose @mainFiles @args
}
