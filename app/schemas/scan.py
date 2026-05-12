"""Pydantic v2 request/response schemas — the full governance contract for every API surface."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class FindingResponse(BaseModel):
    rule_id: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM"]
    title: str
    description: str
    remediation: str
    resource_name: str
    resource_type: str

    model_config = {"frozen": True}


class ScanQueuedResponse(BaseModel):
    scan_id: str
    status: str


class ScanResponse(BaseModel):
    scan_id: str
    filename: str
    status: str
    risk_score: int | None = Field(None, ge=0, le=100)
    findings: list[FindingResponse] = Field(default_factory=list)
    summary: str | None = None
    scanned_at: datetime

    model_config = {"from_attributes": True}


class ScanHistoryItem(BaseModel):
    scan_id: str
    filename: str
    status: str
    risk_score: int | None = Field(None, ge=0, le=100)
    finding_count: int = 0
    scanned_at: datetime

    model_config = {"from_attributes": True}
