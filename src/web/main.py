from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from src.core.config import settings
from src.web.routers import auth as auth_router
from src.web.routers import moderation as mod_router

app = FastAPI(title="RateApp Moderation", version="0.1.0")

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="mod_starlette_session",
    max_age=60 * 60 * 8,
    https_only=False,
)

app.include_router(auth_router.router)
app.include_router(mod_router.router)


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
