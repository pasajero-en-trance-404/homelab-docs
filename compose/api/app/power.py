"""Narrow host power operation authorization and fixed socket helper client."""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import logging
import os
import secrets
import socket
import threading
import time

from fastapi import Header, HTTPException

from config import get_api_key

logger = logging.getLogger(__name__)

POWER_ACTION = "host.shutdown"
APPROVAL_TTL_SECONDS = 30
POWER_SOCKET_PATH = os.environ.get(
    "POWER_SOCKET_PATH", "/run/homelab-power/poweroff.sock"
)


class ApprovalError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class ShutdownHelperUnavailable(Exception):
    """The fixed helper could not be reached, so no action was submitted."""


class ShutdownHelperRejected(Exception):
    """The helper explicitly rejected the fixed action before scheduling it."""


class ShutdownOutcomeUnknown(Exception):
    """The helper may have scheduled shutdown, but its acknowledgement was lost."""


class ShutdownApprovalStore:
    """Single outstanding approval and shutdown, guarded across worker threads."""

    def __init__(self):
        self._lock = threading.Lock()
        self._approval_digest: bytes | None = None
        self._expires_at = 0.0
        self._shutdown_pending = False

    def issue(self) -> tuple[str, datetime]:
        with self._lock:
            now = time.monotonic()
            if self._shutdown_pending:
                raise ApprovalError("shutdown_pending")
            if self._approval_digest is not None and now < self._expires_at:
                raise ApprovalError("approval_pending")
            token = secrets.token_urlsafe(32)
            self._approval_digest = _digest(token)
            self._expires_at = now + APPROVAL_TTL_SECONDS
            return token, datetime.now(timezone.utc) + timedelta(seconds=APPROVAL_TTL_SECONDS)

    def consume(self, token: str) -> None:
        candidate = _digest(token)
        with self._lock:
            if self._shutdown_pending:
                raise ApprovalError("shutdown_pending")
            if self._approval_digest is None:
                raise ApprovalError("approval_invalid_or_used")
            if time.monotonic() >= self._expires_at:
                self._clear_approval()
                raise ApprovalError("approval_expired")
            if not hmac.compare_digest(candidate, self._approval_digest):
                raise ApprovalError("approval_invalid")
            self._clear_approval()
            self._shutdown_pending = True

    def execution_failed(self) -> None:
        with self._lock:
            self._shutdown_pending = False

    def reset_for_tests(self) -> None:
        with self._lock:
            self._clear_approval()
            self._shutdown_pending = False

    def _clear_approval(self) -> None:
        self._approval_digest = None
        self._expires_at = 0.0


approvals = ShutdownApprovalStore()


def _digest(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def verify_power_key(x_power_approval_key: str | None = Header(default=None)) -> None:
    expected = os.environ.get("POWER_API_KEY", "")
    if not expected.strip():
        raise HTTPException(status_code=503, detail="Power authorization is not configured")
    if hmac.compare_digest(_digest(expected), _digest(get_api_key())):
        raise HTTPException(status_code=503, detail="Power authorization must use a separate key")
    if not x_power_approval_key or not hmac.compare_digest(
        _digest(x_power_approval_key), _digest(expected)
    ):
        raise HTTPException(status_code=401, detail="Invalid power authorization")


def execute_host_shutdown() -> None:
    """Request only the fixed host.shutdown action from the host-owned socket."""
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.settimeout(5.0)
        try:
            client.connect(POWER_SOCKET_PATH)
        except OSError as error:
            raise ShutdownHelperUnavailable from error
        try:
            client.sendall((POWER_ACTION + "\n").encode("ascii"))
            response = bytearray()
            while len(response) <= 32 and not response.endswith(b"\n"):
                chunk = client.recv(1)
                if not chunk:
                    break
                response.extend(chunk)
        except OSError as error:
            raise ShutdownOutcomeUnknown from error
        if bytes(response) == b"rejected\n":
            raise ShutdownHelperRejected
        if bytes(response) != b"accepted\n":
            raise ShutdownOutcomeUnknown
    finally:
        client.close()


def audit_shutdown(event: str, audit_id: str) -> None:
    """Write only the operation name and opaque event identifier, never secrets."""
    logger.info("power_event=%s operation=%s audit_id=%s", event, POWER_ACTION, audit_id)
