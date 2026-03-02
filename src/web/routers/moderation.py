"""Moderation panel routes."""
from __future__ import annotations

import io
import uuid
from pathlib import Path

import httpx
from PIL import Image

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from src.core.config import settings
from src.core.database import async_session_factory
from src.core.models import Photo
from src.core.services.moderation import (
    apply_moderation_action,
    ban_user,
    create_fake_user,
    delete_photo,
    generate_fake_user_id,
    get_all_comments,
    get_all_photos,
    get_all_users,
    get_audit_log,
    get_pending_reports,
    get_report,
    get_report_target_preview,
    get_user_by_id,
    get_user_photos,
    hard_delete_user,
    hide_comment,
    hide_photo,
    unban_user,
    upload_photo_for_user,
)
from src.web.auth import require_moderator
from sqlalchemy import select

router = APIRouter()
templates = Jinja2Templates(directory="src/web/templates")

VALID_ACTIONS = {"hide", "delete", "ban", "reject"}

# Fake user IDs must fall within this range (outside real Telegram ID space).
FAKE_USER_ID_MIN = 9_000_000_000
FAKE_USER_ID_MAX = 9_999_999_999


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


@router.get("/users", response_class=HTMLResponse)
async def users_list(request: Request, moderator: str = Depends(require_moderator)) -> HTMLResponse:
    async with async_session_factory() as session:
        users = await get_all_users(session, limit=200)
    return templates.TemplateResponse(
        "users.html",
        {"request": request, "moderator": moderator, "users": users, "flash": None},
    )


@router.get("/users/create-fake", response_class=HTMLResponse)
async def create_fake_user_form(
    request: Request,
    moderator: str = Depends(require_moderator),
) -> HTMLResponse:
    suggested_id = generate_fake_user_id()
    return templates.TemplateResponse(
        "create_fake_user.html",
        {
            "request": request,
            "moderator": moderator,
            "suggested_id": suggested_id,
            "flash": None,
        },
    )


@router.post("/users/create-fake")
async def create_fake_user_submit(
    request: Request,
    user_id: int = Form(...),
    display_name: str = Form(...),
    first_name: str = Form(default=""),
    gender: str = Form(default="M"),
    moderator: str = Depends(require_moderator),
) -> RedirectResponse:
    # Ensure the ID is in the reserved fake-user range to prevent collisions
    # with real Telegram user IDs (which are below ~8 billion as of 2025).
    if not (FAKE_USER_ID_MIN <= user_id <= FAKE_USER_ID_MAX):
        return RedirectResponse(
            f"/users/create-fake?error=id_out_of_range", status_code=302
        )

    async with async_session_factory() as session:
        user = await create_fake_user(
            session,
            user_id=user_id,
            display_name=display_name,
            first_name=first_name or display_name,
            gender=gender,
            moderator=moderator,
        )
    return RedirectResponse(f"/users/{user.id}", status_code=302)


@router.post("/users/{user_id}/ban")
async def user_ban(user_id: int, moderator: str = Depends(require_moderator)) -> RedirectResponse:
    async with async_session_factory() as session:
        await ban_user(session, user_id, moderator)
    return RedirectResponse(f"/users/{user_id}", status_code=302)


@router.post("/users/{user_id}/unban")
async def user_unban(user_id: int, moderator: str = Depends(require_moderator)) -> RedirectResponse:
    async with async_session_factory() as session:
        await unban_user(session, user_id, moderator)
    return RedirectResponse(f"/users/{user_id}", status_code=302)


@router.post("/users/{user_id}/delete")
async def user_delete(user_id: int, moderator: str = Depends(require_moderator)) -> RedirectResponse:
    async with async_session_factory() as session:
        await hard_delete_user(session, user_id, moderator)
    return RedirectResponse("/users", status_code=302)


@router.get("/users/{user_id}", response_class=HTMLResponse)
async def user_profile(
    user_id: int,
    request: Request,
    moderator: str = Depends(require_moderator),
) -> HTMLResponse:
    async with async_session_factory() as session:
        user = await get_user_by_id(session, user_id)
        if user is None:
            return HTMLResponse("Пользователь не найден", status_code=404)
        photos = await get_user_photos(session, user_id)
    return templates.TemplateResponse(
        "user_profile.html",
        {
            "request": request,
            "moderator": moderator,
            "user": user,
            "photos": photos,
            "flash": None,
        },
    )


@router.get("/comments", response_class=HTMLResponse)
async def comments_list(request: Request, moderator: str = Depends(require_moderator)) -> HTMLResponse:
    async with async_session_factory() as session:
        comments = await get_all_comments(session, limit=200)
    return templates.TemplateResponse(
        "comments.html",
        {"request": request, "moderator": moderator, "comments": comments, "flash": None},
    )


@router.post("/comments/{comment_id}/hide")
async def comment_hide(comment_id: int, moderator: str = Depends(require_moderator)) -> RedirectResponse:
    async with async_session_factory() as session:
        await hide_comment(session, comment_id, moderator)
    return RedirectResponse("/comments", status_code=302)


