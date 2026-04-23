from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.database import init_database
from backend.models import error_response
from backend.routers.admin import router as admin_router
from backend.routers.analytics import router as analytics_router
from backend.routers.auth import router as auth_router
from backend.routers.chat import router as chat_router
from backend.routers.recommend import router as recommend_router
from backend.routers.sessions import router as sessions_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(
    title='AI Intelligent Education Tutor Backend',
    version='0.1.0',
    lifespan=lifespan,
)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(sessions_router)
app.include_router(analytics_router)
app.include_router(recommend_router)
app.include_router(admin_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=error_response(
            message='请求字段缺失或格式错误',
            error_code='INVALID_REQUEST',
            details={'errors': exc.errors()},
        ),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    """
    Convert FastAPI HTTPException into the project's unified error envelope
    { success, message, error_code } so clients never see the raw { detail } form.
    """
    if exc.status_code == 401:
        return JSONResponse(
            status_code=401,
            content=error_response(
                message='未登录或登录已失效',
                error_code='UNAUTHORIZED',
            ),
        )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            message=str(exc.detail),
            error_code='HTTP_ERROR',
        ),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=error_response(
            message='服务端异常',
            error_code='INTERNAL_ERROR',
            details={'error': str(exc)},
        ),
    )


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('backend.main:app', host='127.0.0.1', port=8000, reload=False)
