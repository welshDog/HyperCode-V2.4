
# 🚀 HYPERFOCUS ZONE: COMPREHENSIVE E2E TEST PLAN

**Date:** 2026-05-12  
**Status:** Ready for Execution  
**Tested By:** BROski Orchestration Agent 🤖

---

## 📋 PRE-REQUISITES

### 1. Services Running
- [ ] HyperCode-V2.4 backend (`docker-compose -f docker-compose.core.yml up -d`)
- [ ] Redis container
- [ ] Postgres container
- [ ] HyperAgent-SDK CLI installed
- [ ] Supabase edge functions deployed
- [ ] Stripe test mode configured (if needed)

### 2. Environment Variables
- [ ] `HYPERCODE_API_URL` = `http://localhost:8000`
- [ ] `COURSE_SYNC_SECRET` = (shared secret between Course &amp; V2.4)
- [ ] `SHOP_SYNC_SECRET` = (shared secret for graduation &amp; pet minting)
- [ ] `DISCORD_BOT_TOKEN` = (for DM testing)

### 3. Test Data
- [ ] Test Discord ID: `123456789012345678` (mock or real)
- [ ] Test user created in V2.4 with `discord_id` linked
- [ ] Test tokens available in Course system

---

## 🎯 WORKFLOW 1: HYPER-AGENT GRADUATE FUNCTIONALITY

### Test Case 1.1: Successful Graduation
**Objective:** Verify that a user can graduate successfully with all downstream events triggered.

**Steps:**
1. Prepare test environment
2. Run graduation command:
   ```powershell
   cd HyperAgent-SDK
   $env:HYPERCODE_API_URL = "http://localhost:8000"
   $env:SHOP_SYNC_SECRET = "&lt;your-secret&gt;"
   node cli/index.js graduate 123456789012345678 --tokens 500
   ```
3. Verify API response
4. Check database for graduation event
5. Verify user token balance increased by 500
6. Check if Discord DM was sent (if applicable)

**Expected Results:**
- [ ] Command returns: `✅ GRADUATED! 123456789012345678`
- [ ] Badge: `hyper-graduate`
- [ ] Tokens: `+500 BROski$`
- [ ] `graduation_events` table has new record
- [ ] `users.broski_tokens` increased by 500
- [ ] Discord DM sent (if bot token configured)

**Response Time Target:** &lt; 2 seconds

---

### Test Case 1.2: Idempotency Check (No Double Graduation)
**Objective:** Verify that the same user can't graduate twice with the same source_id.

**Steps:**
1. Run graduation command first time (success expected)
2. Run the EXACT same command again immediately
3. Verify 409 response

**Expected Results:**
- [ ] First command succeeds
- [ ] Second command returns: `🎓 123456789012345678 already graduated — nothing to do!`
- [ ] No duplicate records in `graduation_events`
- [ ] Token balance only increased ONCE

---

### Test Case 1.3: Custom Token Amount
**Objective:** Verify that custom token amounts work correctly.

**Steps:**
1. Run graduation with custom tokens:
   ```powershell
   node cli/index.js graduate 123456789012345679 --tokens 1000
   ```
2. Verify token amount in response and database

**Expected Results:**
- [ ] Response shows: `Tokens: +1000 BROski$`
- [ ] Database records show `tokens_awarded = 1000`

---

### Test Case 1.4: Invalid Secret (403 Forbidden)
**Objective:** Verify that invalid secrets are rejected.

**Steps:**
1. Set wrong secret:
   ```powershell
   $env:SHOP_SYNC_SECRET = "wrong-secret-123"
   ```
2. Run graduation command
3. Verify 403 error

**Expected Results:**
- [ ] Command fails with: `✗ Graduation failed: HTTP 403`
- [ ] No graduation event created
- [ ] Token balance unchanged

---

## 💰 WORKFLOW 2: TOKEN SYNCHRONIZATION PIPELINE

### Test Case 2.1: Successful Token Sync
**Objective:** Verify tokens transfer accurately from Course to V2.4.

**Steps:**
1. Create a test token transaction in Course
2. Trigger sync-tokens-to-v24 edge function
3. Verify V2.4 `/api/v1/economy/award-from-course` endpoint
4. Check balances on both systems
5. Verify no data loss

**API Request (Direct Test):**
```powershell
$body = @{
    source_id = "test_sync_$(Get-Date -Format 'yyyyMMddHHmmss')"
    discord_id = "123456789012345678"
    tokens = 100
    reason = "E2E Test: Lesson Complete"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/economy/award-from-course" `
    -Method POST `
    -ContentType "application/json" `
    -Headers @{"X-Sync-Secret" = "&lt;COURSE_SYNC_SECRET&gt;"} `
    -Body $body
```

**Expected Results:**
- [ ] Response: `200 OK` with `awarded: true`
- [ ] `coins_balance` increased by 100
- [ ] `course_sync_events` table has new record
- [ ] `source_id` unique constraint enforced
- [ ] Both systems show same balance
- [ ] No data loss

**Response Time Target:** &lt; 500ms

---

### Test Case 2.2: Idempotent Sync (No Double Award)
**Objective:** Verify same source_id doesn't cause double token award.

**Steps:**
1. Send first sync request (success)
2. Send EXACT same request again immediately
3. Verify 409 response
4. Check balance only increased once

**Expected Results:**
- [ ] First request: 200 OK
- [ ] Second request: 409 Conflict with message
- [ ] Token balance only increased ONCE
- [ ] No duplicate `course_sync_events` records

---

### Test Case 2.3: User Not Found (404)
**Objective:** Verify proper error handling when user doesn't exist.

**Steps:**
1. Send sync request with non-existent discord_id
2. Verify 404 response

**Expected Results:**
- [ ] Response: 404 Not Found
- [ ] Error message suggests linking via /link-discord
- [ ] No tokens awarded
- [ ] No sync event created

---

### Test Case 2.4: Invalid Token Amount
**Objective:** Verify validation on token amount (1-10000).

**Steps:**
1. Test with tokens=0
2. Test with tokens=-50
3. Test with tokens=10001
4. Verify all fail with validation errors

**Expected Results:**
- [ ] All invalid amounts return 422 Validation Error
- [ ] No tokens awarded
- [ ] No sync events created

---

## 🐶 WORKFLOW 3: PET MINTING WORKFLOW

### Test Case 3.1: Complete Mint Flow (Auth + Confirm)
**Objective:** Verify full pet minting process including both stages.

**Prerequisites:**
- [ ] `mint-pet-auth` edge function deployed
- [ ] `mint-pet-confirm` edge function deployed
- [ ] `BROSKIPET_CONTRACT_ADDRESS` set in Supabase secrets
- [ ] Base Sepolia RPC accessible
- [ ] Relay wallet has ETH for gas

**Steps (Stage 1 - Auth):**
1. User requests pet mint from frontend
2. Call `mint-pet-auth` edge function
3. Verify EIP-712 signing works
4. Relay mint transaction to Base Sepolia
5. Get tx hash from response

**Steps (Stage 2 - Confirm):**
6. Wait for tx confirmation on Base Sepolia
7. Call `mint-pet-confirm` edge function with tx hash
8. Verify tx hash is valid and confirmed
9. Check `pets` table updated
10. Check `mint_nonces` table updated
11. Verify BROski$ awarded
12. Verify XP awarded

**Expected Results:**
- [ ] Stage 1: Returns signed tx + relay initiated
- [ ] Tx mined on Base Sepolia (check via block explorer)
- [ ] Stage 2: Returns success confirmation
- [ ] `pets` table has new record with correct metadata
- [ ] `mint_nonces` table updated (prevents replay attacks)
- [ ] User's BROski$ balance increased (if applicable)
- [ ] User's XP increased (if applicable)
- [ ] Pet visible in user's collection

**Response Time Target:**
- Stage 1 (auth): &lt; 3 seconds
- Stage 2 (confirm): &lt; 2 seconds (after tx confirmation)

---

### Test Case 3.2: Mint with Various Species/Rarities
**Objective:** Verify consistent behavior across all pet types and rarities.

**Test Matrix:**
| Species | Rarity | Expected Result |
|---------|--------|-----------------|
| Apex Dragon | Legendary | [ ] |
| Blizzard Lizard | Rare | [ ] |
| Chaos Cat | Uncommon | [ ] |
| Cyber Fox | Common | [ ] |
| Hyper Hamster | Common | [ ] |
| (Add all 10+ species) | | |

