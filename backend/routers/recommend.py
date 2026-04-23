from __future__ import annotations

import json
from contextlib import closing
from datetime import datetime, timezone
from json import JSONDecodeError
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from backend.database import get_connection
from backend.dependencies.auth import get_current_user_id
from backend.models import (
    FeedbackRequest,
    RecommendationItemOut,
    RecommendResponseData,
    success_response,
)
from backend.tools.question_tool import question_tool


router = APIRouter()


@router.get('/api/recommend')
def get_recommend(
    user_id: int = Depends(get_current_user_id),
) -> JSONResponse:
    pending_items = _fetch_pending_recommendations(user_id)
    if not pending_items:
        topics = _fetch_top_topics(user_id)
        if topics:
            _generate_recommendations(user_id, topics)
            pending_items = _fetch_pending_recommendations(user_id)

    response_data = RecommendResponseData(
        items=[_row_to_recommendation_item(item) for item in pending_items],
    )
    return JSONResponse(status_code=200, content=success_response(response_data))


@router.post('/api/recommend/feedback')
def post_recommend_feedback(
    payload: FeedbackRequest,
    user_id: int = Depends(get_current_user_id),
) -> JSONResponse:
    item = _fetch_recommendation_for_user(payload.id, user_id)
    if item is None:
        return _recommendation_not_found_response()
    if str(item['status']) == 'completed':
        return JSONResponse(
            status_code=409,
            content={
                'success': False,
                'message': '推荐题目已完成，无需重复反馈',
                'error_code': 'RECOMMENDATION_ALREADY_COMPLETED',
            },
        )

    feedback_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    updated_item = _update_recommendation_feedback(
        item_id=payload.id,
        user_id=user_id,
        status=payload.status,
        feedback_at=feedback_at,
    )
    if updated_item is None:
        return _recommendation_not_found_response()

    return JSONResponse(
        status_code=200,
        content=success_response(_row_to_recommendation_item(updated_item)),
    )


def _recommendation_not_found_response() -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            'success': False,
            'message': '推荐题目不存在',
            'error_code': 'RECOMMENDATION_NOT_FOUND',
        },
    )


def _fetch_top_topics(user_id: int, limit: int = 3) -> list[str]:
    with closing(get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT mt.tag, COUNT(*) AS count
            FROM message_tags mt
            JOIN messages m ON mt.message_id = m.id
            JOIN sessions s ON m.session_id = s.id
            WHERE s.user_id = ?
            GROUP BY mt.tag
            ORDER BY count DESC, mt.tag ASC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

    return [str(row['tag']) for row in rows]


def _fetch_recommendation_for_user(item_id: int, user_id: int) -> Any | None:
    with closing(get_connection()) as connection:
        return connection.execute(
            """
            SELECT id, recommended_topic, question_payload, source, status, created_at, feedback_at
            FROM recommendation_items
            WHERE id = ? AND user_id = ?
            """,
            (item_id, user_id),
        ).fetchone()


def _fetch_pending_recommendations(user_id: int) -> list[Any]:
    with closing(get_connection()) as connection:
        return connection.execute(
            """
            SELECT id, recommended_topic, question_payload, source, status, created_at, feedback_at
            FROM recommendation_items
            WHERE user_id = ? AND status = 'pending'
            ORDER BY id ASC
            """,
            (user_id,),
        ).fetchall()


def _update_recommendation_feedback(
    item_id: int,
    user_id: int,
    status: str,
    feedback_at: str,
) -> Any | None:
    with closing(get_connection()) as connection:
        connection.execute(
            """
            UPDATE recommendation_items
            SET status = ?, feedback_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (status, feedback_at, item_id, user_id),
        )
        connection.commit()
        return connection.execute(
            """
            SELECT id, recommended_topic, question_payload, source, status, created_at, feedback_at
            FROM recommendation_items
            WHERE id = ? AND user_id = ?
            """,
            (item_id, user_id),
        ).fetchone()


def _generate_recommendations(user_id: int, topics: list[str]) -> None:
    generated_items: list[tuple[int, str, str, str, str]] = []
    for topic in topics:
        payload_str = question_tool(topic)
        if payload_str.startswith('出题错误'):
            continue
        if not _is_valid_question_payload(payload_str):
            continue
        generated_items.append((user_id, topic, payload_str, 'question_tool', 'pending'))

    if not generated_items:
        return

    with closing(get_connection()) as connection:
        connection.executemany(
            """
            INSERT INTO recommendation_items (
                user_id, recommended_topic, question_payload, source, status
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            generated_items,
        )
        connection.commit()


def _is_valid_question_payload(payload_str: str) -> bool:
    try:
        return isinstance(json.loads(payload_str), dict)
    except (JSONDecodeError, TypeError):
        return False


def _row_to_recommendation_item(row: Any) -> RecommendationItemOut:
    return RecommendationItemOut(
        id=int(row['id']),
        recommended_topic=str(row['recommended_topic']),
        question_payload=json.loads(str(row['question_payload'])),
        source=str(row['source']),
        status=str(row['status']),
        created_at=str(row['created_at']),
        feedback_at=row['feedback_at'],
    )
