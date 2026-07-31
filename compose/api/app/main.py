from fastapi import FastAPI

from routers.private import private_router
from routers.public import public_router

app = FastAPI(
    title="Homelab API",
    version="1.0.0",
    description="API pública del homelab. Endpoints privados protegidos con X-API-Key.",
)

app.include_router(public_router)
app.include_router(private_router)
