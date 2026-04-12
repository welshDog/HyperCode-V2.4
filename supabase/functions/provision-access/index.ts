/**
 * provision-access — Supabase Edge Function
 * Phase 3: Agent Access + Shop Bridge
 *
 * Triggered by a Supabase Database Webhook on:
 *   Table: shop_purchases
 *   Event: INSERT
 *
 * Filters for item_slug = "agent-sandbox-access" (300 tokens).
 * Calls V2.4 POST /api/v1/access/provision which:
 *   - generates api_key
 *   - stores access_provisions record
 *   - sends Discord DM to the student
 *
 * Idempotency: source_id = shop_purchases.id
 *   V2.4 returns 409 if already provisioned — edge fn treats 409 as success.
 *
 * Deploy to: Hyper-Vibe-Coding-Course Supabase project
 *
 * Env vars required:
 *   HYPERCODE_V24_URL   — https://api.hypercode.dev (no trailing slash)
 *   SHOP_SYNC_SECRET    — shared secret matching SHOP_SYNC_SECRET in V2.4 .env
 *   SUPABASE_URL        — injected automatically
 *   SUPABASE_ANON_KEY   — injected automatically
 */

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const V24_URL      = Deno.env.get("HYPERCODE_V24_URL") ?? "";
const SHOP_SECRET  = Deno.env.get("SHOP_SYNC_SECRET")  ?? "";
const PROVISION_ENDPOINT = `${V24_URL}/api/v1/access/provision`;

// The item slug that triggers sandbox provisioning
const PROVISIONABLE_SLUG = "agent-sandbox-access";

interface ShopPurchase {
  id: number;
  user_id: string;          // Supabase auth UUID
  item_id?: number;
  item_slug?: string;
  tokens_spent?: number;
  metadata?: Record<string, unknown>;
  created_at: string;
}

interface WebhookPayload {
  type: "INSERT" | "UPDATE" | "DELETE";
  table: string;
  record: ShopPurchase;
  old_record?: ShopPurchase | null;
}

serve(async (req: Request) => {
  if (req.method !== "POST") {
    return new Response("Method Not Allowed", { status: 405 });
  }

  let payload: WebhookPayload;
  try {
    payload = await req.json();
  } catch {
    return new Response("Bad JSON", { status: 400 });
  }

  // Only process INSERT on shop_purchases
  if (payload.type !== "INSERT" || payload.table !== "shop_purchases") {
    return new Response(JSON.stringify({ skipped: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  const purchase = payload.record;

  // Only provision for the right item slug
  if (purchase.item_slug !== PROVISIONABLE_SLUG) {
    return new Response(
      JSON.stringify({ skipped: true, reason: `item_slug '${purchase.item_slug}' not provisionable` }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  }

  if (!V24_URL || !SHOP_SECRET) {
    console.error("HYPERCODE_V24_URL or SHOP_SYNC_SECRET not configured");
    return new Response("Edge function misconfigured", { status: 500 });
  }

  // ── Resolve discord_id from Supabase users table ───────────────────────
  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_ANON_KEY")!,
  );

  const { data: courseUser, error: userErr } = await supabase
    .from("users")
    .select("discord_id")
    .eq("id", purchase.user_id)
    .single();

  if (userErr || !courseUser?.discord_id) {
    console.warn(
      `No discord_id for user ${purchase.user_id} (purchase ${purchase.id}) — cannot provision`,
    );
    // Return 200 so the webhook doesn't retry forever.
    // Student needs to link Discord first, then can re-trigger via support.
    return new Response(
      JSON.stringify({ skipped: true, reason: "user has no discord_id linked" }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  }

  // ── Forward to V2.4 ────────────────────────────────────────────────────
  const body = JSON.stringify({
    source_id:  `shop_purchase_${purchase.id}`,
    discord_id: courseUser.discord_id,
    item_slug:  PROVISIONABLE_SLUG,
  });

  let v24Res: Response;
  try {
    v24Res = await fetch(PROVISION_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Sync-Secret": SHOP_SECRET,
      },
      body,
    });
  } catch (err) {
    console.error("Failed to reach V2.4:", err);
    return new Response(
      JSON.stringify({ error: "V2.4 unreachable", detail: String(err) }),
      { status: 500, headers: { "Content-Type": "application/json" } },
    );
  }

  // 409 = already provisioned — idempotent re-delivery, treat as success
  if (v24Res.status === 409) {
    console.log(`shop_purchase_${purchase.id} already provisioned — skipping`);
    return new Response(JSON.stringify({ provisioned: false, reason: "already_provisioned" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  if (!v24Res.ok) {
    const detail = await v24Res.text();
    console.error(`V2.4 provision failed: status=${v24Res.status} body=${detail}`);
    return new Response(
      JSON.stringify({ error: "V2.4 provision failed", detail }),
      { status: 500, headers: { "Content-Type": "application/json" } },
    );
  }

  const result = await v24Res.json();
  console.log(
    `✅ Sandbox provisioned: shop_purchase_${purchase.id} → discord=${courseUser.discord_id}`,
  );

  return new Response(JSON.stringify({ provisioned: true, ...result }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
});
