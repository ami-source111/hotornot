FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Web stage
FROM base AS web
CMD ["uvicorn", "src.web.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Bot stage
FROM base AS bot
CMD ["python", "-m", "src.bot.main"]
