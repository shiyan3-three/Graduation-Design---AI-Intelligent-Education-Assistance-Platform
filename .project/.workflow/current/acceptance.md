# 验收标准

> 维护责任：`Leader Agent`

## 当前任务
B-Admin-2 + F-Admin 题库 CRUD 后端 + 前端管理员面板

## 第一部分：B-Admin-2 后端扩展
- 登录接口响应中包含 `is_admin` 字段
- `PUT /api/admin/users/{id}/admin` 无 Token 返回 401，普通用户 403，管理员 200 并切换状态
- `GET /api/admin/questions` 管理员 Token 返回 200，`data.items` 列表包含 `options`（合并字段）
- `POST /api/admin/questions` 缺少必填字段返回 422，管理员创建成功返回 201
- `PUT /api/admin/questions/{id}` 修改后查询可见更新结果
- `DELETE /api/admin/questions/{id}` 删除成功后再次删除返回 404
- 现有所有后端测试全部通过（`python -m unittest discover -s backend/tests`）

## 第二部分：F-Admin 前端面板
- `GlobalHeader` 中管理员用户可见蓝色“🛡 管理后台”菜单项，普通用户不可见
- 访问 `/admin` 路由时非管理员自动跳转至 `/`
- 系统概览 Tab：4 张统计卡展示真实数据（`total_users`、`total_sessions`、`total_messages`、`total_recommendations`）
- 用户管理 Tab：列表展示所有用户，可切换管理员状态、内联展开确认删除
- 题库管理 Tab：列表展示题目，支持学科/专题过滤
- 题库管理：点击“+ 新增题目”在表格顶部展开内联新增表单行
- 题库管理：点击“编辑”该行切换为内联可编辑状态（只修改 question/answer/options）
- 题库管理：点击“删除”该行展开内联确认区（不弹层）
- `npm run build` 通过，无 ESLint error
- `/chat`、`/`、`/learning`、`/recommend`、`/login` 路由烟测无回归

## 加分项
- 题库管理的学科过滤 + 专题搜索功能正常过滤
- 统计卡加载期间显示骨架屏

## 不要求
- 不要求题库分页
- 不要求管理员注册 HTTP 接口
- 不要求前端单元测试

## 使用规则
- `Coding Agent` 不自行修改完成标准
- `Review Agent` 必须先对照本文件判断任务是否通过
