from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from config import validate_api_key
from routers.private import private_router
from routers.public import public_router
from util import verify_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail closed: refuse to start without a non-empty API_KEY.
    validate_api_key()
    yield


app = FastAPI(
    title="Homelab API",
    version="1.0.0",
    description=(
        "API del homelab. Solo GET /api/health es público; el resto "
        "requiere X-API-Key."
    ),
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.include_router(public_router)
app.include_router(private_router)


@app.get("/openapi.json", include_in_schema=False, dependencies=[Depends(verify_key)])
def openapi_schema():
    """OpenAPI schema, protected like every other non-health route."""
    return JSONResponse(app.openapi())
