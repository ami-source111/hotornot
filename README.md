# RateApp

Telegram-бот для анонимной оценки фото + веб-панель модерации.

## Стек

- **Bot**: Python 3.12, aiogram 3.x (polling), SQLAlchemy 2.0 async
- **Web**: FastAPI, Jinja2, сессионная cookie-авторизация
- **DB**: PostgreSQL 16, asyncpg, Alembic (async migrations)
- **Infra**: Docker Compose (multi-stage: `web` + `bot` targets)

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
| `POSTGRES_PASSWORD` | Пароль PostgreSQL (замени `changeme`) |
| `WEB_ADMIN_USER` | Логин модератора (по умолчанию `admin`) |
| `WEB_ADMIN_PASSWORD` | Пароль модератора (замени `changeme`) |
| `SECRET_KEY` | Секрет для подписи cookie (минимум 32 символа) |

### 2. Запуск

```bash
docker compose up --build
```

### 3. Миграции БД

Необходимо выполнить **при первом запуске** и после каждого обновления:

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

# Логи web-сервиса
docker compose logs -f web
```

---

## Telegram-бот: команды

| Команда | Описание |
|---|---|
| `/start` | Регистрация: предупреждение 18+, подтверждение возраста, выбор пола |
| `/upload` | Загрузить фото (с опцией разрешить/запретить комментарии) |
| `/browse` | Смотреть ленту (фильтр: Все / Парни / Девушки) |
| `/chats` | Открыть список активных анонимных переписок |

### Реакции на фото

Доступные реакции: ❤️ 🔥 😍 👎 — одна реакция на фото на пользователя.
После реакции кнопки меняются на: Комментировать / Следующее / Профиль автора / Пожаловаться / Заблокировать.

### Анонимный диалог

1. Автор фото получает уведомление о комментарии и может нажать «Ответить».
2. Ответ доставляется комментатору анонимно.
3. Комментатор может ответить — цепочка проксируется через бота бесконечно.
4. Любой участник может закрыть диалог.

---

## Веб-панель модерации

URL: `http://localhost:8000`

| Маршрут | Описание |
|---|---|
| `GET /login` | Форма входа |
| `POST /login` | Аутентификация |
| `GET /logout` | Выход |
| `GET /` | Дашборд (кол-во ожидающих жалоб) |
| `GET /reports` | Очередь жалоб |
| `GET /reports/{id}` | Карточка жалобы + содержимое объекта |
| `POST /reports/{id}/action` | Действие: `hide` / `delete` / `ban` / `reject` |
| `GET /users` | Список пользователей |
| `GET /users/{id}` | Профиль пользователя + его фото |
| `POST /users/{id}/ban` | Заблокировать пользователя |
| `POST /users/{id}/unban` | Разблокировать |
| `POST /users/{id}/delete` | Удалить аккаунт и все данные (CASCADE) |
| `GET /users/create-fake` | Форма создания тестового пользователя |
| `POST /users/create-fake` | Создать тестового пользователя (ID: 9B–10B) |
| `GET /photos` | Список всех фото |
| `GET /photos/upload` | Загрузить фото от имени пользователя |
| `POST /photos/{id}/hide` | Скрыть фото |
| `POST /photos/{id}/delete` | Удалить фото |
| `GET /comments` | Список комментариев |
| `POST /comments/{id}/hide` | Скрыть комментарий |
| `GET /photo-proxy/{id}` | Прокси: отдать байты фото (локальный файл или Telegram CDN) |
| `GET /audit` | Audit log всех действий модераторов |

### Действия модератора

| Действие | Что делает |
|---|---|
| `hide` | Статус объекта → `hidden` (скрыт от пользователей, не удалён из БД) |
| `delete` | Статус объекта → `deleted` |
| `ban` | Автор объекта → `is_blocked=true` |
| `reject` | Жалоба отклонена, объект не тронут |

---

## Структура проекта

