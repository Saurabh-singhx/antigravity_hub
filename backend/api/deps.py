import logging
import os
from pathlib import Path
import re
import secrets
import time
from typing import Dict, List, Optional
from fastapi import Header, HTTPException, Query, Request, status

from config.settings import (
    HUB_AUTH_REQUIRED,
    get_or_create_hub_token,
)

logger = logging.getLogger("AntigravityHub.Security")


class InMemoryRateLimiter:
    """
    Thread-safe, sliding-window rate limiter for sensitive endpoints.
    Protects against action brute-forcing and API denial-of-service.
    """

    def __init__(self):
        self._requests: Dict[str, List[float]] = {}

    def check(self, key: str, max_requests: int, window_seconds: int = 60) -> bool:
        now = time.time()
        timestamps = self._requests.get(key, [])
        # Filter out expired timestamps
        cutoff = now - window_seconds
        valid_timestamps = [t for t in timestamps if t > cutoff]

        if len(valid_timestamps) >= max_requests:
            self._requests[key] = valid_timestamps
            return False

        valid_timestamps.append(now)
        self._requests[key] = valid_timestamps
        return True

    def reset(self, key: str):
        self._requests.pop(key, None)


limiter = InMemoryRateLimiter()


def get_client_ip(request: Request) -> str:
    """Extracts client IP address safely, taking proxies into account if available."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def verify_hub_token(
    request: Request,
    x_hub_token: Optional[str] = Header(None, alias="X-Hub-Token"),
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None),
) -> str:
    """
    FastAPI dependency validating the pre-shared Hub Token.
    Accepts:
      1. 'X-Hub-Token' header
      2. 'Authorization: Bearer <token>' header
      3. '?token=<token>' query parameter (useful for WebSockets & media requests)
    """
    if not HUB_AUTH_REQUIRED:
        return "auth_disabled"

    expected_token = get_or_create_hub_token()

    provided_token = None
    if x_hub_token:
        provided_token = x_hub_token.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        provided_token = authorization[7:].strip()
    elif token:
        provided_token = token.strip()

    client_ip = get_client_ip(request)

    # Brute-force lockout check: max 15 failed token attempts / 5 mins
    lockout_key = f"auth_fail:{client_ip}"
    if provided_token is None or not secrets.compare_digest(provided_token, expected_token):
        # Record failed attempt
        if not limiter.check(lockout_key, max_requests=15, window_seconds=300):
            logger.warning(f"Auth brute-force lockout triggered for IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed authentication attempts. Locked out for 5 minutes.",
            )

        logger.warning(f"Unauthorized access attempt from {client_ip} on {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Missing or invalid X-Hub-Token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Reset failure counter upon successful auth
    limiter.reset(lockout_key)
    return provided_token


def require_rate_limit(max_requests: int, window_seconds: int = 60, key_prefix: str = "rate"):
    """Dependency factory generating rate-limit checks per endpoint & IP."""
    def dependency(request: Request):
        client_ip = get_client_ip(request)
        rate_key = f"{key_prefix}:{request.url.path}:{client_ip}"
        if not limiter.check(rate_key, max_requests=max_requests, window_seconds=window_seconds):
            logger.warning(f"Rate limit exceeded on {request.url.path} by {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded ({max_requests} requests per {window_seconds}s). Please wait.",
            )
        return True

    return dependency


def sanitize_filename(filename: str) -> str:
    """
    Strict path-traversal prevention for file downloads and screenshots.
    Rejects any characters outside [a-zA-Z0-9_.-] and disallows '..' or hidden files.
    """
    if not filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty")

    base = Path(filename).name
    if base != filename or base.startswith(".") or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename format: directory traversal detected")

    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", base):
        raise HTTPException(status_code=400, detail="Invalid characters in filename")

    return base