# ---------------------------------------------------------------------------
# Photos
# ---------------------------------------------------------------------------

@router.get("/photos/upload", response_class=HTMLResponse)
async def photo_upload_form(
    request: Request,
    user_id: int | None = None,
    moderator: str = Depends(require_moderator),
) -> HTMLResponse:
    async with async_session_factory() as session:
        users = await get_all_users(session, limit=500)
    return templates.TemplateResponse(
        "upload_photo.html",
        {
            "request": request,
            "moderator": moderator,
            "users": users,
            "preselected_user_id": user_id,
            "flash": None,
        },
    )


@router.post("/photos/upload")
async def photo_upload_submit(
    request: Request,
    user_id: int = Form(...),
    allow_comments: str = Form(default="false"),
    file: UploadFile = File(...),
    moderator: str = Depends(require_moderator),
) -> RedirectResponse:
    allow_comments_bool = allow_comments.lower() in ("true", "on", "1", "yes")
    ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        ext = ".jpg"

    contents = await file.read()

    # Validate that the upload is a real image using Pillow.
    try:
        Image.open(io.BytesIO(contents)).verify()
    except Exception:
        return RedirectResponse("/photos/upload?error=invalid_image", status_code=302)

    filename = f"{uuid.uuid4().hex}{ext}"
    dest = settings.media_dir / filename
    dest.write_bytes(contents)

    async with async_session_factory() as session:
        await upload_photo_for_user(
            session,
            author_id=user_id,
            file_path=filename,          # store relative filename only
            allow_comments=allow_comments_bool,
            moderator=moderator,
        )

    return RedirectResponse("/photos", status_code=302)


@router.get("/photos", response_class=HTMLResponse)
async def photos_list(request: Request, moderator: str = Depends(require_moderator)) -> HTMLResponse:
    async with async_session_factory() as session:
        photos = await get_all_photos(session, limit=100)
    return templates.TemplateResponse(
        "photos.html",
        {"request": request, "moderator": moderator, "photos": photos, "flash": None},
    )


@router.post("/photos/{photo_id}/hide")
async def photo_hide(photo_id: int, moderator: str = Depends(require_moderator)) -> RedirectResponse:
    async with async_session_factory() as session:
        await hide_photo(session, photo_id, moderator)
    return RedirectResponse("/photos", status_code=302)


@router.post("/photos/{photo_id}/delete")
async def photo_delete(photo_id: int, moderator: str = Depends(require_moderator)) -> RedirectResponse:
    async with async_session_factory() as session:
        await delete_photo(session, photo_id, moderator)
    return RedirectResponse("/photos", status_code=302)


# ---------------------------------------------------------------------------
# Photo proxy (local file or Telegram CDN)
# ---------------------------------------------------------------------------

@router.get("/photo-proxy/{photo_id}")
async def photo_proxy(
    photo_id: int,
    moderator: str = Depends(require_moderator),
) -> StreamingResponse:
    async with async_session_factory() as session:
        result = await session.execute(select(Photo).where(Photo.id == photo_id))
        photo = result.scalar_one_or_none()

    if photo is None:
        return StreamingResponse(iter([b""]), status_code=404, media_type="image/jpeg")

    # Local file takes priority; file_path stores only the filename.
    if photo.file_path:
        local_path = settings.media_dir / photo.file_path
        if local_path.exists():
            img_bytes = local_path.read_bytes()
            suffix = photo.file_path.lower()
            if suffix.endswith(".png"):
                media_type = "image/png"
            elif suffix.endswith(".webp"):
                media_type = "image/webp"
            else:
                media_type = "image/jpeg"
            return StreamingResponse(iter([img_bytes]), media_type=media_type)

    # Fall back to Telegram CDN using async HTTP (non-blocking).
    if photo.telegram_file_id:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                tg_resp = await client.get(
                    f"https://api.telegram.org/bot{settings.bot_token}/getFile",
                    params={"file_id": photo.telegram_file_id},
                )
                tg_data = tg_resp.json()
                tg_path = tg_data["result"]["file_path"]
                img_resp = await client.get(
                    f"https://api.telegram.org/file/bot{settings.bot_token}/{tg_path}"
                )
                img_bytes = img_resp.content
            return StreamingResponse(iter([img_bytes]), media_type="image/jpeg")
        except Exception:
            pass

    placeholder = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
        b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1b\xc0"
        b"\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00"
        b"\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01"
        b"\x01\x00\x00?\x00\xf5\x0f\xff\xd9"
    )
    return StreamingResponse(iter([placeholder]), media_type="image/jpeg")


@router.get("/audit", response_class=HTMLResponse)
async def audit_log(request: Request, moderator: str = Depends(require_moderator)) -> HTMLResponse:
    async with async_session_factory() as session:
        logs = await get_audit_log(session, limit=200)
    return templates.TemplateResponse(
        "audit.html",
        {"request": request, "moderator": moderator, "logs": logs, "flash": None},
    )
