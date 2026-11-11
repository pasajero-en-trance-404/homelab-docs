import hashlib
import hmac
import os


class ConfigurationError(RuntimeError):
    """Raised when a required setting is missing or invalid."""


def get_api_key() -> str:
    """Return the configured API key, or fail closed if it is missing/empty."""
    key = os.environ.get("API_KEY", "")
    if not key.strip():
        raise ConfigurationError(
            "API_KEY is required and must not be empty; refusing to start"
        )
    return key


def validate_api_key() -> None:
    """Validate the API key configuration at application startup."""
    get_api_key()


def _digest(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def api_key_matches(provided: str | None) -> bool:
    """Constant-time comparison of a provided key against the configured key.

    Both values are hashed first so the comparison is independent of the key
    length. Returns False when no key is configured (fail closed).
    """
    if not provided:
        return False
    try:
        expected = get_api_key()
    except ConfigurationError:
        return False
    return hmac.compare_digest(_digest(provided), _digest(expected))
