"""GET /dashboard — Jinja2 HTML dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.scan import Finding as FindingORM
from app.models.scan import Scan

router = APIRouter()
templates = Jinja2Templates(directory="app/dashboard/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> HTMLResponse:
    scans_result = await session.execute(
        select(
            Scan,
            func.count(FindingORM.id).label("finding_count"),
        )
        .outerjoin(FindingORM, FindingORM.scan_id == Scan.id)
        .group_by(Scan.id)
        .order_by(Scan.scanned_at.desc())
        .limit(10)
    )
    recent_scans = [
        {
            "scan_id": scan.id,
            "filename": scan.filename,
            "status": scan.status,
            "risk_score": scan.risk_score,
            "finding_count": int(count),
            "scanned_at": scan.scanned_at.strftime("%Y-%m-%d %H:%M"),
        }
        for scan, count in scans_result.all()
    ]

    severity_counts_result = await session.execute(
        select(FindingORM.severity, func.count(FindingORM.id))
        .group_by(FindingORM.severity)
    )
    severity_counts = {row[0]: row[1] for row in severity_counts_result.all()}

    rule_counts_result = await session.execute(
        select(FindingORM.rule_id, func.count(FindingORM.id))
        .group_by(FindingORM.rule_id)
        .order_by(func.count(FindingORM.id).desc())
        .limit(5)
    )
    top_rules = [{"rule_id": r, "count": c} for r, c in rule_counts_result.all()]

    latest_score = recent_scans[0]["risk_score"] if recent_scans else 0

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "recent_scans": recent_scans,
            "severity_counts": severity_counts,
            "top_rules": top_rules,
            "latest_score": latest_score or 0,
        },
    )
