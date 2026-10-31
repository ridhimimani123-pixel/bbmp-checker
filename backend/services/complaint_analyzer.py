"""AGENT 3 — COMPLAINT ANALYZER: ward-level complaint context.

Complaint volume is supporting context only — NEVER proof of non-completion.
Complaints link to wards, not to individual tenders (no project id in source).
"""


def analyze(collected):
    cats = {}
    for c in collected["complaint_categories"]:
        key = c.get("category") or "Uncategorised"
        cats[key] = cats.get(key, 0) + 1
    top = sorted(cats.items(), key=lambda kv: -kv[1])[:5]
    return {
        "total": collected["complaint_count"],
        "top_categories": [{"category": k, "count": v} for k, v in top],
        "note": ("Grievance counts are ward-wide for 2024 and are context only — "
                 "they are not evidence about any specific tender or contractor."),
    }
