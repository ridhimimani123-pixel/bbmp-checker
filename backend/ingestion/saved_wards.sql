-- PHASE 6 (updated) — "My Saved Wards" list (run in Supabase SQL Editor)
-- Multiple saved wards per user are allowed; duplicates of the same ward are not.

create table if not exists saved_wards (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  ward text not null,
  created_at timestamptz default now()
);

-- one row per (user, ward): prevents saving the same ward twice at the DB level
create unique index if not exists saved_wards_user_ward_uidx
  on saved_wards (user_id, ward);

alter table saved_wards enable row level security;

create policy "users can read own saved wards"
  on saved_wards for select
  using (auth.uid() = user_id);

create policy "users can save own wards"
  on saved_wards for insert
  with check (auth.uid() = user_id);

create policy "users can update own saved wards"
  on saved_wards for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "users can delete own saved wards"
  on saved_wards for delete
  using (auth.uid() = user_id);
