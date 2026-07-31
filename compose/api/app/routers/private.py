from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from util import HOSTNAME, SERVICES, docker_containers, docker_state, verify_key

private_router = APIRouter(dependencies=[Depends(verify_key)])


@private_router.get("/api")
def root():
    return {
        "service": "homelab-api",
        "status": "running",
        "version": "1.0.0",
        "private_endpoints": ["/api/status", "/api/containers"],
    }


@private_router.get("/api/status")
def status():
    services = {}
    for svc in SERVICES:
        state = docker_state(svc)
        services[svc] = (
            "up"
            if state == "running"
            else "down"
            if state in ("exited", "not_found")
            else "unknown"
        )
    return {
        "server": HOSTNAME,
        "services": services,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@private_router.get("/api/containers")
def containers():
    return {
        "server": HOSTNAME,
        "containers": docker_containers(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
