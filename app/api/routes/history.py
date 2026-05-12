"""GET /api/scans — scan history, last 50."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.scan import Finding as FindingORM
from app.models.scan import Scan
from app.schemas.scan import ScanHistoryItem

router = APIRouter()


@router.get("/scans", response_model=list[ScanHistoryItem])
async def list_scans(
    session: AsyncSession = Depends(get_session),
) -> list[ScanHistoryItem]:
    result = await session.execute(
        select(
            Scan,
            func.count(FindingORM.id).label("finding_count"),
        )
        .outerjoin(FindingORM, FindingORM.scan_id == Scan.id)
        .group_by(Scan.id)
        .order_by(Scan.scanned_at.desc())
        .limit(50)
    )
    rows = result.all()
    return [
        ScanHistoryItem(
            scan_id=scan.id,
            filename=scan.filename,
            status=scan.status,
            risk_score=scan.risk_score,
            finding_count=int(count),
            scanned_at=scan.scanned_at,
        )
        for scan, count in rows
    ]