```
src/
  core/
    models.py           # SQLAlchemy модели (User, Photo, Rating, Comment,
    |                   #   Message, Report, Block, AuditLog, ContentStatus)
    config.py           # Pydantic Settings из .env (database_url вычисляется
    |                   #   автоматически из отдельных POSTGRES_* переменных)
    database.py         # async_session_factory, engine
    services/
      user.py           # get_or_create_user, set_gender, etc.
      photo.py          # upload_photo, get_next_photo (фильтры + блокировки)
      rating.py         # set_reaction (одна реакция на фото)
      comment.py        # add_comment, get_active_comments
      dialog.py         # get_or_create_dialog, add_message, close_dialog
      report.py         # create_report
      block.py          # block_user, is_blocked
      moderation.py     # get_pending_reports, apply_moderation_action,
                        #   create_fake_user, audit log и прочее для веб-панели

  bot/
    main.py             # Точка входа polling, регистрация роутеров
    keyboards.py        # Все inline-клавиатуры (единственный источник)
    handlers/
      start.py          # /start: предупреждение 18+, регистрация, выбор пола
      upload.py         # /upload: FSM загрузки фото с валидацией Pillow
      browse.py         # /browse: лента, реакции, профиль автора
      comments.py       # просмотр/добавление комментариев, начало диалога
      dialog.py         # /chats, открытие и ответы в анонимном диалоге
      nav.py            # nav:feed / nav:menu — глобальная навигация
      report.py         # жалобы на photo / comment / message
      block.py          # блокировка автора

  web/
    main.py             # FastAPI app, SessionMiddleware, роутеры
    auth.py             # Cookie-авторизация (itsdangerous, SameSite=Strict)
    routers/
      auth.py           # GET/POST /login, GET /logout
      moderation.py     # Все маршруты панели модерации
    templates/
      base.html         # Базовый layout
      login.html
      index.html        # Дашборд
      reports.html      # Очередь жалоб
      report_card.html  # Карточка жалобы + действия
      audit.html        # Audit log
      users.html        # Список пользователей
      user_profile.html
      create_fake_user.html
      photos.html
      upload_photo.html
      comments.html

alembic/
  versions/
    0001_initial.py     # Полная первоначальная миграция (все таблицы)
    0002_reactions_dialogs_displayname.py
    0003_photo_file_path.py
    0004_comment_media.py
    0005_refactor.py    # BIGINT для audit_logs.target_id; относительные пути фото
  env.py                # Async Alembic env (asyncpg)
```

---

## Запуск миграций вручную

```bash
# Применить все миграции до последней
docker compose exec web alembic upgrade head

# Откатить последнюю миграцию
docker compose exec web alembic downgrade -1

# Показать текущую версию
docker compose exec web alembic current

# История миграций
docker compose exec web alembic history --verbose
```

---

## Заметки по архитектуре

**Хранение медиа.** Фото хранятся в `/app/media/` (Docker volume, общий для `web` и `bot`).
В `photos.file_path` записывается только имя файла (например, `abc123.jpg`), а не полный путь.
Полный путь собирается через `settings.media_dir / filename` во время выполнения.

**Статусы контента.** Единый enum `ContentStatus` (active / hidden / deleted) используется для
фото, комментариев и сообщений — каждая таблица имеет собственный PostgreSQL-тип enum,
но все они отображаются на один класс Python.

**FSM в боте.** Используется `MemoryStorage` (по умолчанию). При рестарте бота все незавершённые
сессии сбрасываются. Для продакшена рекомендуется заменить на `RedisStorage`.

**Фейковые пользователи.** ID тестовых пользователей должны быть в диапазоне 9 000 000 000 –
9 999 999 999 (зарезервированный диапазон, не пересекается с реальными Telegram ID).

---

## Деплой на Hetzner

1. Создать VPS (CX21, Ubuntu 22.04)
2. Установить Docker + Docker Compose Plugin
3. Склонировать репозиторий
4. Создать `.env` на сервере (без коммита в git)
5. `docker compose up -d --build`
6. `docker compose exec web alembic upgrade head`
7. При необходимости — Nginx reverse proxy для HTTPS

---

## Фазы разработки

- [x] **Phase 0** — Скелет проекта (структура, Docker, .env.example)
- [x] **Phase 1** — БД + Alembic миграции (8 таблиц)
- [x] **Phase 2** — Бот: /start, /upload, /browse, реакции
- [x] **Phase 3** — Бот: комментарии, анонимный диалог, жалобы, блокировка
- [x] **Phase 4** — Веб-модерация: login, очередь, карточка, hide/delete/ban/reject, audit log
- [x] **Phase 5** — Предупреждение 18+ + рефакторинг (ContentStatus, BIGINT, httpx, Pillow, keyboards.py)
- [ ] **Phase 6** — Деплой Hetzner
