from datetime import datetime, timezone
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from util import HOSTNAME, SERVICES, docker_containers, verify_key

from power import (
    ApprovalError,
    ShutdownHelperRejected,
    ShutdownHelperUnavailable,
    ShutdownOutcomeUnknown,
    approvals,
    audit_shutdown,
    execute_host_shutdown,
    verify_power_key,
)

private_router = APIRouter(dependencies=[Depends(verify_key)])

SENSITIVE_HEADERS = {
    "authorization",
    "proxy-authorization",
    "x-api-key",
    "x-power-approval-key",
    "cookie",
    "set-cookie",
}

SENSITIVE_QUERY_PARAMS = {
    "api_key",
    "x-api-key",
    "token",
    "password",
    "secret",
    "access_token",
    "approval_token",
    "power_api_key",
}

REDACTED = "<redacted>"
logger = logging.getLogger(__name__)


class ShutdownApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approval_token: str = Field(min_length=40, max_length=128)


@private_router.get("/")
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
            "docs": "/openapi.json",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@private_router.get("/api")
def api_root():
    return {
        "service": "homelab-api",
        "status": "running",
        "version": "1.0.0",
        "private_endpoints": ["/api/status", "/api/containers"],
    }


@private_router.get("/api/status")
def status():
    containers = docker_containers()
    if containers is None:
        services = {svc: "unknown" for svc in SERVICES}
    else:
        running = {
            container["name"]
            for container in containers
            if container.get("state") == "running"
        }
        services = {svc: "up" if svc in running else "down" for svc in SERVICES}
    return {
        "server": HOSTNAME,
        "services": services,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@private_router.get("/api/containers")
def containers():
    return {
        "server": HOSTNAME,
        "containers": docker_containers() or [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@private_router.get("/api/time")
def time():
    now = datetime.now(timezone.utc)
    return {
        "time_utc": now.isoformat(),
        "unix_seconds": int(now.timestamp()),
        "timezone": "UTC",
        "server": HOSTNAME,
    }


@private_router.get("/api/ip")
def client_ip(request: Request):
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return {"ip": xff.split(",")[0].strip(), "source": "x-forwarded-for"}
    return {"ip": request.client.host, "source": "direct"}


@private_router.get("/api/request")
def request_info(request: Request):
    headers = {
        k: v for k, v in request.headers.items() if k.lower() not in SENSITIVE_HEADERS
    }
    query = dict(request.query_params)
    for name in query:
        if name.lower() in SENSITIVE_QUERY_PARAMS:
            query[name] = REDACTED
    return {
        "method": request.method,
        "path": request.url.path,
        "query": query,
        "user_agent": request.headers.get("user-agent"),
        "referer": request.headers.get("referer"),
        "headers": headers,
    }


@private_router.get("/api/server")
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


@private_router.get("/api/uuid")
def gen_uuid():
    return {
        "uuid": str(uuid.uuid4()),
        "version": 4,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@private_router.post(
    "/api/power/shutdown/prepare",
    status_code=201,
    dependencies=[Depends(verify_power_key)],
)
def prepare_host_shutdown():
    """Issue one short-lived approval scoped to host.shutdown only."""
    try:
        token, expires_at = approvals.issue()
    except ApprovalError as error:
        raise HTTPException(status_code=409, detail="A power operation is already pending") from error
    audit_id = uuid.uuid4().hex
    audit_shutdown("approval_issued", audit_id)
    return {
        "operation": "host.shutdown",
        "approval_token": token,
        "expires_at": expires_at.isoformat(),
    }


@private_router.post(
    "/api/power/shutdown",
    status_code=202,
    dependencies=[Depends(verify_power_key)],
)
def request_host_shutdown(body: ShutdownApprovalRequest):
    """Consume a host.shutdown approval and invoke the fixed local socket action."""
    try:
        approvals.consume(body.approval_token)
    except ApprovalError as error:
        raise HTTPException(status_code=409, detail="Power approval is invalid, expired, used, or pending") from error

    audit_id = uuid.uuid4().hex
    try:
        execute_host_shutdown()
    except (ShutdownHelperRejected, ShutdownHelperUnavailable) as error:
        approvals.execution_failed()
        logger.error(
            "power_event=execution_failed operation=host.shutdown audit_id=%s error_type=%s",
            audit_id,
            type(error).__name__,
        )
        raise HTTPException(status_code=503, detail="The host shutdown helper did not accept the request") from None
    except ShutdownOutcomeUnknown as error:
        logger.error(
            "power_event=outcome_unknown operation=host.shutdown audit_id=%s error_type=%s",
            audit_id,
            type(error).__name__,
        )
        raise HTTPException(status_code=503, detail="Shutdown outcome is unknown; duplicate requests are blocked") from None
    except Exception as error:
        # An unexpected helper failure after token consumption may be ambiguous.
        # Keep the pending flag set to prevent another poweroff attempt.
        logger.error(
            "power_event=outcome_unknown operation=host.shutdown audit_id=%s error_type=%s",
            audit_id,
            type(error).__name__,
        )
        raise HTTPException(status_code=503, detail="Shutdown outcome is unknown; duplicate requests are blocked") from None

    audit_shutdown("shutdown_accepted", audit_id)
    return {"status": "shutdown_scheduled", "operation": "host.shutdown", "audit_id": audit_id}
