"""Pydantic response schemas — only fields actually supported by real data."""
from typing import Optional, List
from pydantic import BaseModel


class Evidence(BaseModel):
    source: str
    source_url: Optional[str] = None


class WorkOrderReport(BaseModel):
    wo_id: Optional[str] = None
    description: Optional[str] = None
    contractor: Optional[str] = None
    amount: Optional[float] = None
    payment_ref: Optional[str] = None
    source_url: Optional[str] = None


class ProjectReport(BaseModel):
    title: str
    tender_number: Optional[str] = None
    amount: Optional[float] = None
    tender_date: Optional[str] = None
    tender_last_date: Optional[str] = None   # tender CLOSING date, NOT a project deadline
    category: Optional[str] = None
    status: str                               # from Checker (e.g. NO_COMPLETION_INFORMATION)
    finding: str                              # from Investigator
    evidence: List[Evidence] = []


class ComplaintSummary(BaseModel):
    total: int
    top_categories: list = []
    note: str


class ReportResponse(BaseModel):
    ward: str
    ward_number: Optional[int] = None
    ward_name: Optional[str] = None
    zone: Optional[str] = None
    projects: List[ProjectReport] = []
    work_orders: List[WorkOrderReport] = []
    complaints: Optional[ComplaintSummary] = None
    findings: List[str] = []
    assessment: Optional[str] = None
    summary: Optional[str] = None
    summary_generated_by: Optional[str] = None
    message: Optional[str] = None
    data_vintage_note: str = "Public records here cover FY 2017-18 tenders, 2021-26 work-order payments, and 2024 grievances."
