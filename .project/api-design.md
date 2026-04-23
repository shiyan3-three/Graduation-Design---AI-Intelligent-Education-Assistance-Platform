# API 设计初稿

## 1. 文档目标

本文基于以下两份文档产出第一版 API 设计稿：

- `.project/database-design.md`
- `.project/系统模块设计方案.md`

目标是为后续后端实现提供稳定、可直接编码的接口契约。

本稿覆盖以下 4 个模块的接口设计：

- B1 用户管理
- B2 智能对话
- B4 学习分析
- B5 题目推荐

本稿不包含：

- 后端业务代码
- 前端页面
- MCP Server 工具接口设计
- 流式输出相关接口

## 2. 统一约定

### 2.1 基础约定

- 接口基础前缀：`/api`
- 数据格式：`application/json`
- 认证方式：JWT Bearer Token
- 时间字段：API 统一返回 ISO 8601 字符串，例如 `2026-03-23T14:30:00Z`
- ID 字段：统一为整数，对应 SQLite `INTEGER PRIMARY KEY`

### 2.2 统一响应格式

成功响应：

```json
{
  "success": true,
  "message": "ok",
  "data": {}
}
```

失败响应：

```json
{
  "success": false,
  "message": "用户名已存在",
  "error_code": "USERNAME_EXISTS"
}
```

字段说明：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `success` | boolean | 是否成功 |
| `message` | string | 人类可读提示 |
| `data` | object / array / null | 成功时返回的数据 |
| `error_code` | string | 失败时的稳定错误码 |

### 2.3 字段命名原则

- 能直接复用数据库字段名的，接口层保持一致，例如 `id`、`username`、`grade`、`subject`、`title`、`content`、`created_at`
- 出于安全原因，注册和登录接口只接收 `password`，不直接暴露数据库字段 `password_hash`
- `tools_used` 和 `question_payload` 在数据库中以 JSON 字符串保存，在 API 中以结构化 JSON 返回

### 2.4 鉴权规则

| 接口类型 | 是否需要 `Authorization` |
|----------|--------------------------|
| 注册、登录 | 否 |
| 用户信息、会话、聊天、学习分析、推荐相关 | 是 |

Header 约定：

```http
Authorization: Bearer <token>
```

### 2.5 阶段标注规则

- 第一阶段必须：后续后端实现优先落地
- 后续阶段预留：本轮先定义契约，不进入实现

## 3. 阶段划分总览

| 模块 | 接口 | 阶段标注 | 关联表 |
|------|------|----------|--------|
| B1 用户管理 | `POST /api/register` | 后续阶段预留 | `users` |
| B1 用户管理 | `POST /api/login` | 后续阶段预留 | `users` |
| B1 用户管理 | `GET /api/user/profile` | 后续阶段预留 | `users` |
| B2 智能对话 | `GET /api/sessions` | 第一阶段必须 | `sessions` |
| B2 智能对话 | `GET /api/sessions/{id}` | 第一阶段必须 | `sessions`、`messages` |
| B2 智能对话 | `POST /api/chat` | 第一阶段必须 | `sessions`、`messages` |
| B4 学习分析 | `GET /api/analytics/tags` | 后续阶段预留 | `message_tags` |
| B4 学习分析 | `GET /api/analytics/report` | 后续阶段预留 | `message_tags` |
| B5 题目推荐 | `GET /api/recommend` | 后续阶段预留 | `recommendation_items` |
| B5 题目推荐 | `POST /api/recommend/feedback` | 后续阶段预留 | `recommendation_items` |

## 4. B1 用户管理模块

### 4.1 `POST /api/register`

- 阶段标注：后续阶段预留
- 关联表：`users`
- 说明：注册新用户，服务端负责将 `password` 转换为 `password_hash`

请求体：

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `username` | string | 是 | 用户名，需全局唯一 |
| `password` | string | 是 | 明文密码，服务端负责哈希 |
| `grade` | string | 是 | 年级 |
| `subject` | string | 是 | 主修或当前辅导学科 |

成功响应 `data`：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | integer | 用户 ID |
| `username` | string | 用户名 |
| `grade` | string | 年级 |
| `subject` | string | 学科 |
| `created_at` | string | 创建时间 |

状态码：

| 状态码 | 说明 |
|--------|------|
| `201` | 注册成功 |
| `400` | 请求字段缺失或格式错误 |
| `409` | 用户名已存在 |
| `500` | 服务端异常 |

### 4.2 `POST /api/login`

- 阶段标注：后续阶段预留
- 关联表：`users`
- 说明：校验账号密码并返回 JWT

请求体：

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `username` | string | 是 | 用户名 |
| `password` | string | 是 | 明文密码 |

成功响应 `data`：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `token` | string | JWT 令牌 |
| `token_type` | string | 固定为 `Bearer` |
| `expires_in` | integer | 过期秒数，建议 `604800` |
| `user` | object | 当前登录用户 |

