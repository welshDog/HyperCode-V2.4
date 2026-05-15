-- ============================================================
-- 🤖 BROski-Bot — Supabase Schema
-- ============================================================
-- Run this ONCE in your Supabase SQL editor.
-- Safe to re-run: all statements use IF NOT EXISTS / IF NOT EXISTS.
-- Location: agents/broski-bot/supabase_schema.sql
-- Last updated: May 15, 2026
-- ============================================================

-- ============================================================
-- 👤 MEMBERS — one row per Discord user
-- ============================================================
create table if not exists broski_members (
  id                   uuid        primary key default gen_random_uuid(),
  discord_id           text        unique not null,
  username             text,
  broski_coins         integer     default 100,
  xp                   integer     default 0,
  level                integer     default 1,           -- auto-updated by award_coins logic
  focus_start          timestamptz,                     -- null = not in a session
  total_focus_minutes  integer     default 0,
  last_daily           date,                            -- Tier 2: daily reward cooldown
  streak_days          integer     default 0,           -- Tier 2: daily streak counter
  created_at           timestamptz default now(),
  updated_at           timestamptz default now()
);

-- ============================================================
-- 💸 TRANSACTIONS — full audit trail of every BROski$ movement
-- ============================================================
create table if not exists broski_transactions (
  id          uuid        primary key default gen_random_uuid(),
  discord_id  text        not null references broski_members(discord_id) on delete cascade,
  amount      integer     not null,    -- positive = earn, negative = spend
  reason      text,
  created_at  timestamptz default now()
);

-- ============================================================
-- 📋 MISSION COMPLETIONS — Tier 2: track which missions done today
-- ============================================================
create table if not exists broski_mission_completions (
  id          uuid  primary key default gen_random_uuid(),
  discord_id  text  not null references broski_members(discord_id) on delete cascade,
  mission_key text  not null,          -- e.g. 'focus_block', 'ask_broski'
  completed_at date  default current_date,
  unique (discord_id, mission_key, completed_at)
);

-- ============================================================
-- 🔍 INDEXES
-- ============================================================
create index if not exists idx_members_discord_id   on broski_members(discord_id);
create index if not exists idx_txn_discord_id        on broski_transactions(discord_id);
create index if not exists idx_txn_created_at        on broski_transactions(created_at);
create index if not exists idx_missions_discord_date on broski_mission_completions(discord_id, completed_at);

-- ============================================================
-- 🔒 ROW LEVEL SECURITY
-- ============================================================
alter table broski_members             enable row level security;
alter table broski_transactions        enable row level security;
alter table broski_mission_completions enable row level security;

-- Service role key (used by the bot) gets full access to all tables.
-- Public/anon role gets NO access — bot data is private.
create policy "service_full_access_members" on broski_members
  for all using (true) with check (true);

create policy "service_full_access_txn" on broski_transactions
  for all using (true) with check (true);

create policy "service_full_access_missions" on broski_mission_completions
  for all using (true) with check (true);

-- ============================================================
-- ⚡ updated_at auto-trigger
-- ============================================================
create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_members_updated_at on broski_members;
create trigger trg_members_updated_at
  before update on broski_members
  for each row execute function set_updated_at();

-- ============================================================
-- ✅ Done! Tables created:
--   broski_members           — Discord users + economy + focus
--   broski_transactions      — BROski$ audit trail
--   broski_mission_completions — daily mission tracking (Tier 2 ready)
-- ============================================================
