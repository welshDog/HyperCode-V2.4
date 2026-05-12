---
name: mint-pet-confirm
description: Deploys and manages the mint-pet-confirm Supabase Edge Function
  in HyperCode-V2.4. Use when deploying, updating, debugging, or verifying
  the pet minting confirmation flow on Base Sepolia.
---

# mint-pet-confirm Skill

## When to use
- Deploying or redeploying the mint-pet-confirm edge function.
- Debugging failed mint confirmations on Base Sepolia.
- Checking logs or health of the edge function after deploy.

## Deploy steps

1. Navigate to the HyperCode-V2.4 repo root.
2. Check the function exists:
   ```
   ls supabase/functions/mint-pet-confirm/
   ```
3. Deploy to Supabase:
   ```powershell
   npx supabase functions deploy mint-pet-confirm --project-ref <YOUR_PROJECT_REF>
   ```
4. Verify deployment in Supabase dashboard → Edge Functions.
5. Test with a curl or Postman call to the function URL.
6. Check logs:
   ```powershell
   npx supabase functions logs mint-pet-confirm --project-ref <YOUR_PROJECT_REF>
   ```

## Success criteria
- Function shows as "Active" in Supabase dashboard.
- Test mint confirmation returns expected response (pet ID confirmed, metadata updated).
- No errors in logs for a clean test call.

## Key env vars required
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `BASE_SEPOLIA_RPC_URL`
- `MINTER_PRIVATE_KEY`

## Common issues
- **Timeout**: Increase function timeout in Supabase dashboard if RPC calls are slow.
- **Auth error**: Double-check SERVICE_ROLE_KEY is set, not the anon key.
- **RPC failure**: Confirm Base Sepolia RPC endpoint is live before deploying.
