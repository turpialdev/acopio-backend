# acopio-backend

Backend API for Acopio, built with [Django](https://www.djangoproject.com/) and [Django REST Framework](https://www.django-rest-framework.org/).

## Requirements

- Python 3.13
- pip / virtualenv

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # On Windows: copy .env.example .env
python manage.py migrate
python manage.py runserver
```

The API is then available at http://127.0.0.1:8000/.

## Project layout

- `acopio/` — project settings, URL config, WSGI/ASGI entrypoints
- `api/` — application code (views, models, URLs, tests)

## Configuration

Settings read from environment variables (loaded from `.env` if present):

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | insecure dev key | Cryptographic signing key |
| `DJANGO_DEBUG` | `True` | Debug mode |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated allowed hosts |
| `DJANGO_CORS_ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated CORS origins (Vue dev server) |

## Endpoints

- `GET /api/health/` — health check → `{"status": "ok", "service": "acopio-backend"}`
- `/admin/` — Django admin

## Running tests

```bash
python manage.py test
```

## Related

- [acopio-frontend](https://github.com/turpialdev/acopio-frontend) — Vue.js client
