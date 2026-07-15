-- BROski Discord Bot — Supabase Schema
-- Run this in your Supabase SQL editor

create table if not exists broski_members (
  id                   uuid primary key default gen_random_uuid(),
  discord_id           text unique not null,
  username             text,
  broski_coins         integer default 100,
  xp                   integer default 0,
  focus_start          timestamptz,
  total_focus_minutes  integer default 0,
  created_at           timestamptz default now()
);

create table if not exists broski_transactions (
  id          uuid primary key default gen_random_uuid(),
  discord_id  text not null references broski_members(discord_id),
  amount      integer not null,
  reason      text,
  timestamp   timestamptz default now()
);

-- Index for fast lookups
create index if not exists idx_members_discord_id on broski_members(discord_id);
create index if not exists idx_txn_discord_id     on broski_transactions(discord_id);

-- RLS policies
alter table broski_members     enable row level security;
alter table broski_transactions enable row level security;

-- Service role has full access (bot uses service key)
create policy "service_full_access_members" on broski_members
  for all using (true) with check (true);
create policy "service_full_access_txn" on broski_transactions
  for all using (true) with check (true);
