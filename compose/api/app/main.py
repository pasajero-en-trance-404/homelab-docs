from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, Depends
import os

app = FastAPI(title="Homelab API", version="1.0.0")

API_KEY = os.environ.get("API_KEY", "")


def verify_key(x_api_key: str = Header(None)):
    if not API_KEY:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")


@app.get("/api")
def root(_=Depends(verify_key)):
    return {"service": "homelab-api", "status": "running"}


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "server": "debian-server",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
