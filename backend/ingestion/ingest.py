"""
WHOSE MONEY? — Phase 2 ingestion: wards, tenders, work orders, complaints.

Run options:
  python -m backend.ingestion.ingest --wards                 # load 198-ward lookup (fast)
  python -m backend.ingestion.ingest --tenders --limit 20    # 20-row TEST first
  python -m backend.ingestion.ingest --tenders               # full load (6,842 rows)
  python -m backend.ingestion.ingest --work-orders           # 4,729 rows
  python -m backend.ingestion.ingest --complaints --limit 2000  # sample of 207K
"""
import argparse
import csv
import difflib
import html
import json
import re
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from backend import config  # noqa: E402

import requests  # noqa: E402

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
REST = f"{config.SUPABASE_URL}/rest/v1"
HEADERS = {
    "apikey": config.SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=representation",
}

# Resilient session: retry on connection resets / 5xx with backoff
from requests.adapters import HTTPAdapter  # noqa: E402
from urllib3.util.retry import Retry  # noqa: E402

_session = requests.Session()
_retry = Retry(total=5, connect=5, read=5, backoff_factor=1.5,
               status_forcelist=[429, 500, 502, 503, 504],
               allowed_methods=None)
_session.mount("https://", HTTPAdapter(max_retries=_retry))
BATCH_SIZE = 200

WARD_RE = re.compile(r"ward\s*(?:no\.?\s*[-–]?\s*|number\s*)?(\d{1,3})", re.I)
WARD_NAME_RE = re.compile(r"ward\s*(?:no\.?\s*[-–]?\s*)?[a-z]")

_month_map = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
              "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def parse_amount(raw):
    """'3,333,233' -> 3333233 | 'Not Available'/'' -> None. Never invent."""
    if not raw:
        return None
    s = str(raw).strip().replace(",", "")
    if not s or s.lower().startswith("not") or not s.replace(".", "").isdigit():
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_dmy(raw):
    """DD/MM/YYYY -> ISO date string, else None."""
    if not raw or not raw.strip():
        return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_ymd(raw):
    if not raw or not raw.strip():
        return None
    try:
        return datetime.strptime(raw.strip()[:10], "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def extract_ward_number(title):
    m = WARD_RE.search(title or "")
    if not m:
        return None
    n = int(m.group(1))
    return n if 1 <= n <= 198 else None


def clean_text(s):
    return html.unescape(s or "").strip()


def post_rows(table, rows):
    """Insert via Supabase REST, batched. Returns count inserted."""
    if not rows:
        return 0
    inserted = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        r = _session.post(f"{REST}/{table}", headers=HEADERS, json=batch, timeout=120)
        if r.status_code >= 300:
            print(f"  ERROR inserting batch into {table}: {r.status_code} {r.text[:300]}")
            sys.exit(1)
        inserted += len(batch)
    return inserted


def upsert_row(table, match_col, match_val, payload):
    """Insert or update a single row matched on match_col."""
    r = _session.post(
        f"{REST}/{table}", headers=HEADERS,
        params={match_col: f"eq.{match_val}"},
        json=payload, timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    return data[0] if data else None


def table_count(table):
    r = _session.head(f"{REST}/{table}", headers=HEADERS,
                      params={"select": "id"}, timeout=30)
    cr = r.headers.get("content-range", "*/0")
    return int(cr.split("/")[-1])


# ---------------------------------------------------------------- loaders

def load_wards():
    path = os.path.join(DATA_DIR, "wards_mapping.csv")
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "ward_number": int(r["Ward No"]),
                "ward_name": clean_text(r["Ward Name"]),
                "locality": clean_text(r["Ward Name"]),
                "zone": clean_text(r["BBMP Zone Name"]),
            })
    n = post_rows("wards", rows)
    print(f"wards: attempted={len(rows)} inserted={n}")


def get_ward_index():
    """ward_number -> ward id (fetch the whole small table once)."""
    r = _session.get(f"{REST}/wards", headers=HEADERS,
                     params={"select": "id,ward_number"}, timeout=60)
    r.raise_for_status()
    return {row["ward_number"]: row["id"] for row in r.json()}


def norm_ward_name(s):
    """Normalize a ward name for tolerant matching, e.g. J.P. Nagar Ward -> jpnagar."""
    s = (s or "").lower().strip()
    s = re.sub(r"\bward\b", "", s)
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def build_ward_name_index():
    """normalized ward name -> ward row, from the wards table."""
    r = _session.get(f"{REST}/wards", headers=HEADERS,
                     params={"select": "id,ward_number,ward_name"}, timeout=60)
    r.raise_for_status()
    idx = {}
    for row in r.json():
        name = norm_ward_name(row["ward_name"])
        if name:
            idx[name] = row
    return idx


