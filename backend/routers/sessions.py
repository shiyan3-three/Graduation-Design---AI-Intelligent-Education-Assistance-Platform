from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from backend.database import get_connection
from backend.dependencies.auth import get_current_user_id
from backend.models import (
    SessionDetailResponseData,
    SessionListResponseData,
    error_response,
    success_response,
)
from backend.serializers import serialize_message, serialize_session


router = APIRouter()


@router.get('/api/sessions')
async def get_sessions(
    user_id: int = Depends(get_current_user_id),
) -> JSONResponse:
    with closing(get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT id, user_id, title, created_at, updated_at
            FROM sessions
            WHERE user_id = ?
            ORDER BY updated_at DESC, id DESC
            """,
            (user_id,),
        ).fetchall()

    response_data = SessionListResponseData(
        items=[serialize_session(row) for row in rows],
    )
    return JSONResponse(status_code=200, content=success_response(response_data))


@router.get('/api/sessions/{session_id}')
async def get_session_detail(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
) -> JSONResponse:
    with closing(get_connection()) as connection:
        session_row = _fetch_session(connection, session_id, user_id)
        if session_row is None:
            return JSONResponse(
                status_code=404,
                content=error_response(
                    message='会话不存在或不属于当前用户',
                    error_code='SESSION_NOT_FOUND',
                ),
            )

        message_rows = connection.execute(
            """
            SELECT id, session_id, sequence_no, role, content, tools_used, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY sequence_no ASC
            """,
            (session_id,),
        ).fetchall()

    response_data = SessionDetailResponseData(
        session=serialize_session(session_row),
        messages=[serialize_message(row) for row in message_rows],
    )
    return JSONResponse(status_code=200, content=success_response(response_data))


def _fetch_session(
    connection: sqlite3.Connection, session_id: int, user_id: int
) -> Optional[sqlite3.Row]:
    return connection.execute(
        """
        SELECT id, user_id, title, created_at, updated_at
        FROM sessions
        WHERE id = ? AND user_id = ?
        """,
        (session_id, user_id),
    ).fetchone()
