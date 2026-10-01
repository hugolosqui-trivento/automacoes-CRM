FROM ghcr.io/astral-sh/uv:0.11.17 AS uv

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_NO_CACHE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=uv /uv /uvx /bin/

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home --home-dir /app app \
    && chown app:app /app

USER app

# Install locked production dependencies in a cache-friendly layer.
COPY --chown=app:app pyproject.toml uv.lock README.md ./
COPY --chown=app:app src ./src
RUN uv sync --frozen --no-dev

COPY --chown=app:app api ./api
COPY --chown=app:app dashboard ./dashboard
COPY --chown=app:app database ./database
COPY --chown=app:app shared ./shared
COPY --chown=app:app app.py ./app.py

EXPOSE 8000 8501

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
