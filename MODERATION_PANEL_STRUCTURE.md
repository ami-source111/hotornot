# FastAPI + Jinja2 Web Moderation Panel

## Project Structure Created

```
/sessions/wizardly-jolly-ptolemy/mnt/outputs/
├── src/
│   ├── core/
│   │   └── services/
│   │       └── moderation.py          (Moderation service layer)
│   └── web/
│       ├── auth.py                    (Session authentication)
│       ├── main.py                    (FastAPI application)
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── auth.py                (Login/logout routes)
│       │   └── moderation.py          (Moderation panel routes)
│       └── templates/
│           ├── base.html              (Base layout)
│           ├── login.html             (Login page)
│           ├── index.html             (Dashboard)
│           ├── reports.html           (Reports queue)
│           ├── report_card.html       (Individual report detail)
│           └── audit.html             (Audit log)
```

## File Descriptions

### Python Files (All syntax validated)

#### 1. src/core/services/moderation.py
Core moderation service with database operations:
- `get_pending_reports()` - Fetch pending reports
- `get_report()` - Get single report by ID
- `get_report_target_preview()` - Get target content preview
- `apply_moderation_action()` - Execute moderation actions (hide, delete, ban, reject)
- `get_audit_log()` - Fetch audit log entries

#### 2. src/web/auth.py
Session-based authentication for moderation panel:
- `create_session_token()` - Create signed session token
- `decode_session_token()` - Verify and decode token
- `get_current_moderator()` - Get current user from request
- `require_moderator()` - Dependency for protected routes
- `verify_credentials()` - Validate username/password

#### 3. src/web/main.py
FastAPI application entry point:
- SessionMiddleware for cookie-based authentication
- Includes auth and moderation routers
- Health check endpoint

#### 4. src/web/routers/__init__.py
Router module initialization

#### 5. src/web/routers/auth.py
Authentication routes:
- GET `/login` - Login page
- POST `/login` - Login submission
- GET `/logout` - Logout and cookie cleanup

#### 6. src/web/routers/moderation.py
Moderation panel routes:
- GET `/` - Dashboard with pending count
- GET `/reports` - Reports queue list
- GET `/reports/{report_id}` - Individual report detail
- POST `/reports/{report_id}/action` - Apply moderation action
- GET `/audit` - Audit log viewer

### Template Files (Jinja2)

#### 1. base.html
Base template with:
- Navigation bar with links
- Current moderator display
- Flash messages support
- Responsive styling (flexbox/CSS Grid)
- Color-coded badges (pending, resolved, rejected, etc.)
- Button styles (primary, danger, warning, secondary)

#### 2. login.html
Login form template:
- Simple card layout
- Username and password inputs
- Error message display
- Centered design

#### 3. index.html
Dashboard template:
- Pending reports count card
- Link to reports queue
- Grid layout for metrics

#### 4. reports.html
Reports queue template:
- Table listing all pending reports
- Report ID, type, target ID, status, date
- Review button for each report
- Empty state message

#### 5. report_card.html
Individual report detail template:
- Two-column layout (report info + target content)
- Report metadata table
- Target object information
- Content preview
- Moderation action buttons (hide, delete, ban, reject)
- Back to queue link

#### 6. audit.html
Audit log template:
- Table with all moderation actions
- Moderator name, action type, target, note, timestamp
- Badge-based action styling

## Features

- Session-based authentication with secure cookies
- SQL-based moderation database operations
- Async/await for database operations
- Type hints throughout
- Jinja2 template inheritance
- Responsive CSS styling
- Badge system for status indicators
- Audit logging of all actions
- Support for photo, comment, and message moderation

## Configuration Required

The following must be available in `src.core.config.settings`:
- `secret_key` - For session token signing
- `web_admin_user` - Admin username
- `web_admin_password` - Admin password

The following must be available in `src.core.database`:
- `async_session_factory` - SQLAlchemy async session factory

The following models must exist in `src.core.models`:
- Report, ReportStatus
- Photo, PhotoStatus
- Comment, CommentStatus
- Message, MessageStatus
- User
- AuditLog
- Block

## Running the Application

```bash
uvicorn src.web.main:app --reload
```

Access at: http://localhost:8000/login
