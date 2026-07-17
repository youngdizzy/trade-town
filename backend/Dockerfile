# Build context: ./backend
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY app ./app

# Run as an unprivileged user rather than root inside the container.
RUN groupadd --system app && useradd --system --gid app --home /app app \
    && mkdir -p /app/data \
    && chown -R app:app /app
USER app

VOLUME ["/app/data"]

EXPOSE 8000

# HOST/PORT are read from the environment (see docker-compose.yml) so they
# stay meaningful — changing PORT here also requires updating the `expose`
# port and frontend/deploy/nginx.conf's proxy_pass, since those aren't
# derived from this env var automatically.
ENV HOST=0.0.0.0 \
    PORT=8000
CMD ["sh", "-c", "uvicorn app.main:app --host ${HOST} --port ${PORT}"]
