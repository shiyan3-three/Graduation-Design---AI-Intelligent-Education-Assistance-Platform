# 多 Agent 配合工作流

## 一、设计目标

这套工作流用于支持以下协作方式：

- AI 主要负责代码实现
- 你主要负责基础运行验证
- 多个 AI 需要长期协作，不能频繁丢上下文
- 项目推进方式以“最小任务闭环”为核心

这套设计同时解决两个问题：

1. 如何让 AI 一次只做一个明确任务，避免发散
2. 如何让多个 AI 在长期协作中持续继承上下文

因此，本工作流采用两条主线同时运行：

- **执行主线**：围绕当前最小任务快速闭环
- **历史主线**：围绕项目长期上下文持续沉淀

---

## 二、核心原则

### 1. 最小任务优先

任何时候，系统中只能有一个“当前任务”作为主执行目标。

当前任务必须满足：

- 范围足够小
- 一轮内有机会做完
- 能写出明确验收标准
- 做完后能立即运行验证

### 2. 历史分层

历史不能只有一种。

本工作流把历史分成两层：

- **完整历史**：给你看，保留当天工作细节
- **压缩历史**：给 AI 看，只保留交接必需信息

### 3. 人看和 AI 看分开

给人看的历史可以更完整、更细。

给 AI 看的历史必须：

- 短
- 结构化
- 可快速读取
- 只保留高价值上下文

### 4. 验收优先于自述

Agent 说“已经完成”不算完成。  
是否完成，首先看 `acceptance.md`。

---

## 三、目录结构

```text
.workflow/
├── current/
│   ├── task.md
│   ├── acceptance.md
│   └── context.md
├── project/
│   ├── status.md
│   ├── next.md
│   ├── decisions.md
│   └── open-issues.md
├── history-full/
│   └── 2026/
│       └── 03/
│           ├── 17.md
│           └── 18.md
├── history-ai/
│   └── 2026/
│       └── 03/
│           ├── 17.md
│           └── 18.md
├── review/
│   └── 2026/
│       └── 03/
│           ├── 17.md
│           └── 18.md
└── prompts/
    ├── leader-agent-prompt.md
    ├── coding-agent-prompt.md
    ├── review-agent-prompt.md
    └── doc-agent-prompt.md
```

---

## 四、三层信息结构

### 第一层：当前执行层

目录：`.workflow/current/`

作用：

- 只描述“现在这一轮正在做什么”
- 给 Coding Agent 和 Review Agent 提供当前任务上下文
- 防止任务边界发散

包含文件：

- `task.md`：当前唯一任务
- `acceptance.md`：当前任务验收标准
- `context.md`：当前任务的临时补充背景

这是执行层，不负责长期记忆。

---

### 第二层：项目状态层

目录：`.workflow/project/`

作用：

- 描述项目整体状态
- 记录跨任务持续生效的信息
- 记录长期决策和未解决风险

包含文件：

- `status.md`：项目当前快照
- `next.md`：后续任务列表
- `decisions.md`：重要决策
- `open-issues.md`：尚未解决的问题和风险

这是全局层，不记录开发流水。

---

### 第三层：历史记忆层

分为两个目录：

- `.workflow/history-full/`
- `.workflow/history-ai/`

#### `history-full/`

给你看，保留完整开发历史。

记录特点：

- 按天记录
- 一天一个文件
- 文件路径格式：`YYYY/MM/DD.md`
- 记录当天所有重要工作

#### `history-ai/`

给 AI 看，保留压缩后的长期上下文。

记录特点：

- 按天记录
- 一天一个文件
- 文件路径格式：`YYYY/MM/DD.md`
- 只保留对后续协作真正有价值的内容

---

## 五、角色定义

### 1. Leader Agent

职责：

- 掌握项目全局状态
- 决定下一步行动
- 选择当前唯一任务
- 定义当前任务的完成标准
- 在任务结束后判断是否切换下一任务

必须关注：

- `roadmap.md` 中当前处于哪个阶段
- `next.md` 中哪些任务优先级最高
- `review/` 中是否存在阻塞问题
- `history-ai/` 中是否有影响当前决策的长期背景

负责更新：

- `current/task.md`
- `current/acceptance.md`
- `current/context.md`
- `project/status.md`
- `project/next.md`
- `project/roadmap.md`
- `project/decisions.md`
- `project/open-issues.md`

不负责：

- 直接写业务代码
- 直接做代码审查
- 写 `history-full/` 或 `history-ai/`

---

### 2. Coding Agent

职责：

- 读取当前任务
- 实现代码
- 根据最新 review 修复问题
- 记录本轮历史

必须关注：

- 只做当前任务范围内的内容
- 不能顺手扩展无关功能
- 遇到歧义要显式说明假设

负责更新：

- 必要代码
- `history-full/`

不负责：

- 深度人工测试
- 直接修改 review 文件
- 接管项目方向判断
- 决定下一任务
- 修改 `current/` 和 `project/` 中的全局状态文件

---

### 3. Review Agent

职责：

