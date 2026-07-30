from datetime import datetime, timezone
from http.client import HTTPConnection
import json
import os
import socket

from fastapi import FastAPI, Header, HTTPException, Depends

SERVICES = ["homepage", "portainer", "n8n", "uptime-kuma"]

app = FastAPI(title="Homelab API", version="1.0.0")

API_KEY = os.environ.get("API_KEY", "")

HOSTNAME = socket.gethostname()


def verify_key(x_api_key: str = Header(None)):
    if not API_KEY:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")


def _docker_state(name: str) -> str:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        sock.connect("/var/run/docker.sock")
        conn = HTTPConnection("localhost")
        conn.sock = sock
        conn.request("GET", f"/containers/{name}/json")
        resp = conn.getresponse()
        if resp.status == 200:
            data = json.loads(resp.read())
            return data["State"]["Status"]
        return "not_found"
    except Exception:
        return "unknown"
    finally:
        try:
            sock.close()
        except Exception:
            pass


@app.get("/api")
def root(_=Depends(verify_key)):
    return {"service": "homelab-api", "status": "running"}


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "server": HOSTNAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/status")
def status(_=Depends(verify_key)):
    services = {}
    for svc in SERVICES:
        state = _docker_state(svc)
        services[svc] = "up" if state == "running" else "down" if state in (
            "exited", "not_found") else "unknown"
    return {
        "server": HOSTNAME,
        "services": services,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
