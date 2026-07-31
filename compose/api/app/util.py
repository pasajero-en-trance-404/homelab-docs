from http.client import HTTPConnection
import json
import os
import socket

from fastapi import Header, HTTPException

API_KEY = os.environ.get("API_KEY", "")

HOSTNAME = socket.gethostname()

SERVICES = ["traefik", "homepage", "portainer", "n8n", "uptime-kuma"]


def verify_key(x_api_key: str = Header(None)):
    if not API_KEY:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")


def docker_state(name: str) -> str:
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


def docker_containers() -> list:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        sock.connect("/var/run/docker.sock")
        conn = HTTPConnection("localhost")
        conn.sock = sock
        conn.request("GET", "/containers/json")
        resp = conn.getresponse()
        if resp.status != 200:
            return []
        data = json.loads(resp.read())
        return [
            {
                "name": c["Names"][0].lstrip("/"),
                "image": c["Image"],
                "state": c["State"],
                "status": c["Status"],
            }
            for c in data
        ]
    except Exception:
        return []
    finally:
        try:
            sock.close()
        except Exception:
            pass
