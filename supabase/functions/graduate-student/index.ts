import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const V24_URL = Deno.env.get("V24_API_URL")!;
const SYNC_SECRET = Deno.env.get("SHOP_SYNC_SECRET")!;
const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

Deno.serve(async (req: Request) => {
  // Called by Supabase webhook on graduation_events INSERT
  const body = await req.json();
  const record = body.record;

  if (!record) {
    return new Response(JSON.stringify({ error: "No record" }), { status: 400 });
  }

  const { id, discord_id, portfolio_url } = record;

  if (!discord_id) {
    return new Response(JSON.stringify({ skipped: "no discord_id" }), { status: 200 });
  }

  // Look up student for portfolio URL if not set
  let finalPortfolioUrl = portfolio_url;
  if (!finalPortfolioUrl) {
    const { data: user } = await supabase
      .from("users")
      .select("portfolio_url")
      .eq("discord_id", discord_id)
      .single();
    finalPortfolioUrl = user?.portfolio_url ?? null;
  }

  // POST to V2.4 graduate endpoint
  const resp = await fetch(`${V24_URL}/api/v1/graduate/trigger`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Sync-Secret": SYNC_SECRET,
    },
    body: JSON.stringify({
      discord_id,
      source_id: `graduation_${id}`,
      badge_slug: "hyper-graduate",
      tokens_awarded: 500,
      portfolio_url: finalPortfolioUrl,
    }),
  });

  const result = await resp.json();

  if (resp.status === 409) {
    // Already graduated — idempotent, not an error
    return new Response(JSON.stringify({ status: "already_graduated", ...result }), { status: 200 });
  }

  if (!resp.ok) {
    return new Response(JSON.stringify({ error: "V2.4 graduation failed", ...result }), { status: 500 });
  }

  return new Response(JSON.stringify({ status: "graduated", ...result }), {
    headers: { "Content-Type": "application/json" },
  });
});