def resolve_ward_name(raw_name, by_norm, cache):
    """exact -> normalized -> fuzzy (cutoff 0.84). None if unresolvable."""
    raw = (raw_name or "").strip()
    if not raw:
        return None
    if raw in cache:
        return cache[raw]
    row = by_norm.get(norm_ward_name(raw))
    if row is None:
        close = difflib.get_close_matches(norm_ward_name(raw), list(by_norm.keys()), n=1, cutoff=0.84)
        if close:
            row = by_norm[close[0]]
    cache[raw] = row
    return row


def load_tenders(limit=None):
    path = os.path.join(DATA_DIR, "tenders_2017_2018.csv")
    ward_index = get_ward_index()
    rows = []
    stats = {"no_ward": 0, "no_amount": 0, "no_date": 0}
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            title = clean_text(r["Tender Title"])
            ward_no = extract_ward_number(title)
            if ward_no is None:
                stats["no_ward"] += 1
            amount = parse_amount(r["Tender Value in Rs"])
            if amount is None:
                stats["no_amount"] += 1
            tdate = parse_dmy(r["Published Date"])
            ldate = parse_dmy(r["Last Date"])
            if not tdate:
                stats["no_date"] += 1
            rows.append({
                "ward_id": ward_index.get(ward_no),
                "title": title,
                "description": None,
                "tender_number": clean_text(r["Tender Number"]),
                "tender_amount": amount,
                "tender_date": tdate,
                "tender_last_date": ldate,
                "category": clean_text(r["Category"]),
                "sub_category": clean_text(r["Sub-Category"]),
                "department": clean_text(r["Department-Location"]),
                "source": config.TENDER_SOURCE,
                "source_url": config.TENDER_SOURCE_URL,
            })
            if limit and len(rows) >= limit:
                break
    n = post_rows("tenders", rows)
    print(f"tenders: attempted={len(rows)} inserted={n} | skipped: "
          f"no_ward={stats['no_ward']} no_amount={stats['no_amount']} no_date={stats['no_date']}")
    for sample in rows[:3]:
        print("  sample:", json.dumps(sample, ensure_ascii=False)[:220])


def load_work_orders(limit=None):
    path = os.path.join(DATA_DIR, "work_orders_2025_26_198wards.csv")
    ward_index = get_ward_index()
    rows = []
    skipped = 0
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            try:
                ward_no = int(r["ward"])
            except (TypeError, ValueError):
                skipped += 1
                continue
            desc = clean_text(re.sub(r"^\d{3}-\d{2}-\d{6}", "", re.sub(r"</a>", " ", r.get("wodetails") or "")))
            contractor = clean_text(re.sub(r"\d{6,}", "", r.get("contractor") or ""))  # strip glued phone no.
            payment = clean_text((r.get("brnumber") or "").replace("\n", " "))
            rows.append({
                "ward_id": ward_index.get(ward_no),
                "wo_id": clean_text(r.get("id")),
                "description": desc,
                "contractor": contractor or None,
                "amount": parse_amount(r.get("amount")),
                "payment_ref": payment or None,
                "source": config.WO_SOURCE,
                "source_url": config.WO_SOURCE_URL,
            })
            if limit and len(rows) >= limit:
                break
    n = post_rows("work_orders", rows)
    print(f"work_orders: attempted={len(rows)} inserted={n} skipped_bad_ward={skipped}")
    for sample in rows[:3]:
        print("  sample:", json.dumps(sample, ensure_ascii=False)[:220])


def load_complaints(limit=None):
    path = os.path.join(DATA_DIR, "grievances_2024.csv")
    name_index = build_ward_name_index()
    cache = {}
    rows = []
    skipped = 0
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            ward = resolve_ward_name(clean_text(r.get("Ward Name")), name_index, cache)
            if ward is None:
                skipped += 1
                continue
            rows.append({
                "ward_id": ward["id"],
                "complaint_id": clean_text(r.get("Complaint ID")),
                "category": clean_text(r.get("Category")),
                "sub_category": clean_text(r.get("Sub Category")),
                "description": clean_text(r.get("Staff Remarks")) or None,
                "location": None,
                "complaint_date": parse_ymd(r.get("Grievance Date")),
                "status": clean_text(r.get("Grievance Status")) or None,
                "source": config.GRIEV_SOURCE,
                "source_url": config.GRIEV_SOURCE_URL,
            })
            if limit and len(rows) >= limit:
                break
    n = post_rows("complaints", rows)
    print(f"complaints: attempted={len(rows)} inserted={n} skipped_unknown_ward_name={skipped}")
    for sample in rows[:3]:
        print("  sample:", json.dumps(sample, ensure_ascii=False)[:220])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--wards", action="store_true")
    ap.add_argument("--tenders", action="store_true")
    ap.add_argument("--work-orders", action="store_true")
    ap.add_argument("--complaints", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    if args.wards:
        load_wards()
    if args.tenders:
        load_tenders(args.limit)
    if args.work_orders:
        load_work_orders(args.limit)
    if args.complaints:
        load_complaints(args.limit)
    if not any([args.wards, args.tenders, args.work_orders, args.complaints]):
        print(__doc__)