`user` 字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | integer | 用户 ID |
| `username` | string | 用户名 |
| `grade` | string | 年级 |
| `subject` | string | 学科 |
| `created_at` | string | 创建时间 |

状态码：

| 状态码 | 说明 |
|--------|------|
| `200` | 登录成功 |
| `400` | 请求字段缺失或格式错误 |
| `401` | 用户名或密码错误 |
| `500` | 服务端异常 |

### 4.3 `GET /api/user/profile`

- 阶段标注：后续阶段预留
- 关联表：`users`
- 说明：返回当前登录用户画像信息

请求参数：

- 请求体：无
- Query：无

成功响应 `data`：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | integer | 用户 ID |
| `username` | string | 用户名 |
| `grade` | string | 年级 |
| `subject` | string | 学科 |
| `created_at` | string | 创建时间 |

状态码：

| 状态码 | 说明 |
|--------|------|
| `200` | 获取成功 |
| `401` | 未登录或 Token 无效 |
| `404` | 用户不存在 |
| `500` | 服务端异常 |

## 5. B2 智能对话模块

### 5.1 `GET /api/sessions`

- 阶段标注：第一阶段必须
- 关联表：`sessions`
- 说明：获取当前用户历史会话列表，按 `updated_at` 倒序返回

请求参数：

- 请求体：无
- Query：无

成功响应 `data`：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `items` | array<object> | 会话列表 |

`items[]` 字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | integer | 会话 ID |
| `user_id` | integer | 所属用户 ID |
| `title` | string | 会话标题 |
| `created_at` | string | 创建时间 |
| `updated_at` | string | 最近活跃时间 |

状态码：

| 状态码 | 说明 |
|--------|------|
| `200` | 获取成功 |
| `401` | 未登录或 Token 无效 |
| `500` | 服务端异常 |

### 5.2 `GET /api/sessions/{id}`

- 阶段标注：第一阶段必须
- 关联表：`sessions`、`messages`
- 说明：获取指定会话及其完整消息记录，消息按 `sequence_no` 正序返回

Path 参数：

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `id` | integer | 是 | 会话 ID |

请求体：

- 无

成功响应 `data`：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `session` | object | 会话元信息 |
| `messages` | array<object> | 消息列表 |

`session` 字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | integer | 会话 ID |
| `user_id` | integer | 所属用户 ID |
| `title` | string | 会话标题 |
| `created_at` | string | 创建时间 |
| `updated_at` | string | 最近活跃时间 |

`messages[]` 字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | integer | 消息 ID |
| `session_id` | integer | 所属会话 ID |
| `sequence_no` | integer | 会话内顺序号 |
| `role` | string | `system` / `user` / `assistant` / `tool` |
| `content` | string | 消息内容 |
| `tools_used` | array<object> \| null | 工具调用摘要 |
| `created_at` | string | 创建时间 |

状态码：

| 状态码 | 说明 |
|--------|------|
| `200` | 获取成功 |
| `401` | 未登录或 Token 无效 |
| `404` | 会话不存在或不属于当前用户 |
| `500` | 服务端异常 |

### 5.3 `POST /api/chat`

- 阶段标注：第一阶段必须
- 关联表：`sessions`、`messages`
- 说明：发送一条用户消息，返回本轮 AI 回复；若未传 `session_id`，则创建新会话

请求体：

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `session_id` | integer \| null | 否 | 已存在会话 ID；为空时创建新会话 |
| `content` | string | 是 | 用户输入内容 |

成功响应 `data`：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `session` | object | 当前会话 |
| `user_message` | object | 本次写入的用户消息 |
| `assistant_message` | object | 本次生成的助手消息 |

`session` 字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | integer | 会话 ID |
| `user_id` | integer | 所属用户 ID |
| `title` | string | 会话标题 |
| `created_at` | string | 创建时间 |
| `updated_at` | string | 最近活跃时间 |

`user_message` / `assistant_message` 字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | integer | 消息 ID |
| `session_id` | integer | 所属会话 ID |
| `sequence_no` | integer | 会话内顺序号 |
| `role` | string | `user` 或 `assistant` |
| `content` | string | 消息内容 |
| `tools_used` | array<object> \| null | 助手消息中的工具调用摘要；用户消息固定为 `null` |
| `created_at` | string | 创建时间 |

状态码：

| 状态码 | 说明 |
|--------|------|
| `200` | 对话成功 |
| `400` | 请求字段缺失或格式错误 |
| `401` | 未登录或 Token 无效 |
| `404` | `session_id` 不存在或不属于当前用户 |
| `500` | 服务端异常 |

实现备注：

