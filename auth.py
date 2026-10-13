import secrets
from pathlib import Path

from fastapi import Header, HTTPException

TOKEN_PATH = Path(__file__).parent / "token.txt"

def load_token() -> str:
    """Read the shared secret from disk. Fail loudly if missing."""
    if not TOKEN_PATH.exists():
        raise RuntimeError(
            f"Missing token file: {TOKEN_PATH}. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\" > token.txt"
        )
    token = TOKEN_PATH.read_text().strip()
    if not token:
        raise RuntimeError(f"Token file {TOKEN_PATH} is empty.")
    return token

def require_token(authorization: str | None = Header(default=None)) -> None:
    """FastAPI dependency: validates 'Authorization: Bearer <token>'."""
    if authorization is None:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, _, supplied = authorization.partition(" ")
    if scheme.lower() != "bearer" or not supplied:
        raise HTTPException(
            status_code=401,
            detail="Expected 'Authorization: Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expected = load_token()
    if not secrets.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )