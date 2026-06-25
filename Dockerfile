# syntax=docker/dockerfile:1
FROM python:3.13-slim

# - PYTHONUNBUFFERED: stream logs straight to stdout (CloudWatch)
# - PYTHONDONTWRITEBYTECODE: no .pyc clutter
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect static assets for WhiteNoise. A dummy SECRET_KEY is fine here — this
# only runs the staticfiles pipeline, no secrets are baked into the image.
RUN DJANGO_SECRET_KEY=build-only DJANGO_DEBUG=False \
    python manage.py collectstatic --noinput

EXPOSE 8000

# Gunicorn binds to the port the ALB target group health-checks.
CMD ["gunicorn", "acopio.wsgi", "--bind", "0.0.0.0:8000", "--log-file", "-", "--workers", "2"]