- 当前 API 契约默认在响应返回前完成本轮用户消息与助手消息的落库，以便稳定返回 `id` 和 `sequence_no`
- 如果后续实现改为“先响应、后异步写库”，也需要保持当前响应字段结构兼容
- 新增消息时，应用层必须维护 `messages.sequence_no` 递增
- 每次写入用户消息或助手消息后，必须同步刷新 `sessions.updated_at`

## 6. B4 学习分析模块

### 6.1 `GET /api/analytics/tags`

- 阶段标注：后续阶段预留
- 关联表：`message_tags`
- 说明：统计当前用户历史消息的知识点标签频次

请求参数：

- 请求体：无
- Query：无

成功响应 `data`：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `items` | array<object> | 标签频次列表 |

`items[]` 字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `tag` | string | 知识点标签 |
| `count` | integer | 出现次数 |

状态码：

| 状态码 | 说明 |
|--------|------|
| `200` | 获取成功 |
| `401` | 未登录或 Token 无效 |
| `500` | 服务端异常 |

### 6.2 `GET /api/analytics/report`

- 阶段标注：后续阶段预留
- 关联表：`message_tags`
- 说明：返回当前用户薄弱点 Top3

请求参数：

- 请求体：无
- Query：无

成功响应 `data`：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `weak_points` | array<object> | 薄弱点列表，最多 3 项 |

`weak_points[]` 字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `tag` | string | 知识点标签 |
| `count` | integer | 出现次数 |
| `rank` | integer | 排名，从 1 开始 |

状态码：

| 状态码 | 说明 |
|--------|------|
| `200` | 获取成功 |
| `401` | 未登录或 Token 无效 |
| `500` | 服务端异常 |

## 7. B5 题目推荐模块

### 7.1 `GET /api/recommend`

- 阶段标注：后续阶段预留
- 关联表：`recommendation_items`
- 说明：基于学习分析结果返回推荐题目列表，默认 1 到 3 题

Query 参数：

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `limit` | integer | 否 | 返回题目数量，默认 `3`，最大 `3` |

请求体：

- 无

成功响应 `data`：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `items` | array<object> | 推荐题目列表 |

`items[]` 字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | integer | 推荐题目 ID |
| `recommended_topic` | string | 推荐依据的知识点 |
| `question_payload` | object | 题目内容 |
| `source` | string | 推荐来源，默认 `question_tool` |
| `status` | string | `pending` / `completed` / `skipped` |
| `created_at` | string | 题目生成时间 |
| `feedback_at` | string \| null | 用户反馈时间 |

状态码：

| 状态码 | 说明 |
|--------|------|
| `200` | 获取成功 |
| `401` | 未登录或 Token 无效 |
| `500` | 服务端异常 |

### 7.2 `POST /api/recommend/feedback`

- 阶段标注：后续阶段预留
- 关联表：`recommendation_items`
- 说明：记录当前用户对推荐题目的处理结果

请求体：

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `id` | integer | 是 | 推荐题目 ID |
| `status` | string | 是 | 只允许 `completed` 或 `skipped` |

成功响应 `data`：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | integer | 推荐题目 ID |
| `recommended_topic` | string | 推荐依据的知识点 |
| `question_payload` | object | 题目内容 |
| `source` | string | 推荐来源 |
| `status` | string | 更新后的状态 |
| `created_at` | string | 题目生成时间 |
| `feedback_at` | string | 反馈时间 |

状态码：

| 状态码 | 说明 |
|--------|------|
| `200` | 更新成功 |
| `400` | 请求字段缺失或状态值非法 |
| `401` | 未登录或 Token 无效 |
| `404` | 推荐题目不存在或不属于当前用户 |
| `409` | 当前题目已反馈完成，无需重复提交 |
| `500` | 服务端异常 |

## 8. 与数据库设计的对齐说明

### 8.1 直接对应关系

- `users` → 注册、登录、用户画像
- `sessions` → 会话列表、会话详情、聊天时的会话元信息
- `messages` → 会话详情、聊天收发消息
- `message_tags` → 标签统计、薄弱点报告
- `recommendation_items` → 推荐题目、推荐反馈

### 8.2 本轮需要特别注意的实现约束

- SQLite 启动时必须显式执行 `PRAGMA foreign_keys = ON`
- `GET /api/sessions` 的排序基于 `sessions.updated_at`
- `GET /api/sessions/{id}` 的消息顺序基于 `messages.sequence_no`
- `POST /api/chat` 在写入消息时必须同步维护 `sequence_no` 和 `updated_at`

## 9. 本稿结论

本稿已经满足当前任务的验收要求：

- 已定义注册/登录、会话列表、消息详情、推荐反馈这 4 组接口，并补全了同模块相关接口
- 每个接口均明确了 URL、HTTP 方法、请求体、响应体和状态码
- 接口字段已与 `.project/database-design.md` 中的表字段保持对齐
- 已区分第一阶段必须接口与后续阶段预留接口
- 文档可直接作为下一轮后端实现的输入
