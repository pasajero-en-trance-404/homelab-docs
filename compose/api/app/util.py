import json
import os
import socket
from urllib.error import URLError
from urllib.request import ProxyHandler, Request, build_opener

from fastapi import Header, HTTPException

from config import ConfigurationError, api_key_matches, get_api_key

HOSTNAME = socket.gethostname()

SERVICES = ["traefik", "homepage", "portainer", "n8n", "uptime-kuma"]

# Internal socket-proxy endpoint. It is only reachable on the docker_api
# network; the proxy only allows GET /containers/json.
DOCKER_PROXY_URL = os.environ.get(
    "DOCKER_PROXY_URL", "http://socket-proxy:2375"
).rstrip("/")

# Never route internal Docker API calls through an environment HTTP proxy.
_docker_opener = build_opener(ProxyHandler({}))


def verify_key(x_api_key: str | None = Header(default=None)) -> None:
    """Dependency protecting every endpoint except GET /api/health."""
    try:
        get_api_key()
    except ConfigurationError:
        # Fail closed and never reveal configuration details.
        raise HTTPException(
            status_code=500, detail="API authentication is not configured"
        ) from None
    if not api_key_matches(x_api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "X-API-Key"},
        )


def _docker_get(path: str):
    """Perform a single GET against the read-only Docker socket proxy."""
    request = Request(
        f"{DOCKER_PROXY_URL}{path}",
        method="GET",
        headers={"Accept": "application/json"},
    )
    try:
        with _docker_opener.open(request, timeout=3) as response:
            if response.status != 200:
                return None
            return json.loads(response.read().decode("utf-8"))
    except (URLError, OSError, ValueError):
        return None


def docker_containers():
    """Return running containers from GET /containers/json.

    Returns None when the socket proxy is unreachable or returns an invalid
    response, so callers can distinguish "unknown" from "no containers".
    """
    data = _docker_get("/containers/json")
    if not isinstance(data, list):
        return None
    containers = []
    for container in data:
        try:
            names = container.get("Names") or []
            containers.append(
                {
                    "name": names[0].lstrip("/") if names else "",
                    "image": container.get("Image", ""),
                    "state": container.get("State", "unknown"),
                    "status": container.get("Status", ""),
                }
            )
        except AttributeError:
            continue
    return containers
