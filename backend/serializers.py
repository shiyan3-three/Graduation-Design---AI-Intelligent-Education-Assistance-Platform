from __future__ import annotations

import json
import sqlite3

from backend.models import MessageOut, SessionOut, UserOut


def sqlite_timestamp_to_iso8601(value: str) -> str:
    return value.replace(' ', 'T') + 'Z'


def serialize_session(row: sqlite3.Row) -> SessionOut:
    return SessionOut(
        id=int(row['id']),
        user_id=int(row['user_id']),
        title=str(row['title']),
        created_at=sqlite_timestamp_to_iso8601(str(row['created_at'])),
        updated_at=sqlite_timestamp_to_iso8601(str(row['updated_at'])),
    )


def serialize_user(row: sqlite3.Row) -> UserOut:
    is_admin = bool(row['is_admin']) if 'is_admin' in row.keys() else False
    return UserOut(
        id=int(row['id']),
        username=str(row['username']),
        grade=str(row['grade']),
        subject=str(row['subject']),
        created_at=sqlite_timestamp_to_iso8601(str(row['created_at'])),
        is_admin=is_admin,
    )


def serialize_message(row: sqlite3.Row) -> MessageOut:
    raw_tools = row['tools_used']
    tools_used = json.loads(raw_tools) if raw_tools else None
    return MessageOut(
        id=int(row['id']),
        session_id=int(row['session_id']),
        sequence_no=int(row['sequence_no']),
        role=str(row['role']),
        content=str(row['content']),
        tools_used=tools_used,
        tool_suggestion=None,
        created_at=sqlite_timestamp_to_iso8601(str(row['created_at'])),
    )
