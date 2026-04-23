# .workflow 使用说明

## 一、这是什么

`.workflow/` 是本项目给 LLM / Agent 使用的协作工作区。

它的目标不是记录所有过程，而是帮助多个 AI 在长期协作中做到：

- 不丢当前任务
- 不丢项目状态
- 不丢关键历史
- 不乱改范围

本工作流采用两条主线：

1. **最小任务闭环**
2. **双层历史记忆**

---

## 二、核心原则

### 1. 一次只做一个任务

任何时候，当前正在执行的任务只看 `current/task.md`。

不要同时推进多个任务。  
不要跨阶段顺手扩展。

### 2. 验收优先于自述

任务是否完成，不看“Agent 觉得差不多了”，而看：

- `current/acceptance.md`

这是当前任务的第一锚点。

### 3. 历史分层

历史分两类：

- `history-full/`：给人看，保留完整细节
- `history-ai/`：给 AI 看，保留压缩交接信息

默认不要优先读取 `history-full/`。  
AI 默认优先读 `history-ai/`。

### 4. 先设计，再开发

项目推进顺序遵循：

1. 数据库设计
2. API 设计
3. 后端实现
4. 前端接入
5. 联调
6. 工具逻辑实现
7. MCP Server 正式接入

---

## 三、目录说明

### `current/`

当前执行层。  
只描述“这一轮到底在做什么”。

包含：

- `task.md`：当前唯一任务
- `acceptance.md`：当前任务验收标准
- `context.md`：当前任务的补充背景

### `project/`

项目状态层。  
描述项目整体进度、路线、决策和风险。

包含：

- `status.md`：当前项目快照
- `next.md`：backlog / 后续任务列表
- `roadmap.md`：整体阶段路线
- `decisions.md`：重要决策
- `open-issues.md`：未解决问题与风险

### `history-full/`

完整历史。  
给人看，记录完整过程，按 `YYYY/MM/DD.md` 组织。

### `history-ai/`

压缩历史。  
给 AI 看，记录高价值交接信息，按 `YYYY/MM/DD.md` 组织。

### `review/`

Review Agent 的审查结果。  
按 `YYYY/MM/DD.md` 组织。

### `prompts/`

各 Agent 的启动提示词。  
只有在需要指定角色时才使用。

包含：

- `leader-agent-prompt.md`
- `coding-agent-prompt.md`
- `review-agent-prompt.md`
- `doc-agent-prompt.md`

---

## 四、默认读取顺序

如果你是一个新进入项目的 LLM，又没有被明确指定角色，默认按这个顺序读取：

1. `current/task.md`
2. `current/acceptance.md`
3. `current/context.md`
4. `project/status.md`
5. `project/roadmap.md`
6. `project/next.md`
7. `project/decisions.md`
8. `project/open-issues.md`
9. `history-ai/` 最近 2 到 3 篇
10. 最新 `review/`

目的：

- 先明确当前任务
- 再明确验收标准
- 再明确项目所处阶段
- 最后补长期上下文

---

## 五、不同 Agent 的读取顺序

### Leader Agent

按以下顺序读取：

1. `project/status.md`
2. `project/roadmap.md`
3. `project/next.md`
4. `project/decisions.md`
5. `project/open-issues.md`
6. `current/task.md`
7. `current/acceptance.md`
8. 最新 `review/`
9. `history-ai/` 最近 2 到 3 篇

Leader Agent 目标：

- 掌握全局情况
- 决定下一步行动
- 选择当前任务
- 确定完成标准

### Coding Agent

按以下顺序读取：

1. `current/task.md`
2. `current/acceptance.md`
3. `current/context.md`
4. `project/status.md`
5. `project/roadmap.md`
6. `project/decisions.md`
7. `project/open-issues.md`
8. `history-ai/` 最近 2 到 3 篇
9. 最新 `review/`

Coding Agent 目标：

- 完成当前任务
- 不超范围
- 改完后说明改动

### Review Agent

按以下顺序读取：

1. `current/acceptance.md`
2. `current/task.md`
3. `current/context.md`
4. 本轮实际改动文件或 diff
5. 人类运行反馈
6. `project/open-issues.md`
7. 相关 `history-ai/`
8. `project/status.md`

Review Agent 目标：

- 先判断是否满足验收标准
- 再查明显 bug 和基础运行风险

### Doc Agent

按以下顺序读取：

1. 新增的 `history-full/`
2. `project/status.md`
3. `project/decisions.md`
4. `project/open-issues.md`
5. 输出到 `history-ai/`

Doc Agent 目标：

- 压缩历史
- 帮助下一个 Agent 快速接手

---

## 六、不同 Agent 应更新什么

### Coding Agent 负责更新

- 代码
- `history-full/YYYY/MM/DD.md`

### Leader Agent 负责更新

- `current/task.md`
- `current/acceptance.md`
- `current/context.md`
- `project/status.md`
- `project/next.md`
- `project/roadmap.md`
- `project/decisions.md`
- `project/open-issues.md`

### Review Agent 负责更新

- `review/YYYY/MM/DD.md`

### Doc Agent 负责更新

- `history-ai/YYYY/MM/DD.md`

---

## 七、什么时候看哪一层历史

### 默认情况

优先看：

- `history-ai/`

因为它更短，更适合 AI 继承上下文。

### 需要追细节时

再看：

- `history-full/`

适合以下情况：

- 要追查为什么这样设计
- 要还原某次失败尝试
- 要看当天完整工作记录

---

## 八、当前项目的执行顺序

当前项目应按照以下思路推进：

1. 基础设计阶段
2. 智能对话后端主链路
3. 智能对话前端接入与联调
4. 工具能力实现与验证
5. MCP Server 正式接入
6. 用户体系
7. 学习记录与分析
8. 题目推荐
9. 流式输出与体验增强

阶段细节以：

- `project/roadmap.md`

为准。

当前任务以：

- `current/task.md`

为准。

---

## 九、如果你是 LLM，现在应该怎么做

### 情况 1：你要开始实现任务

先读：

- `current/task.md`
- `current/acceptance.md`
- `project/status.md`
- `project/roadmap.md`

然后明确：

- 当前任务是什么
- 什么叫完成
- 当前处于哪个阶段

### 情况 1.5：你要决定下一步该做什么

先读：

- `project/status.md`
- `project/roadmap.md`
- `project/next.md`
- 最新 `review/`
- `history-ai/` 最近几篇

此时应以 Leader Agent 角色工作。

### 情况 2：你要做代码审查

先读：

- `current/acceptance.md`
- `current/task.md`
- 本轮改动
- 人类运行反馈

### 情况 3：你要接手别人的工作

先读：

- `project/status.md`
- `history-ai/` 最近 2 到 3 篇
- 最新 `review/`

---

## 十、不要做什么

- 不要跳过 `acceptance.md`
- 不要直接从 `history-full/` 开始读
- 不要一次做多个任务
- 不要跨阶段提前实现后续模块
- 不要在没有更新状态的情况下自行切换任务
- 不要把“能写代码”误当成“已完成任务”

---

## 十一、一句话总结

如果你不知道先看什么，就先看：

1. `current/task.md`
2. `current/acceptance.md`
3. `project/status.md`
4. `project/roadmap.md`
5. `history-ai/` 最近几篇

先搞清楚“现在做什么”和“做到什么算完成”，再开始工作。
