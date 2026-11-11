from fastapi import APIRouter

public_router = APIRouter()


@public_router.get("/api/health")
def health():
    # The only unauthenticated endpoint: keep the payload minimal.
    return {"status": "ok"}
