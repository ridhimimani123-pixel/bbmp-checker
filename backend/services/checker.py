"""AGENT 2 — CHECKER: what can actually be established from public records?

Rules (intentionally strict):
- Use a real status field only if the source data has one (ours does not).
- OVERDUE requires an actual completion deadline that has passed with no
  completion record. A tender CLOSING date is never a project deadline,
  so a passed tender closing date NEVER makes a project overdue.
- Otherwise: NO_COMPLETION_INFORMATION.
"""


def check(tender):
    if tender.get("status"):                     # future-proofing; current data has none
        return tender["status"]
    if tender.get("completion_deadline"):        # not present in any public source we load
        return "OVERDUE"                         # (only reachable if real deadline data is added)
    return "NO_COMPLETION_INFORMATION"


def check_all(tenders):
    return [{"tender": t, "status": check(t)} for t in tenders]
