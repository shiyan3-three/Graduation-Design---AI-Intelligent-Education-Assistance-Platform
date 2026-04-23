# 2026-04-21（frontend）

## 任务：F3-1 前端学习记录页与基础统计展示

### 做了什么
- 在 `frontend/src/services/api.js` 追加 `fetchAnalyticsTags` 和 `fetchAnalyticsReport` 两个函数
- 将 `GlobalHeader.jsx` 中"学习记录"的 `<button onClick={() => alert(...)}>` 替换为指向 `/learning` 的 `<NavLink>`，含 isActive 高亮
- 新建 `frontend/src/pages/LearningPage/index.jsx`，实现页头、热点 Top3、标签频次列表、骨架屏加载态、空态引导
- 新建 `frontend/src/pages/LearningPage/LearningPage.module.css`，严格使用 `--dashboard-*` CSS 变量，与 Dashboard 风格一致
- 在 `frontend/src/App.jsx` 的 `ProtectedRoute > AppLayout` 下注册 `/learning` 路由

### 改动文件
- `frontend/src/services/api.js` - 追加 `fetchAnalyticsTags` / `fetchAnalyticsReport`
- `frontend/src/components/GlobalHeader/GlobalHeader.jsx` - "学习记录"改为真实 NavLink
- `frontend/src/pages/LearningPage/index.jsx` - 新建页面组件（含 HotspotCard / TagListItem / EmptyState 子组件）
- `frontend/src/pages/LearningPage/LearningPage.module.css` - 新建样式模块
- `frontend/src/App.jsx` - 注册 `/learning` 路由，新增 LearningPage import

### 关键决策
- rank 色系通过独立 class（`rankBadge1/2/3`）实现，避免 CSS Modules 父子选择器编译歧义
- `AppLayout` 已全局挂载 `GlobalHeader`，`LearningPage` 无需再次引入
- 日志文件命名为 `21-frontend.md` 而非 `21.md`，避免覆盖同日 B4 后端日志

### 遇到的问题
- 无

### 当前结果
- `/learning` 路由可访问，GlobalHeader "学习记录"高亮激活
- 有数据时展示热点 Top3（3 列卡片 + rank 色徽章）和标签频次列表
- 无数据时展示空态 + "去和 AI 对话"跳转按钮
- 加载期间展示骨架屏

---

## 任务：F4-1 前端推荐题目页

### 做了什么
- 在 `frontend/src/services/api.js` 追加 `fetchRecommend` 和 `submitRecommendFeedback` 两个函数
- 新建 `frontend/src/pages/RecommendPage/index.jsx`，实现全屏分栏工作台：骨架屏加载态、空态引导、全部完成态、左侧任务列表、右侧答题详情面板
- 新建 `frontend/src/pages/RecommendPage/RecommendPage.module.css`，100% 还原 `frontend/reflection/7.md` 视觉原型
- 在 `frontend/src/App.jsx` 注册 `/recommend` 路由
- 将 `GlobalHeader.jsx` 中"靶向推荐" button 替换为指向 `/recommend` 的 NavLink，含 isActive 高亮

### 改动文件
- `frontend/src/services/api.js` - 追加 `fetchRecommend` / `submitRecommendFeedback`
- `frontend/src/pages/RecommendPage/index.jsx` - 新建页面组件
- `frontend/src/pages/RecommendPage/RecommendPage.module.css` - 新建样式模块
- `frontend/src/App.jsx` - 注册 `/recommend` 路由，新增 RecommendPage import
- `frontend/src/components/GlobalHeader/GlobalHeader.jsx` - "靶向推荐"改为真实 NavLink

### 关键决策
- `effectiveShowAnswer = qState.showAnswer || status !== 'pending'`：已处理题目自动展示答案与解析，无需用户再点"查看答案"
- 跳过按钮 status 值为 `'skipped'`（非原型中的 `'completed'`），左侧列表区分绿色 ✔（已完成）和灰色 →（已跳过）
- 全部完成态内联展示替代 `alert()`，含"刷新推荐"按钮重新调用 `fetchRecommend()`
- CSS Module 中加分项选项高亮（correct/wrong）通过独立 class 实现，避免复合选择器歧义
- 反馈按钮使用 `feedbackLoading[id]` 防止重复提交

### 遇到的问题
- 无

### 当前结果
- `npm run build` 通过（✓ 320 modules，1.62s）
- `/recommend` 路由已注册，GlobalHeader "靶向推荐"高亮激活
- 加载期间展示 2 个骨架占位卡片
- 有题目时：分栏布局，左侧列表 + 右侧答题面板，支持选项高亮、答案查看切换、完成/跳过反馈
- 无题目时：空态 + 跳转 `/chat` 按钮
- 全部处理后：内联完成区域 + 刷新推荐按钮