- 以 `current/acceptance.md` 为第一锚点审查任务是否达标
- 检查明显 bug、接口问题、基础运行风险
- 判断当前任务是否真正完成
- 补足人类运行验证覆盖不到的代码层问题

负责更新：

- `review/YYYY/MM/DD.md`

不负责：

- 直接改代码
- 接管任务实施
- 更新 `current/` 或 `project/`

---

### 4. Doc Agent

Doc Agent 不是主流程角色。

它的主要职责不是写日报，而是：

- 将 `history-full/` 中的完整历史压缩为 `history-ai/`
- 在需要时为下一轮协作生成短背景
- 帮助控制长期上下文体积

适用时机：

- 一天工作结束后
- 项目跨阶段时
- 多个 agent 即将接力时
- 历史变长，需要压缩背景时

负责更新：

- `history-ai/`

不负责：

- 写代码
- 审代码
- 主导项目推进

---

### 5. 你

你的角色是“基础运行验证者”。

你主要做：

- 启动前后端
- 打开页面
- 点击功能
- 看接口是否通
- 看是否直接报错
- 把现象和报错反馈给 AI

你不是这套流程里的重度 QA。  
你不需要承担系统化测试设计。

---

## 六、主流程

### Step 1：Leader 确定当前任务

由 Leader 读取全局状态后，从 `project/next.md` 中选一个最小任务，写入：

- `current/task.md`
- `current/acceptance.md`
- 如有必要，补充 `current/context.md`

要求：

- 当前任务必须唯一
- 当前任务必须可验收
- 当前任务必须避免与 backlog 混在一起
- 验收标准必须由 Leader 明确写入，而不是留给 Coding Agent 自行判断

---

### Step 2：Coding Agent 实现

Coding Agent 开始前应读取：

1. `current/task.md`
2. `current/acceptance.md`
3. `current/context.md`（如果存在有效内容）
4. `project/status.md`
5. `project/decisions.md`
6. `project/open-issues.md`
7. `history-ai/` 最近 2 到 3 篇
8. 最新 review（如果存在）

Coding Agent 完成本轮任务后，应输出：

- 改了哪些文件
- 每个文件改了什么
- 本轮假设是什么
- 是否已经达到可运行状态

---

### Step 3：你做基础运行验证

你只做最小运行验证：

- 能否启动
- 能否打开
- 能否操作
- 是否出现直接报错
- 日志里是否有明显异常

如果不通过：

- 把现象和报错反馈给 Coding Agent

如果基本通过：

- 进入 Review Agent 复审

---

### Step 4：Review Agent 复审

Review Agent 应读取：

1. `current/acceptance.md`
2. `current/task.md`
3. `current/context.md`（如有）
4. 本轮实际改动文件或 diff
5. 你的运行反馈
6. `project/open-issues.md`
7. 相关 `history-ai/`
8. `project/status.md`

Review Agent 必须按以下顺序判断：

1. 是否满足 `acceptance.md`
2. 是否存在明显 bug
3. 是否存在基础运行风险
4. 是否偏离当前任务范围

如果不通过：

- 写入 `review/YYYY/MM/DD.md`
- 返回 Coding Agent 修复

如果通过：

- 写入 review 结果
- 允许进入 Leader 收口阶段

---

### Step 5：Leader 收口并决定下一步

当任务通过后：

由 Leader 更新：

- `project/status.md`
- `project/next.md`
- `project/decisions.md`
- `project/open-issues.md`

由 Coding Agent 更新：

- `history-full/YYYY/MM/DD.md`

之后如需要压缩长期上下文，再由 Doc Agent 更新：

- `history-ai/YYYY/MM/DD.md`

Leader 需要明确判断：

- 当前任务是否真正完成
- 是否需要补充一个修复任务继续留在当前阶段
- 是否可以切换到下一个任务

---

## 七、history 设计

### 1. 完整历史：`history-full/`

这是给你看的历史。

设计目标：

- 保留当天完整工作记录
- 保留尝试过程
- 保留关键修改和问题
- 保留后续可追溯细节

文件组织：

- 年目录：`YYYY/`
- 月目录：`MM/`
- 文件名：`DD.md`

示例：

- `.workflow/history-full/2026/03/17.md`

建议内容：

```markdown
# 2026-03-17

## 任务 1：最简聊天接口联调

### 做了什么
- 新增后端 chat 接口
- 前端接入发送消息
- 页面展示返回结果

### 改动文件
- `backend/...`
- `frontend/...`

### 关键决策
- 先做非流式
- 本轮不接入推荐功能

### 遇到的问题
- SQLite 表不存在
- 前后端响应字段不一致

### 当前结果
- 页面可发送消息
- 持久化仍未完成
```

一个文件可以包含当天多个任务。

---

### 2. 压缩历史：`history-ai/`

这是给 AI 看的历史。

设计目标：

- 为多个 agent 提供长期上下文
- 让下一个 agent 快速接手
- 不让 AI 淹没在细节里

文件组织：

- 年目录：`YYYY/`
- 月目录：`MM/`
- 文件名：`DD.md`

示例：

- `.workflow/history-ai/2026/03/17.md`

建议内容：

