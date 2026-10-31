"""AGENT 4 — INVESTIGATOR: transparent findings from plain conditionals.

Finding vocabulary (spec):
  No issue identified / Potential discrepancy / Project appears overdue /
  No completion information found / Conflicting public records /
  Insufficient information
Indicators are a visible checklist — never a corruption probability.
"""


def _fmt_money(v):
    if v is None:
        return None
    if v >= 1e7:
        return f"Rs {v/1e7:.2f} crore"
    if v >= 1e5:
        return f"Rs {v/1e5:.2f} lakh"
    return f"Rs {v:,.0f}"


def investigate_project(tender, status):
    indicators = []
    if status == "NO_COMPLETION_INFORMATION":
        finding = "No completion information found"
        indicators.append("no completion status in public records")
        indicators.append("public records end at the tender stage")
    elif status == "OVERDUE":
        finding = "Project appears overdue"
    else:
        finding = "Insufficient information"
    if tender.get("tender_amount") is None:
        indicators.append("tender amount not published")
    if tender.get("ward_id") is None:
        indicators.append("ward not identifiable in title")
    return {"finding": finding, "indicators": indicators}


def investigate_ward(ward, collected, checker_results, complaints):
    findings = []
    tenders = collected["tenders"]
    total_amount = sum(t["tender_amount"] or 0 for t in tenders)
    if tenders:
        findings.append(
            f"{len(tenders)} tenders published for this ward in FY 2017-18 "
            f"({sum(1 for t in tenders if t['tender_amount'] is None)} without a published amount)."
        )
        findings.append("No public completion status exists for any of them — status unknown.")
    if collected["work_orders"]:
        wo_total = sum(w["amount"] or 0 for w in collected["work_orders"])
        findings.append(
            f"{len(collected['work_orders'])} work orders with payments "
            f"({_fmt_money(wo_total) if wo_total else 'amounts unavailable'}) appear in later records (2021-26)."
        )
    if complaints["total"]:
        findings.append(f"{complaints['total']} citizen grievances were recorded in 2024 (context only).")
    return {
        "tender_total_amount": total_amount,
        "findings": findings,
        "assessment": "Requires civic verification — public records are incomplete.",
    }
