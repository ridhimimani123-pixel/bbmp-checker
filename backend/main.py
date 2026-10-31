"""WHOSE MONEY? — FastAPI backend. GET /report?ward=<number|name>"""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.schemas import (ReportResponse, ProjectReport, WorkOrderReport,
                             ComplaintSummary, Evidence)
from backend.services import collector, checker, complaint_analyzer, investigator, explainer

app = FastAPI(title="WHOSE MONEY? — BBMP Ward Accountability Checker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # hackathon: public demo; restrict later if deployed
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    try:
        collector.resolve_ward("101")
        return {"ok": True, "database": "reachable"}
    except Exception:
        return JSONResponse(status_code=503, content={"ok": False, "database": "unreachable"})


@app.get("/report")
def report(ward: str = Query(..., min_length=1, max_length=80)):
    try:
        w = collector.resolve_ward(ward)
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"detail": "Report service temporarily unavailable — could not reach the records database. Try again shortly."},
        )
    if w is None:
        return ReportResponse(
            ward=ward,
            projects=[],
            message="No public records found for this ward. Try a ward number 1-198 or a ward name.",
        )

    collected = collector.collect(w["id"])
    checker_results = checker.check_all(collected["tenders"])
    complaints = complaint_analyzer.analyze(collected)
    investigation = investigator.investigate_ward(w, collected, checker_results, complaints)

    projects = []
    for cr in checker_results:
        t = cr["tender"]
        inv = investigator.investigate_project(t, cr["status"])
        projects.append(ProjectReport(
            title=t.get("title") or "(untitled tender)",
            tender_number=t.get("tender_number"),
            amount=t.get("tender_amount"),
            tender_date=t.get("tender_date"),
            tender_last_date=t.get("tender_last_date"),
            category=t.get("category"),
            status=cr["status"],
            finding=inv["finding"],
            evidence=[Evidence(source=t.get("source") or "OpenCity BBMP Tenders",
                               source_url=t.get("source_url"))],
        ))

    work_orders = [WorkOrderReport(
        wo_id=wo.get("wo_id"),
        description=wo.get("description"),
        contractor=wo.get("contractor"),
        amount=wo.get("amount"),
        payment_ref=wo.get("payment_ref"),
        source_url=wo.get("source_url"),
    ) for wo in collected["work_orders"]]

    summary = explainer.explain(w, collected, complaints, investigation)

    return ReportResponse(
        ward=f"{w['ward_number']}",
        ward_number=w["ward_number"],
        ward_name=w["ward_name"],
        zone=w.get("zone"),
        projects=projects,
        work_orders=work_orders,
        complaints=ComplaintSummary(**complaints),
        findings=investigation["findings"],
        assessment=investigation["assessment"],
        summary=summary["summary"],
        summary_generated_by=summary["generated_by"],
    )
