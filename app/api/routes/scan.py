"""POST /api/scan and GET /api/scan/{scan_id} — core scanner API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.models.scan import Finding as FindingORM
from app.models.scan import Scan
from app.scanner.engine import ScannerEngine
from app.scanner.parser import FileParser
from app.scanner.scorer import RiskScorer
from app.schemas.scan import FindingResponse, ScanQueuedResponse, ScanResponse

router = APIRouter()

_SUPPORTED = {".tf", ".json", ".yaml", ".yml"}


@router.post("/scan", status_code=202, response_model=ScanQueuedResponse)
async def upload_scan(
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
) -> ScanQueuedResponse:
    import os

    ext = os.path.splitext((file.filename or "").lower())[1]
    if ext not in _SUPPORTED:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {ext or '(none)'}")

    content = await file.read()
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(status_code=413, detail="File exceeds 20 MB limit")

    scan_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    scan = Scan(
        id=scan_id,
        filename=file.filename or "unknown",
        status="scanning",
        risk_score=None,
        summary=None,
        file_size=len(content),
        scanned_at=now,
    )
    session.add(scan)
    await session.flush()

    resources, _parse_error = FileParser.parse(content, file.filename or "unknown")
    findings = ScannerEngine().scan(resources)
    score = RiskScorer.score(findings)

    scan.status = "complete"
    scan.risk_score = score

    for f in findings:
        session.add(FindingORM(
            id=str(uuid.uuid4()),
            scan_id=scan_id,
            rule_id=f.rule_id,
            severity=f.severity,
            title=f.title,
            description=f.description,
            remediation=f.remediation,
            resource_name=f.resource_name,
            resource_type=f.resource_type,
        ))

    await session.commit()
    return ScanQueuedResponse(scan_id=scan_id, status=scan.status)


@router.get("/scan/{scan_id}", response_model=ScanResponse)
async def get_scan(
    scan_id: str,
    session: AsyncSession = Depends(get_session),
) -> ScanResponse:
    result = await session.get(Scan, scan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    findings_q = await session.execute(
        select(FindingORM).where(FindingORM.scan_id == scan_id)
    )
    finding_rows = findings_q.scalars().all()

    findings = [
        FindingResponse(
            rule_id=row.rule_id,
            severity=row.severity,  # type: ignore[arg-type]
            title=row.title,
            description=row.description,
            remediation=row.remediation,
            resource_name=row.resource_name,
            resource_type=row.resource_type,
        )
        for row in finding_rows
    ]

    return ScanResponse(
        scan_id=result.id,
        filename=result.filename,
        status=result.status,
        risk_score=result.risk_score,
        findings=findings,
        summary=result.summary,
        scanned_at=result.scanned_at,
    )
