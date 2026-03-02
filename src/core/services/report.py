"""Report (complaint) service."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import Report, ReportTarget


async def create_report(
    session: AsyncSession,
    reporter_id: int,
    target_type: ReportTarget,
    target_id: int,
    reason: str | None = None,
) -> Report:
    report = Report(
        reporter_id=reporter_id,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report
