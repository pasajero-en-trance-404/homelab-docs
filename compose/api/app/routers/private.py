from datetime import datetime, timezone
import os
import shutil
from time import sleep
import uuid
from glob import glob
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

DISK_PATHS = ("/", "/app")


def _read_cpu_times():
    try:
        with open("/proc/stat") as f:
            fields = f.readline().split()
        if not fields or fields[0] != "cpu":
            return None
        values = [int(value) for value in fields[1:]]
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        return sum(values), idle
    except (OSError, ValueError, IndexError):
        return None


def _cpu_usage_percent():
    first = _read_cpu_times()
    if first is None:
        return None
    sleep(0.1)
    second = _read_cpu_times()
    if second is None:
        return None
    total_delta = second[0] - first[0]
    idle_delta = second[1] - first[1]
    if total_delta <= 0:
        return None
    usage = 100.0 * (1.0 - idle_delta / total_delta)
    return round(max(0.0, min(100.0, usage)), 2)


def _load_average():
    try:
        with open("/proc/loadavg") as f:
            values = f.read().split()
        return {
            "1m": float(values[0]),
            "5m": float(values[1]),
            "15m": float(values[2]),
        }
    except (OSError, ValueError, IndexError):
        return None


def _memory_info():
    try:
        values = {}
        with open("/proc/meminfo") as f:
            for line in f:
                name, raw = line.split(":", 1)
                values[name] = int(raw.split()[0]) * 1024
    except (OSError, ValueError, IndexError):
        return None

    total = values.get("MemTotal")
    if not total:
        return None

    available = values.get("MemAvailable")
    if available is None:
        available = (
            values.get("MemFree", 0)
            + values.get("Buffers", 0)
            + values.get("Cached", 0)
        )
    used = max(0, total - available)
    memory = {
        "total_bytes": total,
        "used_bytes": used,
        "available_bytes": available,
        "used_percent": round(used / total * 100.0, 2),
        "swap": None,
    }

    swap_total = values.get("SwapTotal", 0)
    if swap_total:
        swap_free = values.get("SwapFree", 0)
        swap_used = max(0, swap_total - swap_free)
        memory["swap"] = {
            "total_bytes": swap_total,
            "used_bytes": swap_used,
            "free_bytes": swap_free,
            "used_percent": round(swap_used / swap_total * 100.0, 2),
        }
    return memory


def _disk_info():
    disks = []
    seen_devices = set()
    for path in DISK_PATHS:
        if not os.path.isdir(path):
            continue
        try:
            device = os.stat(path).st_dev
            usage = shutil.disk_usage(path)
        except OSError:
            continue
        if device in seen_devices:
            continue
        seen_devices.add(device)
        disks.append(
            {
                "path": path,
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
                "used_percent": round(usage.used / usage.total * 100.0, 2)
                if usage.total
                else None,
            }
        )
    return disks or None


def _uptime_seconds():
    try:
        with open("/proc/uptime") as f:
            return int(float(f.read().split()[0]))
    except (OSError, ValueError, IndexError):
        return None


def _cpu_temperature_c():
    temperatures = []
    for path in glob("/sys/class/thermal/thermal_zone*/temp"):
        try:
            with open(path) as f:
                raw = int(f.read().strip())
        except (OSError, ValueError):
            continue
        if raw > 0:
            temperatures.append(raw / 1000.0)
    if not temperatures:
        return None
    return round(max(temperatures), 1)


class ShutdownApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approval_token: str = Field(min_length=40, max_length=128)


@private_router.get("/")
def root():
    return {
        "name": "Homelab API",
        "version": "1.1.0",
        "description": "API del homelab",
        "endpoints": {
            "root": "/",
            "health": "/api/health",
            "status": "/api/status",
            "containers": "/api/containers",
            "time": "/api/time",
            "ip": "/api/ip",
            "request": "/api/request",
            "server": "/api/server",
            "uuid": "/api/uuid",
            "resources": "/api/resources",
            "power_shutdown_prepare": "/api/power/shutdown/prepare",
            "power_shutdown": "/api/power/shutdown",
            "openapi": "/openapi.json",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@private_router.get("/api")
def api_root():
    return {
        "service": "homelab-api",
        "status": "running",
        "version": "1.1.0",
        "private_endpoints": [
            "/",
            "/api",
            "/api/status",
            "/api/containers",
            "/api/time",
            "/api/ip",
            "/api/request",
            "/api/server",
            "/api/uuid",
            "/api/resources",
            "/api/power/shutdown/prepare",
            "/api/power/shutdown",
            "/openapi.json",
        ],
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


@private_router.get("/api/resources")
def resources():
    payload = {
        "hostname": HOSTNAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": _uptime_seconds(),
        "cpu": {
            "cores": os.cpu_count(),
            "load_average": _load_average(),
            "usage_percent": _cpu_usage_percent(),
        },
        "memory": _memory_info(),
        "disk": _disk_info(),
    }
    temperature = _cpu_temperature_c()
    if temperature is not None:
        payload["temperature_c"] = temperature
    return payload


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
