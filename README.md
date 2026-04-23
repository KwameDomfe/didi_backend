# The Restaurant Backend (Django REST API)

Backend API for restaurant discovery, ordering, account management, and social dining/community features.

## Current Status

- Runtime: Python 3.11 (see `runtime.txt`)
- Framework: Django 5.x + Django REST Framework
- Auth: Djoser JWT + DRF token + session auth
- Docs: drf-spectacular (`/api/schema/`, `/api/docs/`, `/api/redoc/`)
- DB: SQLite by default, PostgreSQL when configured
- Real-time: SSE notifications endpoint in `social` app; Channels/Redis settings are present

## Project Apps

- `apps.accounts`: custom user model, user types, profile APIs, registration/login, email verification, password reset request
- `apps.restaurants`: restaurants, cuisines, menu categories/items, option groups/choices, reviews, item likes/comments/shares
- `apps.orders`: cart management, checkout, orders, order tracking
- `apps.social`: posts, comments, likes, follow/connect flows, groups, notifications, notification stream

## API Overview

Base URL in local development: `http://127.0.0.1:8000`

### Core

- `GET /` API root payload
- `GET /admin/` Django admin

### Router Endpoints under `/api/`

- `/api/restaurants/`
- `/api/menu-items/`
- `/api/categories/`
- `/api/reviews/`
- `/api/option-groups/`
- `/api/option-choices/`
- `/api/cuisines/`

### Auth and Accounts

- Djoser base: `/api/auth/`
- JWT create: `/api/auth/jwt/create/`
- JWT refresh: `/api/auth/jwt/refresh/`
- JWT verify: `/api/auth/jwt/verify/`
- Accounts module: `/api/accounts/`
	- Custom auth endpoints include:
		- `/api/accounts/login/`
		- `/api/accounts/register/`
		- `/api/accounts/auth/logout/`
		- `/api/accounts/auth/verify-email/`
		- `/api/accounts/auth/resend-verification/`
		- `/api/accounts/auth/request-password-reset/`

### Orders

- Module base: `/api/orders/`
- Viewsets:
	- `/api/orders/orders/`
	- `/api/orders/cart/`
- Custom actions include:
	- `POST /api/orders/orders/checkout/`
	- `GET /api/orders/orders/{id}/tracking/`
	- `POST /api/orders/orders/{id}/cancel/`
	- `GET /api/orders/cart/current/`
	- `POST /api/orders/cart/add_item/`
	- `PUT /api/orders/cart/update_item/`
	- `DELETE /api/orders/cart/remove_item/?item_id=...`
	- `DELETE /api/orders/cart/clear/`

### Social

- Module base: `/api/social/`
- Viewsets:
	- `/api/social/posts/`
	- `/api/social/groups/`
	- `/api/social/follow/`
	- `/api/social/notifications/`
- Stream endpoint:
	- `GET /api/social/notifications/stream/?token=<drf_token>`

### OpenAPI

- `/api/schema/`
- `/api/docs/`
- `/api/redoc/`

## Local Development Setup (Windows)

1. Create and activate virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies.

This repository currently does not include a pinned `requirements.txt`, so install the packages used by the current settings and apps:

```powershell
pip install django djangorestframework djoser djangorestframework-simplejwt drf-spectacular drf-spectacular-sidecar django-cors-headers django-filter channels channels-redis whitenoise gunicorn psycopg2-binary django-json-widget Pillow python-decouple
```

3. Create `.env` in project root:

```env
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=replace-with-a-secret

# Optional comma-separated list
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

# PostgreSQL (optional for local dev)
USE_POSTGRES=False
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_HOST=
POSTGRES_PORT=

# Frontend and email
FRONTEND_URL=http://localhost:5173
DEFAULT_FROM_EMAIL=The Restaurant <noreply@example.com>
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=

# Redis for channel layer
REDIS_URL=redis://127.0.0.1:6379

# Production-oriented CORS settings
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

4. Apply migrations and create superuser:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

5. Start server:

```powershell
python manage.py runserver
```

## Environment and Behavior Notes

- `AUTH_USER_MODEL` is `accounts.CustomUser`.
- REST framework default permission is `IsAuthenticated`.
- Authentication classes include session, DRF token, and JWT.
- Email backend is console in debug; SMTP in non-debug.
- Production security settings (HTTPS redirect, secure cookies, HSTS) are enabled when `DJANGO_DEBUG=False` and not running `runserver`.

## Database Selection Rules

- Uses SQLite (`db.sqlite3`) unless PostgreSQL env variables are fully provided.
- PostgreSQL is activated when all `POSTGRES_*` values are set and either:
	- `USE_POSTGRES=True`, or
	- `DJANGO_DEBUG=False`

## Static and Media

- Static URL: `/static/`
- Static root: `staticfiles/`
- Media URL: `/media/`
- Media root: `media/`
- WhiteNoise is configured for static file serving.

## Useful Commands

```powershell
python manage.py check
python manage.py test
python manage.py collectstatic --noinput
```

Custom management commands in this codebase:

- `python manage.py list_users`
- `python manage.py migrate_users --dry-run`
- `python manage.py audit_slugs`

## Deployment Notes

- Procfile command: `gunicorn core.wsgi --log-file -`
- Set `DJANGO_DEBUG=False` in production.
- Configure secure values for secret key, hosts, CORS/CSRF origins, email, Redis, and database settings.