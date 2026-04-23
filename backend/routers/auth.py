from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from backend.database import get_connection
from backend.dependencies.auth import get_current_user_id
from backend.models import (
    LoginRequest,
    LoginResponseData,
    RegisterRequest,
    error_response,
    success_response,
)
from backend.serializers import serialize_user


router = APIRouter()
# NOTE: Override JWT_SECRET via environment variable before deploying.
# The default here is a dev-only value long enough to silence key-length
# warnings; it must NOT be used in production.
JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret-key-change-this-before-deploying-prod')
JWT_EXPIRES_IN = 604800
JWT_ALGORITHM = 'HS256'


@router.post('/api/register')
async def register(payload: RegisterRequest) -> JSONResponse:
    username = payload.username.strip()
    password = payload.password
    grade = payload.grade.strip()
    subject = payload.subject.strip()

    validation_error = _validate_register_payload(
        username=username,
        password=password,
        grade=grade,
        subject=subject,
    )
    if validation_error is not None:
        return validation_error

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    connection = get_connection()
    try:
        try:
            cursor = connection.execute(
                """
                INSERT INTO users (username, password_hash, grade, subject)
                VALUES (?, ?, ?, ?)
                """,
                (username, password_hash, grade, subject),
            )
            user_id = int(cursor.lastrowid)
            connection.commit()
        except sqlite3.IntegrityError:
            return JSONResponse(
                status_code=409,
                content=error_response(
                    message='用户名已存在',
                    error_code='USERNAME_EXISTS',
                ),
            )

        user_row = _fetch_user_by_id(connection, user_id)
    finally:
        connection.close()

    if user_row is None:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message='服务端异常',
                error_code='INTERNAL_ERROR',
                details={'error': '用户创建成功后未能重新读取用户信息'},
            ),
        )

    return JSONResponse(
        status_code=201,
        content=success_response(serialize_user(user_row)),
    )


@router.get('/api/auth/me')
async def get_me(user_id: int = Depends(get_current_user_id)) -> JSONResponse:
    """
    Lightweight token-validation endpoint.

    - 200: token is valid; returns the current user's profile so the frontend
           can refresh its local edu_user cache.
    - 401: token is missing, malformed, or expired (handled globally in main.py).
    """
    connection = get_connection()
    try:
        user_row = _fetch_user_by_id(connection, user_id)
    finally:
        connection.close()

    if user_row is None:
        return JSONResponse(
            status_code=404,
            content=error_response(
                message='用户不存在',
                error_code='USER_NOT_FOUND',
            ),
        )

    return JSONResponse(status_code=200, content=success_response(serialize_user(user_row)))


@router.post('/api/login')
async def login(payload: LoginRequest) -> JSONResponse:
    username = payload.username.strip()
    password = payload.password

    validation_error = _validate_login_payload(username=username, password=password)
    if validation_error is not None:
        return validation_error

    connection = get_connection()
    try:
        user_row = _fetch_user_by_username(connection, username)
    finally:
        connection.close()

    if user_row is None or not _verify_password(password, str(user_row['password_hash'])):
        return JSONResponse(
            status_code=401,
            content=error_response(
                message='用户名或密码错误',
                error_code='INVALID_CREDENTIALS',
            ),
        )

    user = serialize_user(user_row)
    response_data = LoginResponseData(
        token=_create_token(user_id=user.id, username=user.username),
        token_type='Bearer',
        expires_in=JWT_EXPIRES_IN,
        user=user,
    )
    return JSONResponse(status_code=200, content=success_response(response_data))


def _validate_register_payload(
    username: str,
    password: str,
    grade: str,
    subject: str,
) -> Optional[JSONResponse]:
    if not username or not password or not grade or not subject:
        return JSONResponse(
            status_code=400,
            content=error_response(
                message='请求字段缺失或格式错误',
                error_code='INVALID_REQUEST',
            ),
        )
    return None


def _validate_login_payload(username: str, password: str) -> Optional[JSONResponse]:
    if not username or not password:
        return JSONResponse(
            status_code=400,
            content=error_response(
                message='请求字段缺失或格式错误',
                error_code='INVALID_REQUEST',
            ),
        )
    return None


def _fetch_user_by_id(connection: sqlite3.Connection, user_id: int) -> Optional[sqlite3.Row]:
    return connection.execute(
        """
        SELECT id, username, grade, subject, created_at, is_admin
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()


def _fetch_user_by_username(
    connection: sqlite3.Connection, username: str
) -> Optional[sqlite3.Row]:
    return connection.execute(
        """
        SELECT id, username, grade, subject, password_hash, created_at, is_admin
        FROM users
        WHERE username = ?
        """,
        (username,),
    ).fetchone()


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def _create_token(user_id: int, username: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        'user_id': user_id,
        'username': username,
        'iat': now,
        'exp': now + timedelta(seconds=JWT_EXPIRES_IN),
    }
    return str(jwt.encode(payload, os.getenv('JWT_SECRET', JWT_SECRET), algorithm=JWT_ALGORITHM))
