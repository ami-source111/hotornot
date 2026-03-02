"""Moderation panel routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.core.database import async_session_factory
from src.core.services.moderation import (
    apply_moderation_action,
    get_audit_log,
    get_pending_reports,
    get_report,
    get_report_target_preview,
)
from src.web.auth import require_moderator

router = APIRouter()
templates = Jinja2Templates(directory="src/web/templates")

VALID_ACTIONS = {"hide", "delete", "ban", "reject"}


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, moderator: str = Depends(require_moderator)) -> HTMLResponse:
    async with async_session_factory() as session:
        reports = await get_pending_reports(session, limit=100)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "moderator": moderator, "pending_count": len(reports), "flash": None},
    )


@router.get("/reports", response_class=HTMLResponse)
async def reports_list(request: Request, moderator: str = Depends(require_moderator)) -> HTMLResponse:
    async with async_session_factory() as session:
        reports = await get_pending_reports(session, limit=100)
    return templates.TemplateResponse(
        "reports.html",
        {"request": request, "moderator": moderator, "reports": reports, "flash": None},
    )


@router.get("/reports/{report_id}", response_class=HTMLResponse)
async def report_card(
    report_id: int,
    request: Request,
    moderator: str = Depends(require_moderator),
) -> HTMLResponse:
    async with async_session_factory() as session:
        report = await get_report(session, report_id)
        if report is None:
            return HTMLResponse("Жалоба не найдена", status_code=404)
        target = await get_report_target_preview(session, report)

    return templates.TemplateResponse(
        "report_card.html",
        {"request": request, "moderator": moderator, "report": report, "target": target, "flash": None},
    )


@router.post("/reports/{report_id}/action")
async def report_action(
    report_id: int,
    request: Request,
    action: str = Form(...),
    note: str = Form(default=""),
    moderator: str = Depends(require_moderator),
) -> RedirectResponse:
    if action not in VALID_ACTIONS:
        return RedirectResponse(f"/reports/{report_id}", status_code=302)

    async with async_session_factory() as session:
        await apply_moderation_action(
            session,
            report_id=report_id,
            action=action,
            moderator=moderator,
            note=note or None,
        )

    return RedirectResponse("/reports", status_code=302)


@router.get("/audit", response_class=HTMLResponse)
async def audit_log(request: Request, moderator: str = Depends(require_moderator)) -> HTMLResponse:
    async with async_session_factory() as session:
        logs = await get_audit_log(session, limit=200)
    return templates.TemplateResponse(
        "audit.html",
        {"request": request, "moderator": moderator, "logs": logs, "flash": None},
    )
