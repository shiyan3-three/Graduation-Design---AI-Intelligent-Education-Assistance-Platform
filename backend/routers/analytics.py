from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from backend.database import get_connection
from backend.dependencies.auth import get_current_user_id
from backend.models import (
    AnalyticsReportResponseData,
    AnalyticsSummaryResponseData,
    AnalyticsTagsResponseData,
    FocusAreaOut,
    TagCountOut,
    success_response,
)


router = APIRouter()


@router.get('/api/analytics/tags')
async def get_analytics_tags(
    user_id: int = Depends(get_current_user_id),
) -> JSONResponse:
    tag_counts = _fetch_tag_counts(user_id)
    response_data = AnalyticsTagsResponseData(
        items=[TagCountOut(tag=item['tag'], count=item['count']) for item in tag_counts],
    )
    return JSONResponse(status_code=200, content=success_response(response_data))


@router.get('/api/analytics/report')
async def get_analytics_report(
    user_id: int = Depends(get_current_user_id),
) -> JSONResponse:
    tag_counts = _fetch_tag_counts(user_id, limit=3)
    response_data = AnalyticsReportResponseData(
        focus_areas=[
            FocusAreaOut(tag=item['tag'], count=item['count'], rank=index + 1)
            for index, item in enumerate(tag_counts)
        ],
    )
    return JSONResponse(status_code=200, content=success_response(response_data))


@router.get('/api/analytics/summary')
async def get_analytics_summary(
    user_id: int = Depends(get_current_user_id),
) -> JSONResponse:
    with closing(get_connection()) as connection:
        total_study_days = _fetch_total_study_days(connection, user_id)
        streak_days = _compute_streak(connection, user_id)
        recommend_complete_rate = _compute_recommend_rate(connection, user_id)

    response_data = AnalyticsSummaryResponseData(
        total_study_days=total_study_days,
        streak_days=streak_days,
        recommend_complete_rate=recommend_complete_rate,
    )
    return JSONResponse(status_code=200, content=success_response(response_data))


def _fetch_total_study_days(connection: sqlite3.Connection, user_id: int) -> int:
    row = connection.execute(
        """
        SELECT COUNT(DISTINCT DATE(created_at)) AS days
        FROM sessions
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()
    return int(row['days']) if row is not None else 0


def _compute_streak(connection: sqlite3.Connection, user_id: int) -> int:
    rows = connection.execute(
        """
        SELECT DISTINCT DATE(created_at) AS study_date
        FROM sessions
        WHERE user_id = ?
        ORDER BY study_date DESC
        """,
        (user_id,),
    ).fetchall()
    if not rows:
        return 0

    today = date.today()
    latest_study_date = date.fromisoformat(str(rows[0]['study_date']))
    if latest_study_date not in (today, today - timedelta(days=1)):
        return 0

    streak = 1
    for index in range(1, len(rows)):
        previous_date = date.fromisoformat(str(rows[index - 1]['study_date']))
        current_date = date.fromisoformat(str(rows[index]['study_date']))
        if (previous_date - current_date).days != 1:
            break
        streak += 1
    return streak


def _compute_recommend_rate(connection: sqlite3.Connection, user_id: int) -> int | None:
    row = connection.execute(
        """
        SELECT
            COUNT(CASE WHEN status = 'completed' THEN 1 END) AS completed,
            COUNT(CASE WHEN status IN ('completed', 'skipped') THEN 1 END) AS total
        FROM recommendation_items
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()
    if row is None or int(row['total']) == 0:
        return None
    return round(int(row['completed']) / int(row['total']) * 100)


def _fetch_tag_counts(user_id: int, limit: int | None = None) -> list[dict[str, int | str]]:
    limit_clause = 'LIMIT ?' if limit is not None else ''
    params: tuple[int] | tuple[int, int]
    params = (user_id, limit) if limit is not None else (user_id,)
    with closing(get_connection()) as connection:
        rows = connection.execute(
            f"""
            SELECT mt.tag, COUNT(*) AS count
            FROM message_tags mt
            JOIN messages m ON mt.message_id = m.id
            JOIN sessions s ON m.session_id = s.id
            WHERE s.user_id = ?
            GROUP BY mt.tag
            ORDER BY count DESC, mt.tag ASC
            {limit_clause}
            """,
            params,
        ).fetchall()

    return [{'tag': str(row['tag']), 'count': int(row['count'])} for row in rows]
