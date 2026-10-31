"""AGENT 5 — EXPLAINER: 2-3 sentence citizen-friendly summary.

Deterministic string formatting is the PRIMARY path (app must work with no AI).
If LLM_API_KEY is set in .env, we try an OpenAI-compatible API first and fall
back to the deterministic text on ANY failure. The LLM only rewrites the
structured facts below — it is told not to invent anything.
"""
import os

import requests

from backend.services.investigator import _fmt_money


def _facts(ward, collected, complaints, investigation):
    top_cat = complaints["top_categories"][0]["category"] if complaints["top_categories"] else None
    return {
        "ward": f"Ward {ward['ward_number']} ({ward['ward_name']})",
        "tender_count": len(collected["tenders"]),
        "tender_total": _fmt_money(investigation["tender_total_amount"]) or "not published",
        "work_order_count": len(collected["work_orders"]),
        "complaint_count": complaints["total"],
        "top_complaint_category": top_cat,
        "completion_status": "unknown in all public records",
    }


def _deterministic(f):
    parts = [
        f"Public BBMP records show {f['tender_count']} tenders for {f['ward']} in FY 2017-18, "
        f"worth about {f['tender_total']} in total."
    ]
    if f["work_order_count"]:
        parts.append(f"{f['work_order_count']} later work orders with payments also appear in public data.")
    parts.append(
        f"No completion status is available for these works — status unknown from public records."
    )
    if f["complaint_count"]:
        cat = f", most often about {f['top_complaint_category'].lower()}" if f["top_complaint_category"] else ""
        parts.append(f"{f['complaint_count']} citizen grievances were filed in this ward in 2024{cat} (context only).")
    return " ".join(parts[:3]) if len(parts) <= 3 else " ".join(parts[:4])


def _llm_rewrite(facts_text):
    """Optional: rewrite the structured facts more naturally. Never called without a key."""
    r = requests.post(
        f"{os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')}/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['LLM_API_KEY']}"},
        json={
            "model": os.environ.get("LLM_MODEL", "gpt-4o-mini"),
            "messages": [
                {"role": "system", "content":
                    "Rewrite the given verified facts as a 2-3 sentence summary for an ordinary citizen. "
                    "Use ONLY these facts. Do not add causes, blame, or any fact not present. "
                    "Say 'status unknown' where completion is unknown."},
                {"role": "user", "content": facts_text},
            ],
            "temperature": 0.2,
        },
        timeout=8,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def explain(ward, collected, complaints, investigation):
    f = _facts(ward, collected, complaints, investigation)
    deterministic = _deterministic(f)
    if os.environ.get("LLM_API_KEY"):
        try:
            return {"summary": _llm_rewrite(deterministic), "generated_by": "llm"}
        except Exception:
            pass
    return {"summary": deterministic, "generated_by": "deterministic"}
