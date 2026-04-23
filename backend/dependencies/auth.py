"""
backend/dependencies/auth.py

Reusable FastAPI dependency that extracts and validates the JWT from the
`Authorization: Bearer <token>` request header, returning the authenticated
user's `user_id` as an integer.

Usage:
    from backend.dependencies.auth import get_current_user_id

    @router.get('/api/sessions')
    async def get_sessions(user_id: int = Depends(get_current_user_id)):
        ...
"""
from __future__ import annotations

import os
from contextlib import closing
from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException

from backend.database import get_connection

_JWT_ALGORITHM = 'HS256'


def _get_secret() -> str:
    """Read JWT_SECRET at call time so tests can override the env variable."""
    return os.getenv('JWT_SECRET', 'dev-secret-key-change-this-before-deploying-prod')


def get_current_user_id(
    authorization: Optional[str] = Header(None),
) -> int:
    """
    Validate the Bearer token in the Authorization header.

    Returns the numeric user_id encoded in the JWT payload.
    Raises HTTP 401 if the header is missing, malformed, or the token is
    invalid / expired.
    """
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(
            status_code=401,
            detail='Missing or invalid Authorization header',
        )

    token = authorization[len('Bearer '):]
    try:
        payload = jwt.decode(token, _get_secret(), algorithms=[_JWT_ALGORITHM])
        return int(payload['user_id'])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(
            status_code=401,
            detail='Invalid or expired token',
        )


def get_current_admin_user_id(
    user_id: int = Depends(get_current_user_id),
) -> int:
    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT id, is_admin
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

    if row is None or int(row['is_admin']) != 1:
        raise HTTPException(
            status_code=403,
            detail='Admin access required',
        )

    return user_id
