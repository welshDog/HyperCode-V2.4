#!/usr/bin/env powershell
# E2E Stripe Test

$API = "http://localhost:8000"
$PLAN = "starter"

Write-Host "=== STRIPE E2E TEST ===" -ForegroundColor Cyan

# Step 1: Plans
Write-Host "Fetching plans..." -ForegroundColor Yellow
$plansJson = curl.exe -s "$API/api/stripe/plans"
$plans = $plansJson | ConvertFrom-Json
Write-Host "OK: $($plans.plans.Count) plans available" -ForegroundColor Green

# Step 2: Checkout
Write-Host "Creating checkout for: $PLAN" -ForegroundColor Yellow
$body = @{ price_id = $PLAN } | ConvertTo-Json
$resp = curl.exe -s -X POST "$API/api/stripe/checkout" -H "Content-Type: application/json" -d $body
Write-Host "Response: $resp" -ForegroundColor Gray

try {
    $checkout = $resp | ConvertFrom-Json
    Write-Host "OK: Session = $($checkout.session_id)" -ForegroundColor Green
    Write-Host "    URL = $($checkout.checkout_url)" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Could not parse response" -ForegroundColor Red
    Write-Host "Raw: $resp" -ForegroundColor Red
}

# Step 3: Health
Write-Host "Checking health..." -ForegroundColor Yellow
$healthResp = curl.exe -s "$API/api/v1/health"
$health = $healthResp | ConvertFrom-Json
Write-Host "Status: $($health.status)" -ForegroundColor Green