```markdown
# 2026-03-17

## 当日关键进展
- 已打通最简聊天闭环
- 前端可以发送消息并展示回复

## 关键决策
- 暂不做流式输出
- 推荐模块后置

## 当前遗留问题
- SQLite 持久化仍未完成
- 异常返回格式还不统一

## 给下一个 Agent 的交接
- 下一步优先补会话与消息持久化
- 不要提前进入推荐模块
```

`history-ai/` 不是流水账，而是交接摘要。

---

## 八、project 层设计

### `project/status.md`

作用：

- 描述项目当前处于什么阶段
- 记录已完成、进行中、下一步和当前风险

维护责任：

- 由 Leader 维护
- Coding Agent 和 Review Agent 只提供输入，不直接改主状态

### `project/next.md`

作用：

- 保存 backlog
- 用于选择下一个最小任务

要求：

- 按优先级排序
- 尽量写成可拆分的小任务
- 由 Leader 负责维护

### `project/decisions.md`

作用：

- 记录跨任务的重要决策

例如：

- 为什么先不用 LangChain
- 为什么先不上 question_tool 的三级降级
- 为什么登录后置

维护责任：

- 由 Leader 负责维护

### `project/open-issues.md`

作用：

- 记录尚未解决的风险、坑点和技术债

例如：

- 数据库初始化流程仍不稳定
- chat 响应字段命名仍待统一
- MCP 工具错误处理还不完整

维护责任：

- 由 Leader 汇总维护
- Review Agent 可在 review 中提出新风险，Leader 再同步到此文件

---

## 九、current 层设计

### `current/task.md`

记录当前唯一任务。

至少包含：

- 任务名
- 目标
- 本轮范围
- 本轮不做
- 预期产出

维护责任：

- 由 Leader 维护

### `current/acceptance.md`

这是任务验收锚点。

至少包含：

- 当前任务
- 通过标准
- 不要求

要求：

- 标准必须可运行验证
- 标准数量尽量控制在 3 到 5 条
- 明确排除项，避免 AI 自动扩展

维护责任：

- 由 Leader 维护
- Coding Agent 不自行更改完成标准

### `current/context.md`

作用：

- 放当前任务需要但不适合写进 `task.md` 的补充背景

例如：

- 某个接口字段约定
- 某个模块的兼容限制
- 某次临时协商结果

如果没有额外背景，可以为空。

---

## 十、Review 文件设计

目录：

- `.workflow/review/YYYY/MM/DD.md`

建议格式：

```markdown
# Review 2026-03-17

## 结论
- [ ] 未通过 / [x] 通过

## 阻塞问题
- [ ] `文件路径:行号` - 问题描述

## 非阻塞问题
- [ ] 问题描述

## 是否满足 acceptance
- [ ] 否 / [x] 是

## 建议下一步
1. 修复项或下一步建议
```

如果一天有多轮 review，可以在同一个文件里增加分节。

---

## 十一、推荐读取顺序

### Leader Agent

1. `project/status.md`
2. `project/roadmap.md`
3. `project/next.md`
4. `project/decisions.md`
5. `project/open-issues.md`
6. `current/task.md`
7. `current/acceptance.md`
8. 最新 `review/`
9. `history-ai/` 最近 2 到 3 篇

### Coding Agent

1. `current/task.md`
2. `current/acceptance.md`
3. `current/context.md`
4. `project/status.md`
5. `project/decisions.md`
6. `project/open-issues.md`
7. `history-ai/` 最近 2 到 3 篇
8. 最新 review

### Review Agent

1. `current/acceptance.md`
2. `current/task.md`
3. `current/context.md`
4. 本轮改动文件或 diff
5. 你的运行反馈
6. `project/open-issues.md`
7. 相关 `history-ai/`
8. `project/status.md`

### Doc Agent

1. 新增的 `history-full/`
2. `project/status.md`
3. `project/decisions.md`
4. `project/open-issues.md`
5. 输出到 `history-ai/`

---

## 十二、适合当前项目的推进顺序

针对当前“AI 智能教育辅导平台”，项目推进顺序不再在本文件重复维护。

统一以以下文件为准：

- `.workflow/project/roadmap.md`：阶段路线
- `.workflow/project/next.md`：当前 backlog 与最小任务拆分
- `.workflow/current/task.md`：当前唯一执行任务

这样可以避免出现：

- 总文档和实际路线不一致
- 当前任务已变更，但历史说明仍停留在旧阶段
- 多个 Agent 读取到冲突的推进顺序

如路线发生调整，由 `Leader Agent` 优先更新：

- `.workflow/project/roadmap.md`
- `.workflow/project/next.md`
- `.workflow/current/task.md`

---

## 十三、最终结论

这套新版工作流的核心不是“把文档写得很多”，而是把协作信息分层，并让 Leader 统一掌握全局：

- `current/` 解决当前任务执行
- `project/` 解决全局状态管理
- `history-full/` 解决人类可追溯历史
- `history-ai/` 解决多 AI 长期上下文

因此，这是一套“最小任务闭环 + 双层历史记忆”的多 Agent 协作方案。

它既保留了快速执行能力，也保留了长期协作所必需的历史连续性。

