from __future__ import annotations

from contextlib import closing
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.database import get_connection
from backend.dependencies.auth import get_current_admin_user_id
from backend.models import (
    AdminQuestionsResponseData,
    AdminStatsResponseData,
    AdminUserOut,
    AdminUsersResponseData,
    CreateQuestionRequest,
    QuestionOut,
    UpdateQuestionRequest,
    error_response,
    success_response,
)
from backend.serializers import sqlite_timestamp_to_iso8601


router = APIRouter()


@router.get('/api/admin/users')
async def get_admin_users(
    _: int = Depends(get_current_admin_user_id),
) -> JSONResponse:
    with closing(get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT id, username, grade, subject, created_at, is_admin
            FROM users
            ORDER BY id ASC
            """
        ).fetchall()

    response_data = AdminUsersResponseData(
        items=[
            AdminUserOut(
                id=int(row['id']),
                username=str(row['username']),
                grade=str(row['grade']),
                subject=str(row['subject']),
                created_at=sqlite_timestamp_to_iso8601(str(row['created_at'])),
                is_admin=bool(row['is_admin']),
            )
            for row in rows
        ],
    )
    return JSONResponse(status_code=200, content=success_response(response_data))


@router.put('/api/admin/users/{target_id}/admin')
async def toggle_admin(
    target_id: int,
    admin_user_id: int = Depends(get_current_admin_user_id),
) -> JSONResponse:
    if target_id == admin_user_id:
        return JSONResponse(
            status_code=400,
            content=error_response(
                message='Admin cannot change own admin status',
                error_code='ADMIN_CANNOT_TOGGLE_SELF',
            ),
        )

    with closing(get_connection()) as connection:
        row = _fetch_user(connection, target_id)
        if row is None:
            return JSONResponse(
                status_code=404,
                content=error_response(
                    message='User not found',
                    error_code='USER_NOT_FOUND',
                ),
            )

        next_is_admin = 0 if int(row['is_admin']) == 1 else 1
        connection.execute(
            """
            UPDATE users
            SET is_admin = ?
            WHERE id = ?
            """,
            (next_is_admin, target_id),
        )
        connection.commit()
        updated_row = _fetch_user(connection, target_id)

    return JSONResponse(
        status_code=200,
        content=success_response(_serialize_admin_user(updated_row)),
    )


@router.get('/api/admin/stats')
async def get_admin_stats(
    _: int = Depends(get_current_admin_user_id),
) -> JSONResponse:
    with closing(get_connection()) as connection:
        response_data = AdminStatsResponseData(
            total_users=_count_rows(connection, 'users'),
            total_sessions=_count_rows(connection, 'sessions'),
            total_messages=_count_rows(connection, 'messages'),
            total_recommendations=_count_rows(connection, 'recommendation_items'),
        )

    return JSONResponse(status_code=200, content=success_response(response_data))


@router.get('/api/admin/questions')
async def get_admin_questions(
    subject: str | None = None,
    topic: str | None = None,
    _: int = Depends(get_current_admin_user_id),
) -> JSONResponse:
    where_clauses: list[str] = []
    params: list[str] = []
    if subject:
        where_clauses.append('subject = ?')
        params.append(subject)
    if topic:
        where_clauses.append('LOWER(topic) LIKE ?')
        params.append(f'%{topic.lower()}%')

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ''
    with closing(get_connection()) as connection:
        rows = connection.execute(
            f"""
            SELECT id, subject, topic, question,
                   option_a, option_b, option_c, option_d,
                   answer, source
            FROM question_bank
            {where_sql}
            ORDER BY id ASC
            """,
            tuple(params),
        ).fetchall()

    response_data = AdminQuestionsResponseData(
        items=[_serialize_question(row) for row in rows],
    )
    return JSONResponse(status_code=200, content=success_response(response_data))


@router.post('/api/admin/questions')
async def create_admin_question(
    payload: dict[str, Any],
    _: int = Depends(get_current_admin_user_id),
) -> JSONResponse:
    try:
        request_data = CreateQuestionRequest.model_validate(payload)
    except ValidationError as exc:
        return JSONResponse(
            status_code=422,
            content=error_response(
                message='Question payload is invalid',
                error_code='INVALID_QUESTION_PAYLOAD',
                details={'errors': exc.errors()},
            ),
        )

    option_a, option_b, option_c, option_d = _split_options(request_data.options)
    with closing(get_connection()) as connection:
        cursor = connection.execute(
            """
            INSERT INTO question_bank (
                subject, topic, question,
                option_a, option_b, option_c, option_d,
                answer, explanation, source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_data.subject,
                request_data.topic,
                request_data.question,
                option_a,
                option_b,
                option_c,
                option_d,
                request_data.answer,
                '',
                request_data.source,
            ),
        )
        connection.commit()
        row = _fetch_question(connection, int(cursor.lastrowid))

    return JSONResponse(
        status_code=201,
        content=success_response(_serialize_question(row)),
    )


