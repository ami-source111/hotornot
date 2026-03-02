"""Auth routes: login, logout."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.web.auth import (
    SESSION_COOKIE,
    create_session_token,
    get_current_moderator,
    verify_credentials,
)

router = APIRouter()
templates = Jinja2Templates(directory="src/web/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    if get_current_moderator(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": None, "flash": None, "moderator": None}
    )


@router.post("/login")
async def login_submit(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
) -> Response:
    if not verify_credentials(username, password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверный логин или пароль", "flash": None, "moderator": None},
            status_code=401,
        )
    token = create_session_token(username)
    redirect = RedirectResponse("/", status_code=302)
    redirect.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="strict",
        max_age=60 * 60 * 8,
    )
    return redirect


@router.get("/logout")
async def logout() -> Response:
    redirect = RedirectResponse("/login", status_code=302)
    redirect.delete_cookie(SESSION_COOKIE)
    return redirect
