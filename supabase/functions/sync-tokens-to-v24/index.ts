/**
 * sync-tokens-to-v24 — Supabase Edge Function
 * Phase 2: Token Sync
 *
 * Triggered by a Supabase Database Webhook on:
 *   Table: token_transactions
 *   Event: INSERT
 *
 * Forwards the new transaction to HyperCode V2.4's
 *   POST /api/v1/economy/award-from-course
 * so BROski$ earned in the Course immediately appear in the V2.4 wallet.
 *
 * Idempotency: source_id = token_transactions.id
 *   V2.4 returns 409 if already processed — edge fn treats 409 as success.
 *
 * Deploy to: Hyper-Vibe-Coding-Course Supabase project
 *
 * Env vars required (set via: supabase secrets set KEY=value):
 *   HYPERCODE_V24_URL    — https://api.hypercode.dev  (no trailing slash)
 *   COURSE_SYNC_SECRET   — shared secret matching COURSE_SYNC_SECRET in V2.4 .env
 */

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const V24_URL = Deno.env.get("HYPERCODE_V24_URL") ?? "";
const SYNC_SECRET = Deno.env.get("COURSE_SYNC_SECRET") ?? "";
const AWARD_ENDPOINT = `${V24_URL}/api/v1/economy/award-from-course`;

interface TokenTransaction {
  id: number;
  user_id: string;           // Supabase auth UUID
  discord_id?: string | null;
  amount: number;
  transaction_type: string;  // "earn" | "spend" | "bonus" | ...
  description?: string | null;
  created_at: string;
}

interface WebhookPayload {
  type: "INSERT" | "UPDATE" | "DELETE";
  table: string;
  record: TokenTransaction;
  old_record?: TokenTransaction | null;
}

serve(async (req: Request) => {
  // ── Guard: only accept POST from Supabase webhooks ─────────────────────
  if (req.method !== "POST") {
    return new Response("Method Not Allowed", { status: 405 });
  }

  let payload: WebhookPayload;
  try {
    payload = await req.json();
  } catch {
    return new Response("Bad JSON", { status: 400 });
  }

  // Only process INSERT events on token_transactions
  if (payload.type !== "INSERT" || payload.table !== "token_transactions") {
    return new Response(JSON.stringify({ skipped: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  const tx = payload.record;

  // Only sync "earn"-type transactions (don't sync spends or admin adjustments)
  if (!["earn", "bonus", "reward"].includes(tx.transaction_type)) {
    return new Response(
      JSON.stringify({ skipped: true, reason: `transaction_type=${tx.transaction_type} not synced` }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  }

  if (!tx.discord_id) {
    // User hasn't linked Discord — skip silently
    return new Response(
      JSON.stringify({ skipped: true, reason: "no discord_id on transaction" }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  }

  if (!V24_URL || !SYNC_SECRET) {
    console.error("HYPERCODE_V24_URL or COURSE_SYNC_SECRET not set");
    return new Response("Edge function misconfigured", { status: 500 });
  }

  // ── Forward to V2.4 ────────────────────────────────────────────────────
  const body = JSON.stringify({
    source_id: `course_tx_${tx.id}`,
    discord_id: tx.discord_id,
    tokens: Math.abs(tx.amount),
    reason: tx.description ?? "Course reward",
  });

  let v24Res: Response;
  try {
    v24Res = await fetch(AWARD_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Sync-Secret": SYNC_SECRET,
      },
      body,
    });
  } catch (err) {
    console.error("Failed to reach V2.4:", err);
    // Return 500 so Supabase retries the webhook delivery
    return new Response(JSON.stringify({ error: "V2.4 unreachable", detail: String(err) }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }

  // 409 = already processed (idempotent re-delivery) — treat as success
  if (v24Res.status === 409) {
    console.log(`source_id=course_tx_${tx.id} already processed — skipping`);
    return new Response(JSON.stringify({ synced: false, reason: "already_processed" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  if (!v24Res.ok) {
    const detail = await v24Res.text();
    console.error(`V2.4 award failed: status=${v24Res.status} body=${detail}`);
    // Non-200/409 → return 500 so Supabase retries
    return new Response(JSON.stringify({ error: "V2.4 award failed", detail }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }

  const result = await v24Res.json();
  console.log(`✅ Token sync: course_tx_${tx.id} → discord=${tx.discord_id} +${tx.amount} BROski$`);

  return new Response(JSON.stringify({ synced: true, ...result }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
});