@router.put('/api/admin/questions/{question_id}')
async def update_admin_question(
    question_id: int,
    payload: UpdateQuestionRequest,
    _: int = Depends(get_current_admin_user_id),
) -> JSONResponse:
    with closing(get_connection()) as connection:
        row = _fetch_question(connection, question_id)
        if row is None:
            return JSONResponse(
                status_code=404,
                content=error_response(
                    message='Question not found',
                    error_code='QUESTION_NOT_FOUND',
                ),
            )

        updates: list[str] = []
        params: list[str] = []
        for field_name in ('question', 'answer', 'topic', 'subject'):
            value = getattr(payload, field_name)
            if value is not None:
                updates.append(f'{field_name} = ?')
                params.append(value)

        if payload.options is not None:
            option_a, option_b, option_c, option_d = _split_options(payload.options)
            updates.extend(['option_a = ?', 'option_b = ?', 'option_c = ?', 'option_d = ?'])
            params.extend([option_a, option_b, option_c, option_d])

        if updates:
            params.append(str(question_id))
            connection.execute(
                f"""
                UPDATE question_bank
                SET {', '.join(updates)}
                WHERE id = ?
                """,
                tuple(params),
            )
            connection.commit()

        updated_row = _fetch_question(connection, question_id)

    return JSONResponse(
        status_code=200,
        content=success_response(_serialize_question(updated_row)),
    )


@router.delete('/api/admin/questions/{question_id}')
async def delete_admin_question(
    question_id: int,
    _: int = Depends(get_current_admin_user_id),
) -> JSONResponse:
    with closing(get_connection()) as connection:
        cursor = connection.execute(
            """
            DELETE FROM question_bank
            WHERE id = ?
            """,
            (question_id,),
        )
        if cursor.rowcount == 0:
            return JSONResponse(
                status_code=404,
                content=error_response(
                    message='Question not found',
                    error_code='QUESTION_NOT_FOUND',
                ),
            )
        connection.commit()

    return JSONResponse(
        status_code=200,
        content=success_response({'deleted_question_id': question_id}, message='Question deleted'),
    )


@router.delete('/api/admin/users/{user_id}')
async def delete_admin_user(
    user_id: int,
    admin_user_id: int = Depends(get_current_admin_user_id),
) -> JSONResponse:
    if user_id == admin_user_id:
        return JSONResponse(
            status_code=400,
            content=error_response(
                message='Admin cannot delete self',
                error_code='ADMIN_CANNOT_DELETE_SELF',
            ),
        )

    with closing(get_connection()) as connection:
        cursor = connection.execute(
            """
            DELETE FROM users
            WHERE id = ?
            """,
            (user_id,),
        )
        if cursor.rowcount == 0:
            return JSONResponse(
                status_code=404,
                content=error_response(
                    message='User not found',
                    error_code='USER_NOT_FOUND',
                ),
            )
        connection.commit()

    return JSONResponse(
        status_code=200,
        content=success_response({'deleted_user_id': user_id}, message='User deleted'),
    )


def _count_rows(connection, table: str) -> int:
    if table not in {'users', 'sessions', 'messages', 'recommendation_items'}:
        raise ValueError(f'Unexpected table name: {table}')
    row = connection.execute(f'SELECT COUNT(*) AS count FROM {table}').fetchone()
    return int(row['count']) if row is not None else 0


def _fetch_user(connection, user_id: int):
    return connection.execute(
        """
        SELECT id, username, grade, subject, created_at, is_admin
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()


def _serialize_admin_user(row) -> AdminUserOut:
    return AdminUserOut(
        id=int(row['id']),
        username=str(row['username']),
        grade=str(row['grade']),
        subject=str(row['subject']),
        created_at=sqlite_timestamp_to_iso8601(str(row['created_at'])),
        is_admin=bool(row['is_admin']),
    )


def _fetch_question(connection, question_id: int):
    return connection.execute(
        """
        SELECT id, subject, topic, question,
               option_a, option_b, option_c, option_d,
               answer, source
        FROM question_bank
        WHERE id = ?
        """,
        (question_id,),
    ).fetchone()


def _serialize_question(row) -> QuestionOut:
    return QuestionOut(
        id=int(row['id']),
        subject=str(row['subject']),
        topic=str(row['topic']),
        question=str(row['question']),
        options=_join_options(
            str(row['option_a'] or ''),
            str(row['option_b'] or ''),
            str(row['option_c'] or ''),
            str(row['option_d'] or ''),
        ),
        answer=str(row['answer']),
        source=str(row['source']),
    )


def _join_options(option_a: str, option_b: str, option_c: str, option_d: str) -> str:
    return f'A. {option_a}\nB. {option_b}\nC. {option_c}\nD. {option_d}'


def _split_options(options: str) -> tuple[str, str, str, str]:
    values: list[str] = []
    for line in options.strip().splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        values.append(_strip_option_prefix(stripped))

    while len(values) < 4:
        values.append('')
    return tuple(values[:4])


def _strip_option_prefix(line: str) -> str:
    if len(line) < 2 or line[0].upper() not in {'A', 'B', 'C', 'D'}:
        return line

    remainder = line[1:].lstrip()
    if not remainder:
        return line

    if remainder[0] in {'.', ')', ':', '\u3001', '\uff1a'}:
        return remainder[1:].lstrip()
    if line[1].isspace():
        return remainder
    return line
