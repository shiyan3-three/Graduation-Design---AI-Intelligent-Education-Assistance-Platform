# Backlog

> 维护责任：`Leader Agent`
> 
> 说明：本文件保存全项目待办任务与优先级。只保留可执行任务，不把讨论过程写在这里。

<!-- 按优先级排列，完成后用 [x] 标记 -->
<!-- 每个任务应足够小，一轮内可以完成 -->
- [x] D-1 数据库设计初稿
- [x] D-2 API 设计初稿
- [x] D-3 数据库与接口对应关系检查（Review Agent 在 D-2 审查中已确认全部对齐）
- [x] B2-1 后端最简 `/api/chat` 接口
- [x] B2-2 后端 `/api/sessions` 与会话消息基础接口
- [x] F2-1 前端最简对话页发送与展示
- [x] F2-2 前后端 chat 联调与字段对齐（代码已在 F2-1 中完成，Review 验证通过，随 F2-1 收口）
- [x] F2-侧栏 对话历史侧栏的最小占位或基础列表（Review 通过，人类浏览器验证通过）
- [x] B3-1 后端接入 `calculator_tool`（预备阶段：直接函数调用，验证工具主链路）（Review 通过，2026-04-14）
- [x] B3-2 后端接入 `knowledge_tool`（预备阶段：百度搜索 API 集成）（Review 通过，2026-04-15）
- [x] F2-3 前端工具调用状态最小展示（Review 通过，2026-04-15）
- [x] B3-3 明确 `question_tool` 输入输出与降级策略边界（Review 通过，2026-04-17）
- [x] M4-1 建立最小 MCP Server 骨架 + calculator_tool MCP 封装（Review 通过，2026-04-17）
- [x] M4-2 将 knowledge_tool 和 question_tool 包装为 MCP 工具 + 全部调用路径切换（Review 通过，2026-04-17）
- [x] FR-1 前端 React 重构：Vite + React 重建项目（Review 通过，2026-04-18）
- [x] B1 后端用户注册与登录接口（Review 通过，2026-04-19）
- [x] F1 前端登录注册页 + 路由配置（Review 通过，2026-04-19）
- [x] FH-1 前端首页 Dashboard（Review 通过，2026-04-19）
- [x] B4 后端学习分析（标签打标 + 分析接口，合并原 B4-1/2/3）（Review 通过，2026-04-21）
- [x] F3-1 前端学习记录页与基础统计展示（Review 通过，2026-04-21）
- [x] B5-1 后端推荐接口（Review 通过，2026-04-21）
- [x] B5-2 后端推荐反馈接口（Review 通过，2026-04-21）
- [x] F4-1 前端推荐题目页（Review 通过，2026-04-21）
- [x] B-Auth JWT 鉴权（已在 B1/B4/B5 中完整落地，2026-04-21 确认关闭）
- [x] B2-增强 后端 Chat 流式输出（SSE）（Review 通过，2026-04-22）
- [x] F2-增强 前端流式消费与 UX 优化（Review 通过，2026-04-22）
- [x] B-Analytics-增强 后端学习汇总统计接口（Review 通过，2026-04-22）
- [x] FH-增强 Dashboard 接入真实后端数据（Review 通过，2026-04-22）
- [x] B-Admin 后端管理员模块基础版（Review 通过，2026-04-23）
- [x] B-Admin-2 + F-Admin 题库 CRUD 后端 + 前端管理员面板（Review 通过，2026-04-23）★ 项目全部完成

## 使用规则

- 当前正在执行的任务，必须同时出现在 `current/task.md`
- 只有 `Leader Agent` 负责勾选、重排优先级、拆分或新增任务
- 如果 review 发现需要返工，优先由 `Leader Agent` 判断是回到当前任务，还是新增修复任务
