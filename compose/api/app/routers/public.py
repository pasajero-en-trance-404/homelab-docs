from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Request

from util import HOSTNAME

public_router = APIRouter()

SENSITIVE_HEADERS = {
    "authorization",
    "proxy-authorization",
    "x-api-key",
    "cookie",
    "set-cookie",
}


@public_router.get("/")
def root():
    return {
        "name": "Homelab API",
        "version": "1.0.0",
        "description": "API pública del homelab",
        "endpoints": {
            "root": "/",
            "health": "/api/health",
            "time": "/api/time",
            "ip": "/api/ip",
            "request": "/api/request",
            "server": "/api/server",
            "uuid": "/api/uuid",
            "docs": "/docs",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@public_router.get("/api/health")
def health():
    return {
        "status": "ok",
        "server": HOSTNAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@public_router.get("/api/time")
def time():
    now = datetime.now(timezone.utc)
    return {
        "time_utc": now.isoformat(),
        "unix_seconds": int(now.timestamp()),
        "timezone": "UTC",
        "server": HOSTNAME,
    }


@public_router.get("/api/ip")
def client_ip(request: Request):
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return {"ip": xff.split(",")[0].strip(), "source": "x-forwarded-for"}
    return {"ip": request.client.host, "source": "direct"}


@public_router.get("/api/request")
def request_info(request: Request):
    headers = {
        k: v for k, v in request.headers.items() if k.lower() not in SENSITIVE_HEADERS
    }
    return {
        "method": request.method,
        "path": request.url.path,
        "query": dict(request.query_params),
        "user_agent": request.headers.get("user-agent"),
        "referer": request.headers.get("referer"),
        "headers": headers,
    }


@public_router.get("/api/server")
def server():
    try:
        with open("/proc/uptime") as f:
            uptime_seconds = int(float(f.read().split()[0]))
    except Exception:
        uptime_seconds = None
    return {
        "hostname": HOSTNAME,
        "uptime_seconds": uptime_seconds,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@public_router.get("/api/uuid")
def gen_uuid():
    return {
        "uuid": str(uuid.uuid4()),
        "version": 4,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
