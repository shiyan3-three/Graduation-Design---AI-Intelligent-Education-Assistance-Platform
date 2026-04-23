from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import closing
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from backend.database import get_connection
from backend.dependencies.auth import get_current_user_id
from backend.models import (
    ChatRequest,
    ChatResponseData,
    MessageOut,
    SessionOut,
    ToolSuggestion,
    error_response,
    success_response,
)
from backend.serializers import serialize_message, serialize_session
from backend.services.llm import generate_assistant_reply, generate_assistant_reply_stream
from backend.services.tagging import extract_message_tags


router = APIRouter()
LOGGER = logging.getLogger(__name__)


@router.post('/api/chat')
async def post_chat(
    payload: ChatRequest,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id),
) -> JSONResponse:
    content = payload.content.strip()
    if not content:
        return JSONResponse(
            status_code=400,
            content=error_response(
                message='请求字段缺失或格式错误',
                error_code='INVALID_REQUEST',
                details={'content': 'content 不能为空'},
            ),
        )

    with closing(get_connection()) as connection:
        session_row = _resolve_session(connection, payload.session_id, user_id)
        if payload.session_id is not None and session_row is None:
            return JSONResponse(
                status_code=404,
                content=error_response(
                    message='会话不存在或不属于当前用户',
                    error_code='SESSION_NOT_FOUND',
                ),
            )

        if session_row is None:
            session_id = _create_session(connection, user_id, _build_session_title(content))
            session_row = _fetch_session(connection, session_id, user_id)
        else:
            session_id = int(session_row['id'])

        user_sequence_no = _get_next_sequence_no(connection, session_id)
        user_message_id = _insert_message(
            connection=connection,
            session_id=session_id,
            sequence_no=user_sequence_no,
            role='user',
            content=content,
            tools_used=None,
        )
        _touch_session(connection, session_id)
        conversation = _build_conversation(connection, session_id)
        user_message_row = _fetch_message(connection, user_message_id)
        connection.commit()

    assistant_reply = await generate_assistant_reply(
        conversation,
        tool_preference=payload.tool_preference,
    )

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

        assistant_sequence_no = _get_next_sequence_no(connection, session_id)
        assistant_message_id = _insert_message(
            connection=connection,
            session_id=session_id,
            sequence_no=assistant_sequence_no,
            role='assistant',
            content=assistant_reply.content,
            tools_used=assistant_reply.tools_used or None,
        )
        _touch_session(connection, session_id)

        session_row = _fetch_session(connection, session_id, user_id)
        assistant_message_row = _fetch_message(connection, assistant_message_id)
        connection.commit()

    background_tasks.add_task(
        _tag_assistant_message_safely,
        assistant_message_id,
        assistant_reply.content,
    )

    assistant_message = serialize_message(assistant_message_row).model_copy(
        update={
            'tools_used': assistant_reply.tools_used,
            'tool_suggestion': (
                ToolSuggestion(**assistant_reply.tool_suggestion)
                if assistant_reply.tool_suggestion
                else None
            ),
        }
    )
    response_data = ChatResponseData(
        session=serialize_session(session_row),
        user_message=serialize_message(user_message_row),
        assistant_message=assistant_message,
    )
    return JSONResponse(
        status_code=200,
        content=success_response(response_data),
        background=background_tasks,
    )


