FROM python:3.12.16-slim@sha256:1148dbb014615300fa7e713b2f94f550c0d1c69780c0805f84f093ceee34dd0b

RUN pip install --no-cache-dir fastapi==0.162.0 "uvicorn[standard]==0.54.0" \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid 10001 --no-create-home \
        --shell /usr/sbin/nologin app

COPY --chown=10001:10001 app/ /app
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 10001:10001

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
