FROM cloudflare/cloudflared:latest AS cloudflared

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home app

COPY --from=cloudflared /usr/local/bin/cloudflared /usr/local/bin/cloudflared
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt \
    && python -c "import fastapi, sqlalchemy, alembic, jinja2, multipart, argon2, telegram, itsdangerous, cryptography; from starlette.middleware.sessions import SessionMiddleware" \
    && cloudflared --version

COPY . .
RUN python -c "import app.main, app.bot, app.integrations" \
    && chmod +x /srv/app/scripts/entrypoint.sh /srv/app/scripts/backup.sh /srv/app/scripts/smoke-test.sh /usr/local/bin/cloudflared \
    && mkdir -p /data \
    && chown -R app:app /srv/app /data

EXPOSE 8000
ENTRYPOINT ["/srv/app/scripts/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