**Steps:**
1. For each species/rarity combination:
   - Request mint for that specific pet
   - Complete full auth+confirm flow
   - Verify metadata correct
   - Verify rarity properly assigned
   - Verify all visual layers correct

**Expected Results:**
- [ ] All species mint successfully
- [ ] Rarity properly reflected in metadata
- [ ] IPFS hashes correct for each pet
- [ ] On-chain tokenURI updated correctly
- [ ] No metadata corruption

---

### Test Case 3.3: Invalid Tx Hash (400 Bad Request)
**Objective:** Verify mint-pet-confirm rejects invalid tx hashes.

**Steps:**
1. Call `mint-pet-confirm` with fake tx hash: `0xdeadbeef...`
2. Verify error response

**Expected Results:**
- [ ] Response: 400 Bad Request
- [ ] Error: Invalid transaction hash
- [ ] No pet created
- [ ] No tokens awarded

---

### Test Case 3.4: Unconfirmed Tx (425 Too Early)
**Objective:** Verify mint-pet-confirm waits for tx confirmation.

**Steps:**
1. Send mint-pet-auth and get tx hash
2. Immediately call mint-pet-confirm (before tx mined)
3. Verify "not confirmed yet" error

**Expected Results:**
- [ ] Response: 425 Too Early or equivalent
- [ ] Error message indicates tx not confirmed
- [ ] No pet created yet
- [ ] Can retry later once tx is mined

---

## 📊 OBSERVABILITY &amp; MONITORING CHECKS

### Test Case 4.1: Prometheus Metrics
**Objective:** Verify all metrics are being scraped correctly.

**Checklist:**
- [ ] `http_requests_total` incrementing for each endpoint
- [ ] `http_request_duration_seconds` recording response times
- [ ] `up` metric = 1 for all services
- [ ] Custom BROski$ metrics visible
- [ ] Agent health metrics visible

**URL:** `http://localhost:9090/graph`

---

### Test Case 4.2: Grafana Dashboards
**Objective:** Verify dashboards show real-time data.

**Checklist:**
- [ ] Course Integration Dashboard updating
- [ ] Agent Health Dashboard showing all agents
- [ ] Token Economy Dashboard showing flow
- [ ] Logs visible in Loki
- [ ] Traces visible in Tempo

**URL:** `http://localhost:3001`

---

### Test Case 4.3: Log Aggregation (Loki)
**Objective:** Verify all logs are aggregated and searchable.

**Checklist:**
- [ ] Graduation events logged
- [ ] Token sync events logged
- [ ] Pet minting events logged
- [ ] Errors visible with stack traces
- [ ] Logs searchable by service, level, timestamp

**URL:** `http://localhost:3100`

---

## 🔒 SECURITY VALIDATION

### Test Case 5.1: Secret Exposure Check
**Objective:** Verify no secrets are exposed in logs or responses.

**Checklist:**
- [ ] `COURSE_SYNC_SECRET` not in any logs
- [ ] `SHOP_SYNC_SECRET` not in any logs
- [ ] `DISCORD_BOT_TOKEN` not in any logs
- [ ] API keys not exposed in error messages
- [ ] Secrets only passed via headers, never query params

---

### Test Case 5.2: Rate Limiting
**Objective:** Verify rate limiting works to prevent abuse.

**Steps:**
1. Send 100+ requests to `/api/v1/economy/award-from-course` rapidly
2. Verify 429 Too Many Requests responses
3. Verify legitimate requests still work after cool-down

**Expected Results:**
- [ ] Rate limiting kicks in after configured threshold
- [ ] 429 responses with Retry-After header
- [ ] No tokens awarded for rate-limited requests
- [ ] System remains stable under load

---

## 📝 TEST EXECUTION SUMMARY

### After All Tests Complete

**Overall Pass Rate:** ____ / ____

### Critical Issues Found:
- [ ]

### Warnings/Recommendations:
- [ ]

### Action Items:
- [ ]

---

## 🎉 SUCCESS CRITERIA

All workflows must pass:
- [ ] 100% of Graduation tests pass
- [ ] 100% of Token Sync tests pass
- [ ] 100% of Pet Minting tests pass
- [ ] No critical security issues
- [ ] All metrics and dashboards operational
- [ ] Response times within targets

---

**Ready to Execute?** Start the Docker services and run through the checklist! 🚀

