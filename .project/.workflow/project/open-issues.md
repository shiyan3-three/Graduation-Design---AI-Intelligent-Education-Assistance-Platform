# 未解决问题与风险

> 维护责任：`Leader Agent`
> 
> 说明：本文件记录仍然有效的风险、坑点和技术债。`Review Agent` 可以提出风险，但最终由 `Leader Agent` 收口维护。

<!-- 记录尚未解决的风险、坑点和技术债 -->
<!-- 格式：问题描述（来源：review/日期 或 手动添加）-->
<!-- 问题解决后删除对应条目 -->

- 模型调用、工具调用与正式 MCP Server 的边界尚未最终确定（来源：初始化）
- 如果模型调用或联网条件受限，需要预留清晰的降级或 Mock 方案（来源：初始化）
- 大模型 API 的 base_url 和 api_key 需通过环境变量管理，避免硬编码泄露（来源：B2-1 指令）
- 新会话标题的生成规则尚未正式确定，当前暂用首条消息前 20 字符（来源：D-2 Review，2026-03-23）
- JWT 过期时间 `expires_in` 的精确计算方式需实现时明确，建议 604800 秒（来源：D-2 Review，2026-03-23）
- LLM 调用失败时完全静默 fallback 到 mock，无日志输出，可能影响联调排障（来源：B2-1 Review，2026-03-23）
- `post_chat` 使用两次独立连接上下文，可能出现"只有用户消息但无助手消息"的中间状态（来源：B2-1 Review，2026-03-23）
- 缺少 `.env.example` 环境变量模板文件（来源：B2-1 Review，2026-03-23）
- `knowledge_tool` 搜索结果未做站点过滤，返回来源混入百科、资讯站和内容平台；且 `snippet` 缺失时回退到整段 `content`，结果长度可达 3-4 KB，后续建议增加截断或清洗（来源：B3-2 Review，2026-04-15）
- `sidebar-app.js` 和 `app.js` 各有一份重复的 `createMessageElement` 函数，增加维护成本，后续可考虑抽取为公共模块（来源：Leader Agent F2-3 代码审查，2026-04-15）
- `database.get_connection()` 为裸连接接口，后续新增 SQLite 调用点如仍写成 `with database.get_connection()`，有连接泄漏风险；进入 MCP 阶段前建议补充团队约定或轻量封装（来源：B3-3 Review，2026-04-17）
- MCP Python SDK 版本迭代较快，AI 生成的 MCP 代码可能存在 API 幻觉，Coding Agent 必须参考最新官方文档而非凭训练数据编写（来源：Leader Agent 第 4 阶段风险评估，2026-04-17）
- MCP Client 当前每次调用新建一个 stdio 子进程连接，性能不佳；M4-2 或 M4-3 阶段考虑做连接复用或生命周期管理（来源：M4-1 Review，2026-04-17）
- React 组件交互自动化测试覆盖偏薄，FR-1 仅靠命令行 + 人类浏览器验证确认行为正确；后续建议补轻量组件级回归测试（来源：FR-1 Review，2026-04-18）
- JWT 默认开发密钥 `dev-secret-key` 长度低于 PyJWT 对 HS256 推荐值，会触发 `InsecureKeyLengthWarning`；正式环境必须通过 `JWT_SECRET` 环境变量覆盖为 32 字节以上随机密钥（来源：B1 Review，2026-04-19）
- `/api/auth/me` 成功响应未回写 localStorage，前端可能显示旧用户信息；同时孤儿用户场景返回 404 而非 401，后续完善认证闭环时应一并修正（来源：FH-1 联调 Review，2026-04-19）
- Dashboard 当前为静态原型页，未接真实后端数据；需 B4 学习记录接口就绪后单独立项联调（来源：FH-1 联调 Review，2026-04-19）

## 已解决

- ~~核心数据库表设计尚未正式定稿~~ → D-1 完成
- ~~SQLite 初始化流程尚未落地~~ → 已在 decisions.md 中明确
- ~~chat 请求/响应字段契约尚未固定~~ → D-2 API 设计已固定全部字段契约
- ~~messages.sequence_no 递增管理~~ → 已在 context.md 中明确由应用层递增
- ~~sessions.updated_at 更新时机~~ → 已在 API 设计中明确
- ~~B3-2 依赖百度搜索 API Key 配置~~ → B3-2 已完成，API Key 通过环境变量管理
- ~~B3-3 question_tool 与 import_ceval SQLite 连接泄漏~~ → 已修复为显式关闭，24/24 测试通过（2026-04-17）

## 使用规则

- 已解决的问题应及时删除或转入历史
- 新风险先可出现在 `review/` 中，再由 `Leader Agent` 同步到本文件
