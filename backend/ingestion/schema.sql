-- WHOSE MONEY? — Supabase schema (run in Supabase SQL Editor)
-- Paste this whole file and click Run.

create table if not exists wards (
  id bigint generated always as identity primary key,
  ward_number int unique,
  ward_name text,
  locality text,
  zone text
);

create table if not exists tenders (
  id bigint generated always as identity primary key,
  ward_id bigint references wards(id),
  title text,
  description text,
  tender_number text,
  tender_amount numeric,
  tender_date date,
  tender_last_date date,   -- tender CLOSING date, NOT a project deadline
  category text,
  sub_category text,
  department text,
  source text,
  source_url text
);

create table if not exists work_orders (
  id bigint generated always as identity primary key,
  ward_id bigint references wards(id),
  wo_id text,
  description text,
  contractor text,
  amount numeric,
  payment_ref text,
  source text,
  source_url text
);

create table if not exists complaints (
  id bigint generated always as identity primary key,
  ward_id bigint references wards(id),
  complaint_id text,
  category text,
  sub_category text,
  description text,
  location text,
  complaint_date date,
  status text,
  source text,
  source_url text
);

create table if not exists evidence (
  id bigint generated always as identity primary key,
  project_id bigint references tenders(id),
  evidence_type text,
  title text,
  source text,
  source_url text,
  relevant_text text
);

create table if not exists investigations (
  id bigint generated always as identity primary key,
  project_id bigint references tenders(id),
  status_assessment text,
  discrepancy_score int,
  findings jsonb,
  explanation text,
  created_at timestamptz default now()
);

create index if not exists idx_tenders_ward on tenders(ward_id);
create index if not exists idx_work_orders_ward on work_orders(ward_id);
create index if not exists idx_complaints_ward on complaints(ward_id);
create index if not exists idx_tenders_number on tenders(tender_number);