@router.post('/api/chat/stream')
async def post_chat_stream(
    payload: ChatRequest,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id),
):
    content = payload.content.strip()
    if not content:
        return JSONResponse(
            status_code=400,
            content=error_response(
                message='请求字段缺失或格式错误',
                error_code='INVALID_REQUEST',
                details={'content': 'content 不能为空'},
            ),
        )

    with closing(get_connection()) as connection:
        session_row = _resolve_session(connection, payload.session_id, user_id)
        if payload.session_id is not None and session_row is None:
            return JSONResponse(
                status_code=404,
                content=error_response(
                    message='会话不存在或不属于当前用户',
                    error_code='SESSION_NOT_FOUND',
                ),
            )

        if session_row is None:
            session_id = _create_session(connection, user_id, _build_session_title(content))
        else:
            session_id = int(session_row['id'])

        user_sequence_no = _get_next_sequence_no(connection, session_id)
        _insert_message(
            connection=connection,
            session_id=session_id,
            sequence_no=user_sequence_no,
            role='user',
            content=content,
            tools_used=None,
        )
        _touch_session(connection, session_id)
        conversation = _build_conversation(connection, session_id)
        connection.commit()

    async def event_stream():
        accumulated_content: List[str] = []
        tools_used: List[Dict[str, Any]] = []
        try:
            async for event in generate_assistant_reply_stream(
                conversation,
                tool_preference=payload.tool_preference,
            ):
                event_type = event.get('type')
                if event_type == 'delta':
                    chunk = str(event.get('content') or '')
                    if not chunk:
                        continue
                    accumulated_content.append(chunk)
                    yield _format_sse_event({'type': 'delta', 'content': chunk})
                    continue

                if event_type == 'done':
                    raw_tools_used = event.get('tools_used')
                    if isinstance(raw_tools_used, list):
                        tools_used = raw_tools_used
                    continue

                if event_type == 'error':
                    message = str(event.get('message') or '流式生成失败')
                    yield _format_sse_event({'type': 'error', 'message': message})
                    return

            assistant_content = ''.join(accumulated_content)
            if not assistant_content.strip():
                yield _format_sse_event({'type': 'error', 'message': 'LLM 返回内容为空'})
                return

            with closing(get_connection()) as connection:
                session_row = _fetch_session(connection, session_id, user_id)
                if session_row is None:
                    yield _format_sse_event(
                        {'type': 'error', 'message': '会话不存在或不属于当前用户'}
                    )
                    return

                assistant_sequence_no = _get_next_sequence_no(connection, session_id)
                assistant_message_id = _insert_message(
                    connection=connection,
                    session_id=session_id,
                    sequence_no=assistant_sequence_no,
                    role='assistant',
                    content=assistant_content,
                    tools_used=tools_used or None,
                )
                _touch_session(connection, session_id)
                connection.commit()

            background_tasks.add_task(
                _tag_assistant_message_safely,
                assistant_message_id,
                assistant_content,
            )
            yield _format_sse_event(
                {
                    'type': 'done',
                    'session_id': session_id,
                    'message_id': assistant_message_id,
                    'tools_used': tools_used,
                }
            )
        except Exception as exc:
            LOGGER.exception('Streaming chat failed: %s', exc)
            yield _format_sse_event({'type': 'error', 'message': '流式生成失败'})

    return StreamingResponse(
        event_stream(),
        media_type='text/event-stream',
        background=background_tasks,
    )


def _resolve_session(
    connection: sqlite3.Connection, session_id: Optional[int], user_id: int
) -> Optional[sqlite3.Row]:
    if session_id is None:
        return None
    return _fetch_session(connection, session_id, user_id)


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


def _create_session(connection: sqlite3.Connection, user_id: int, title: str) -> int:
    cursor = connection.execute(
        """
        INSERT INTO sessions (user_id, title)
        VALUES (?, ?)
        """,
        (user_id, title),
    )
    return int(cursor.lastrowid)


def _get_next_sequence_no(connection: sqlite3.Connection, session_id: int) -> int:
    row = connection.execute(
        'SELECT COALESCE(MAX(sequence_no), 0) AS max_sequence_no FROM messages WHERE session_id = ?',
        (session_id,),
    ).fetchone()
    max_sequence_no = int(row['max_sequence_no']) if row is not None else 0
    return max_sequence_no + 1


def _insert_message(
    connection: sqlite3.Connection,
    session_id: int,
    sequence_no: int,
    role: str,
    content: str,
    tools_used: Optional[List[Dict[str, Any]]],
) -> int:
    serialized_tools = json.dumps(tools_used, ensure_ascii=False) if tools_used else None
    cursor = connection.execute(
        """
        INSERT INTO messages (session_id, sequence_no, role, content, tools_used)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session_id, sequence_no, role, content, serialized_tools),
    )
    return int(cursor.lastrowid)


async def _tag_assistant_message_safely(message_id: int, content: str) -> None:
    try:
        tags = await extract_message_tags(content)
        if not tags:
            return
        _insert_message_tags(message_id, tags)
    except Exception as exc:
        LOGGER.debug('Message tag extraction skipped for message %s: %s', message_id, exc)


def _insert_message_tags(message_id: int, tags: List[str]) -> None:
    with closing(get_connection()) as connection:
        for tag in _deduplicate_tags(tags):
            connection.execute(
                """
                INSERT OR IGNORE INTO message_tags (message_id, tag)
                VALUES (?, ?)
                """,
                (message_id, tag),
            )
        connection.commit()


def _deduplicate_tags(tags: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for tag in tags:
        normalized = str(tag).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _touch_session(connection: sqlite3.Connection, session_id: int) -> None:
    connection.execute(
        'UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (session_id,),
    )


def _fetch_message(connection: sqlite3.Connection, message_id: int) -> sqlite3.Row:
    row = connection.execute(
        """
        SELECT id, session_id, sequence_no, role, content, tools_used, created_at
        FROM messages
        WHERE id = ?
        """,
        (message_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f'Message {message_id} was not found after insert.')
    return row


def _build_conversation(connection: sqlite3.Connection, session_id: int) -> List[Dict[str, str]]:
    rows = connection.execute(
        """
        SELECT role, content
        FROM messages
        WHERE session_id = ?
        ORDER BY sequence_no ASC
        """,
        (session_id,),
    ).fetchall()
    return [{'role': str(row['role']), 'content': str(row['content'])} for row in rows]


def _build_session_title(content: str) -> str:
    title = content[:20].strip()
    return title or '新会话'


def _format_sse_event(event: Dict[str, Any]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
