$ErrorActionPreference = "Stop"

$envPath = Join-Path (Get-Location) ".env"
if (Test-Path $envPath) {
  $apiKeyLine = Get-Content $envPath | Where-Object { $_ -match "^\s*MCP_GATEWAY_API_KEY\s*=" } | Select-Object -First 1
  if ($apiKeyLine) {
    $apiKey = ($apiKeyLine -replace "^\s*MCP_GATEWAY_API_KEY\s*=\s*", "").Trim().Trim('"').Trim("'")
    if ($apiKey) {
      $env:MCP_GATEWAY_AUTH_TOKEN = $apiKey
    }
  }
}

docker mcp gateway run --transport sse --port 8820 `
  --servers github,github-official,filesystem,postgres

