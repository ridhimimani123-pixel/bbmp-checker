"""AGENT 1 — COLLECTOR: resolve the ward, gather all public records for it."""
import re
import difflib

from backend import database as db


def _norm(s):
    s = (s or "").lower().strip()
    s = re.sub(r"\bward\b", "", s)
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def resolve_ward(q):
    """'83' / 'ward 83' -> ward by number. 'Kadugodi' -> exact/norm/fuzzy name match."""
    q = (q or "").strip()[:80]
    if not q:
        return None
    m = re.search(r"\d{1,3}", q)
    if m:
        rows = db.query("wards", {"ward_number": f"eq.{int(m.group())}"}, limit=1)
        if rows:
            return rows[0]
    matches = db.query("wards", {"ward_name": f"ilike.{q}"}, limit=1)
    if matches:
        return matches[0]
    all_wards = db.query("wards")
    by_norm = {_norm(w["ward_name"]): w for w in all_wards}
    hit = by_norm.get(_norm(q))
    if hit:
        return hit
    close = difflib.get_close_matches(_norm(q), list(by_norm), n=1, cutoff=0.84)
    return by_norm[close[0]] if close else None


def collect(ward_id):
    """All records tied to this ward. Missing data stays missing — never invented."""
    tenders = db.query("tenders", {"ward_id": f"eq.{ward_id}", "order": "tender_date.desc"})
    work_orders = db.query("work_orders", {"ward_id": f"eq.{ward_id}"})
    complaint_count = db.count("complaints", {"ward_id": f"eq.{ward_id}"})
    categories = db.query("complaints", {"ward_id": f"eq.{ward_id}", "select": "category,sub_category"})
    return {
        "tenders": tenders,
        "work_orders": work_orders,
        "complaint_count": complaint_count,
        "complaint_categories": categories,
    }
