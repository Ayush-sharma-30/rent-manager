FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src
RUN pip install --upgrade pip && pip install -e .

COPY alembic.ini ./
COPY migrations ./migrations
COPY scripts ./scripts
COPY start.sh ./
RUN chmod +x start.sh

ENV PYTHONPATH=/app/src

EXPOSE 8000

# Migrate + seed + launch the API on $PORT. (docker-compose and the Celery
# worker/beat override this with their own `command`.)
CMD ["/app/start.sh"]
