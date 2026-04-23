# prompts 使用说明

本目录保存各角色的启动提示词。

如果你要让一个新的 LLM 进入项目，不要直接口头描述角色，优先复制对应 prompt 使用。

---

## 1. `leader-agent-prompt.md`

适用场景：

- 需要掌握全局情况
- 需要决定下一步行动
- 需要选择当前任务
- 需要定义或修改完成标准
- 需要在任务结束后判断是否切换到下一任务

一句话理解：

`Leader Agent` 是项目指挥层。

---

## 2. `coding-agent-prompt.md`

适用场景：

- 需要产出数据库设计
- 需要产出 API 设计
- 需要写后端代码
- 需要修复后端 review 指出的问题

一句话理解：

`Coding Agent` 只负责后端实现，不负责拍板项目方向。

---

## 2b. `coding-frontend-agent-prompt.md`

适用场景：

- 需要写前端代码（React 页面、组件、样式、路由）
- 需要修复前端 review 指出的问题
- Leader 下达的是 F 系列任务（如 F3-1、FH-1）

关键差异（与 `coding-agent-prompt.md` 相比）：

- 工作日志写入 `history-full/YYYY/MM/DD-frontend.md`，**不覆盖后端日志 `DD.md`**
- 会读取 `frontend/reflection/` 中的 HTML 设计原型作为视觉参考
- 不修改任何 `backend/` 目录下的文件

一句话理解：

`Coding Frontend Agent` 只负责前端实现，日志与后端 Agent 严格隔离。

---

## 3. `review-agent-prompt.md`

适用场景：

- 当前任务看起来已经做完
- 需要检查是否真的满足 `acceptance.md`
- 需要发现明显 bug、遗漏、范围漂移
- 需要给出阻塞问题和收口建议

一句话理解：

`Review Agent` 只负责审查，不负责实现。

---

## 4. `doc-agent-prompt.md`

适用场景：

- 需要把 `history-full/` 压成 `history-ai/`
- 准备交接给下一个 Agent
- 项目阶段切换，需要整理背景
- 历史已经变长，不适合让下一个 Agent 直接读全部细节

一句话理解：

`Doc Agent` 只负责压缩历史，不负责主导任务。

---

## 推荐启动顺序

### 情况 1：项目刚开始或要决定下一步

先用：

- `leader-agent-prompt.md`

### 情况 2：已经确定当前任务，要产出内容

再用：

- 后端任务（B 系列）：`coding-agent-prompt.md`
- 前端任务（F 系列）：`coding-frontend-agent-prompt.md`

### 情况 3：任务看起来完成了，要复审

然后用：

- `review-agent-prompt.md`

### 情况 4：需要整理历史给下一个 Agent

最后按需用：

- `doc-agent-prompt.md`

---

## 最常用组合

### 组合 A：正常推进一轮后端任务

1. `Leader Agent`
2. `Coding Agent`（后端）
3. 你做基础运行验证
4. `Review Agent`
5. `Leader Agent` 收口

### 组合 A2：正常推进一轮前端任务

1. `Leader Agent`
2. `Coding Frontend Agent`（告知使用哪个 `frontend/reflection/` 原型文件）
3. 你做浏览器验证
4. `Review Agent`
5. `Leader Agent` 收口

### 组合 B：只修一个 review 问题

- 后端问题：`Coding Agent`
- 前端问题：`Coding Frontend Agent`

然后：
1. 你做基础运行验证
2. `Review Agent`

### 组合 C：准备切换对话或交接

1. `Doc Agent`
2. `Leader Agent`

