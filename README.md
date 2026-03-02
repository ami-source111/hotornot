# RateApp

Telegram-бот для анонимной оценки фото + веб-панель модерации.

## Стек

- **Bot**: Python 3.12, aiogram 3.x (polling), SQLAlchemy 2.0 async
- **Web**: FastAPI, Jinja2, сессионная cookie-авторизация
- **DB**: PostgreSQL 16
- **Infra**: Docker Compose

---

## Быстрый старт (локально)

### 1. Настройка окружения

```bash
cp .env.example .env
```

Отредактируй `.env`:

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен бота от @BotFather |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL |
| `WEB_ADMIN_USER` | Логин модератора |
| `WEB_ADMIN_PASSWORD` | Пароль модератора |
| `SECRET_KEY` | Секрет для подписи cookie (мин. 32 символа) |

### 2. Запуск

```bash
docker compose up --build
```

### 3. Миграции БД

```bash
docker compose exec web alembic upgrade head
```

### 4. Проверка

```bash
# Health check API
curl http://localhost:8000/health
# → {"status":"ok"}

# Веб-панель модерации
open http://localhost:8000/login

# Логи бота
docker compose logs -f bot

# Логи web
docker compose logs -f web
```

---

## Telegram-бот: команды

| Команда | Описание |
|---|---|
| `/start` | Регистрация, выбор пола |
| `/upload` | Загрузить фото (с выбором: разрешить комментарии или нет) |
| `/browse` | Смотреть ленту (фильтр: Все / Парни / Девушки) |

### Оценки
- Шкала: 1–10
- Одна оценка на фото на пользователя (повтор невозможен)
- После оценки появляются кнопки: Комментарии / Пожаловаться / Заблокировать автора

### Анонимный диалог
- Ответ на комментарий → анонимное сообщение автору
- Получатель может ответить — цепочка проксируется через бота

---

## Веб-панель модерации

URL: `http://localhost:8000`

| Маршрут | Описание |
|---|---|
| `GET /login` | Форма входа |
| `POST /login` | Аутентификация |
| `GET /logout` | Выход |
| `GET /` | Дашборд (кол-во pending жалоб) |
| `GET /reports` | Очередь жалоб |
| `GET /reports/{id}` | Карточка жалобы + объект |
| `POST /reports/{id}/action` | Действие: hide / delete / ban / reject |
| `GET /audit` | Audit log всех действий |

### Действия модератора

| Действие | Что делает |
|---|---|
| `hide` | Статус объекта → `hidden` (скрыт, не удалён) |
| `delete` | Статус объекта → `deleted` |
| `ban` | Автор объекта → `is_blocked=true` |
| `reject` | Жалоба отклонена, объект не тронут |

---

## Структура проекта

```
src/
  core/
    models.py           # SQLAlchemy модели (User, Photo, Rating, Comment, Message, Report, Block, AuditLog)
    config.py           # Pydantic Settings из .env
    database.py         # async_session_factory, engine
    services/
      user.py           # get_or_create_user, set_gender
      photo.py          # upload_photo, get_next_photo (с фильтрами и блокировками)
      rating.py         # create_rating (1 раз на фото)
      comment.py        # add_comment, get_active_comments
      message.py        # create_message (анонимный диалог)
      report.py         # create_report
      block.py          # block_user
      moderation.py     # get_pending_reports, apply_moderation_action, audit log

  bot/
    main.py             # Точка входа, polling, роутеры
    keyboards.py        # Inline-клавиатуры
    handlers/
      start.py          # /start, выбор пола
      upload.py         # /upload, FSM загрузки фото
      browse.py         # /browse, лента, оценки
      comments.py       # просмотр/добавление комментариев, ответ → диалог
      dialog.py         # анонимные ответы в диалоге
      report.py         # жалобы на photo/comment/message
      block.py          # блокировка автора

  web/
    main.py             # FastAPI app, SessionMiddleware, роутеры
    auth.py             # Cookie-авторизация (itsdangerous)
    routers/
      auth.py           # GET/POST /login, GET /logout
      moderation.py     # очередь, карточка, action, audit
    templates/
      base.html         # Базовый layout
      login.html        # Страница входа
      index.html        # Дашборд
      reports.html      # Очередь жалоб
      report_card.html  # Карточка жалобы + действия
      audit.html        # Audit log

  worker/               # (зарезервировано для фоновых задач)

alembic/
  versions/
    0001_initial.py     # Полная первоначальная миграция
  env.py                # Async Alembic env
```

---

## Запуск миграций вручную

```bash
# Применить все миграции
docker compose exec web alembic upgrade head

# Откатить последнюю
docker compose exec web alembic downgrade -1

# Статус
docker compose exec web alembic current
```

---

## Деплой на Hetzner (будет в следующей фазе)

Примерный план:
1. Создать VPS (CX21, Ubuntu 22.04)
2. Установить Docker + Docker Compose
3. Склонировать репозиторий
4. Создать `.env` на сервере (без коммита)
5. `docker compose up -d --build`
6. `docker compose exec web alembic upgrade head`
7. Настроить Nginx (опционально) для HTTPS

---

## Фазы разработки

- [x] **Phase 0** — Скелет проекта (структура, Docker, .env.example)
- [x] **Phase 1** — БД + Alembic миграции (8 таблиц)
- [x] **Phase 2** — Бот: /start, /upload, /browse, оценки 1–10
- [x] **Phase 3** — Бот: комментарии, анонимный диалог, жалобы, блокировка
- [x] **Phase 4** — Веб-модерация: login, очередь, карточка, hide/delete/ban/reject, audit log
- [ ] **Phase 5** — Деплой Hetzner (по запросу)
