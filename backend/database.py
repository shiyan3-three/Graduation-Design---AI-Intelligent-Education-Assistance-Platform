from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from backend.env import load_backend_env


load_backend_env()

DEFAULT_DB_PATH = Path(__file__).resolve().parent / 'app.db'
DB_PATH = Path(os.getenv('APP_DB_PATH', str(DEFAULT_DB_PATH)))


DDL_SCRIPT = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    grade TEXT NOT NULL,
    subject TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL DEFAULT '新会话',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL,
    sequence_no INTEGER NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('system', 'user', 'assistant', 'tool')),
    content TEXT NOT NULL,
    tools_used TEXT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (session_id, sequence_no),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS message_tags (
    id INTEGER PRIMARY KEY,
    message_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (message_id, tag),
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS recommendation_items (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    recommended_topic TEXT NOT NULL,
    question_payload TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'question_tool',
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'completed', 'skipped')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    feedback_at TEXT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS question_bank (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    topic TEXT NOT NULL,
    question TEXT NOT NULL,
    option_a TEXT,
    option_b TEXT,
    option_c TEXT,
    option_d TEXT,
    answer TEXT NOT NULL,
    explanation TEXT DEFAULT '',
    source TEXT NOT NULL DEFAULT 'ceval'
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_updated_at
    ON sessions(user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_messages_session_sequence
    ON messages(session_id, sequence_no);

CREATE INDEX IF NOT EXISTS idx_message_tags_tag
    ON message_tags(tag);

CREATE INDEX IF NOT EXISTS idx_recommendation_items_user_created_at
    ON recommendation_items(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_question_bank_topic_subject
    ON question_bank(topic, subject);
"""


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    return connection


def _run_migrations(connection: sqlite3.Connection) -> None:
    try:
        connection.execute(
            """
            ALTER TABLE users
            ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0
            """
        )
    except sqlite3.OperationalError as exc:
        if 'duplicate column name' not in str(exc).lower():
            raise


def ensure_test_user(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO users (id, username, password_hash, grade, subject)
        VALUES (?, ?, ?, ?, ?)
        """,
        (1, 'demo_user', 'dev-only-hash', '高一', '数学'),
    )


def ensure_test_admin(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO users (
            id, username, password_hash, grade, subject, is_admin
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (9999, 'admin', 'dev-only-hash', '管理员', '管理', 1),
    )
    connection.execute(
        """
        UPDATE users
        SET is_admin = 1
        WHERE id = ?
        """,
        (9999,),
    )


def _configured_admin_usernames() -> list[str]:
    raw_value = os.getenv('ADMIN_USERNAMES') or os.getenv('ADMIN_USERNAME') or ''
    usernames: list[str] = []
    seen: set[str] = set()

    for raw_username in raw_value.replace('，', ',').split(','):
        username = raw_username.strip()
        if not username or username in seen:
            continue
        usernames.append(username)
        seen.add(username)

    return usernames


def ensure_configured_admins(connection: sqlite3.Connection) -> None:
    for username in _configured_admin_usernames():
        connection.execute(
            """
            UPDATE users
            SET is_admin = 1
            WHERE username = ?
            """,
            (username,),
        )


def init_database() -> None:
    connection = get_connection()
    try:
        connection.executescript(DDL_SCRIPT)
        _run_migrations(connection)
        ensure_test_user(connection)
        ensure_test_admin(connection)
        ensure_configured_admins(connection)
        connection.commit()
    finally:
        connection.close()
