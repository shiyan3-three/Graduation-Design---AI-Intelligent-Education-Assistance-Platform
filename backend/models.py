from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, model_serializer


class ChatRequest(BaseModel):
    session_id: Optional[int] = None
    content: str
    tool_preference: Optional[str] = None


class RegisterRequest(BaseModel):
    username: str
    password: str
    grade: str
    subject: str


class LoginRequest(BaseModel):
    username: str
    password: str


class FeedbackRequest(BaseModel):
    id: int
    status: Literal['completed', 'skipped']


class ToolSuggestion(BaseModel):
    tool_name: str
    recommended_prompt: str


class UserOut(BaseModel):
    id: int
    username: str
    grade: str
    subject: str
    created_at: str
    is_admin: bool = False


class AdminUserOut(UserOut):
    pass


class AdminUsersResponseData(BaseModel):
    items: List[AdminUserOut]


class AdminStatsResponseData(BaseModel):
    total_users: int
    total_sessions: int
    total_messages: int
    total_recommendations: int


class QuestionOut(BaseModel):
    id: int
    subject: str
    topic: str
    question: str
    options: str
    answer: str
    source: str


class AdminQuestionsResponseData(BaseModel):
    items: List[QuestionOut]


class CreateQuestionRequest(BaseModel):
    subject: str
    topic: str
    question: str
    options: str
    answer: str
    source: str = 'manual'


class UpdateQuestionRequest(BaseModel):
    question: Optional[str] = None
    options: Optional[str] = None
    answer: Optional[str] = None
    topic: Optional[str] = None
    subject: Optional[str] = None


class SessionOut(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: str
    updated_at: str


class MessageOut(BaseModel):
    id: int
    session_id: int
    sequence_no: int
    role: str
    content: str
    tools_used: Optional[List[Dict[str, Any]]] = None
    tool_suggestion: Optional[ToolSuggestion] = None
    created_at: str

    @model_serializer(mode='wrap')
    def serialize_model(self, handler):
        payload = handler(self)
        if payload.get('tool_suggestion') is None:
            payload.pop('tool_suggestion', None)
        return payload


class ChatResponseData(BaseModel):
    session: SessionOut
    user_message: MessageOut
    assistant_message: MessageOut


class LoginResponseData(BaseModel):
    token: str
    token_type: str
    expires_in: int
    user: UserOut


class TagCountOut(BaseModel):
    tag: str
    count: int


class AnalyticsTagsResponseData(BaseModel):
    items: List[TagCountOut]


class FocusAreaOut(BaseModel):
    tag: str
    count: int
    rank: int


class AnalyticsReportResponseData(BaseModel):
    focus_areas: List[FocusAreaOut]


class AnalyticsSummaryResponseData(BaseModel):
    total_study_days: int
    streak_days: int
    recommend_complete_rate: Optional[int] = None


class RecommendationItemOut(BaseModel):
    id: int
    recommended_topic: str
    question_payload: Dict[str, Any]
    source: str
    status: str
    created_at: str
    feedback_at: Optional[str] = None


class RecommendResponseData(BaseModel):
    items: List[RecommendationItemOut]


class RecommendResponse(BaseModel):
    success: bool
    message: str
    data: RecommendResponseData


class SessionListResponseData(BaseModel):
    items: List[SessionOut]


class SessionDetailResponseData(BaseModel):
    session: SessionOut
    messages: List[MessageOut]


def success_response(data: Any, message: str = 'ok') -> Dict[str, Any]:
    if isinstance(data, BaseModel):
        serialized_data: Any = data.model_dump(mode='json')
    else:
        serialized_data = data

    return {
        'success': True,
        'message': message,
        'data': serialized_data,
    }


def error_response(
    message: str, error_code: str, details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        'success': False,
        'message': message,
        'error_code': error_code,
    }
    if details:
        payload['details'] = details
    return payload
