# Backend

最小可运行的 FastAPI 后端骨架，用于当前阶段的 `/api/chat` 主链路验证。

## 目录结构

```text
backend/
├── main.py
├── database.py
├── models.py
├── routers/
│   └── chat.py
├── services/
│   └── llm.py
├── requirements.txt
└── README.md
```

## 环境要求

- Python 3.13+
- 使用 `requirements.txt` 安装依赖

## 安装依赖

```bash
python -m pip install -r backend/requirements.txt
```

## 可选环境变量

```bash
set LLM_API_KEY=your_key
set LLM_BASE_URL=https://api.openai.com/v1
set LLM_MODEL=gpt-4o-mini
```

兼容读取以下变量名：

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL`

如果没有配置模型环境变量，服务会自动降级到本地 Mock 回复，便于先验证数据库和接口主链路。

## 启动服务

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## 请求示例

```bash
curl -X POST http://127.0.0.1:8000/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"content\":\"你好\"}"
```

追加到已有会话：

```bash
curl -X POST http://127.0.0.1:8000/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"session_id\":1,\"content\":\"继续讲一下\"}"
```

## 当前实现说明

- 启动时自动初始化 SQLite 数据库并执行 `PRAGMA foreign_keys = ON`
- 自动创建硬编码测试用户 `user_id = 1`
- `session_id` 为空时自动创建新会话，标题取用户首条消息前 20 个字符
- `messages.sequence_no` 由应用层递增维护
- 每次写入消息后同步刷新 `sessions.updated_at`
- 当前阶段不做鉴权、工具调用、流式输出
