/**
 * course-profile — Supabase Edge Function
 * Phase 1: Identity Bridge
 *
 * Fetches a user's full cross-system profile by Discord ID:
 *   - Course data from Supabase (XP, level, BROski$ tokens, lessons completed)
 *   - HyperCode platform data from the V2.4 API (projects, tasks, role)
 *
 * Deploy to: Hyper-Vibe-Coding-Course Supabase project
 * Invoke:    GET /functions/v1/course-profile?discord_id=<snowflake>
 *
 * Env vars required:
 *   HYPERCODE_API_URL  — e.g. https://api.hypercode.dev  (or http://hypercode-core:8000 in local)
 *   SUPABASE_URL       — injected automatically by Supabase
 *   SUPABASE_ANON_KEY  — injected automatically by Supabase
 */

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const HYPERCODE_API_URL = Deno.env.get("HYPERCODE_API_URL") ?? "http://hypercode-core:8000";

serve(async (req: Request) => {
  const url = new URL(req.url);
  const discordId = url.searchParams.get("discord_id");

  if (!discordId) {
    return new Response(
      JSON.stringify({ error: "discord_id query param is required" }),
      { status: 400, headers: { "Content-Type": "application/json" } },
    );
  }

  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_ANON_KEY")!,
  );

  // ── Course profile from Supabase ──────────────────────────────────────────
  const { data: courseUser, error: courseErr } = await supabase
    .from("users")
    .select(`
      id,
      discord_id,
      username,
      xp,
      level,
      broski_tokens,
      created_at,
      user_progress ( lesson_id, completed_at, score )
    `)
    .eq("discord_id", discordId)
    .single();

  if (courseErr && courseErr.code !== "PGRST116") {
    return new Response(
      JSON.stringify({ error: "Course DB error", detail: courseErr.message }),
      { status: 500, headers: { "Content-Type": "application/json" } },
    );
  }

  // ── HyperCode platform profile ────────────────────────────────────────────
  let hypercodeUser: Record<string, unknown> | null = null;
  try {
    const hcRes = await fetch(
      `${HYPERCODE_API_URL}/api/v1/users/by-discord/${discordId}`,
      { headers: { "Accept": "application/json" } },
    );
    if (hcRes.ok) {
      hypercodeUser = await hcRes.json();
    }
  } catch {
    // HyperCode is optional — don't fail the whole response if it's down
  }

  const lessonsCompleted = (courseUser?.user_progress ?? []).length;

  return new Response(
    JSON.stringify({
      discord_id: discordId,
      course: courseUser
        ? {
            username: courseUser.username,
            xp: courseUser.xp,
            level: courseUser.level,
            broski_tokens: courseUser.broski_tokens,
            lessons_completed: lessonsCompleted,
            joined: courseUser.created_at,
          }
        : null,
      hypercode: hypercodeUser
        ? {
            id: hypercodeUser.id,
            email: hypercodeUser.email,
            full_name: hypercodeUser.full_name,
            role: hypercodeUser.role,
            is_active: hypercodeUser.is_active,
          }
        : null,
    }),
    { status: 200, headers: { "Content-Type": "application/json" } },
  );
});
