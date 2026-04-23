# 当前任务

> 维护责任：`Leader Agent`

## 任务名称
题库 CRUD 后端 + 前端管理员面板

## 任务编号
B-Admin-2 + F-Admin（合并任务）

## 目标
先完成后端题库 CRUD + 用户管理扩展接口（B-Admin-2），再实现前端管理员面板（F-Admin）。前端设计原图位于 `frontend/reflection/8.md`。

---

## 第一阶段：B-Admin-2 后端扩展（必须先完成）

### 1. 登录接口返回 `is_admin`

`backend/routers/auth.py` 的登录响应中，在 `UserOut` 或登录响应数据中新增 `is_admin` 字段，供前端写入 localStorage 后判断管理员入口。

### 2. `PUT /api/admin/users/{id}/admin` 切换管理员状态

```python
@router.put('/api/admin/users/{target_id}/admin')
async def toggle_admin(
    target_id: int,
    admin_id: int = Depends(get_current_admin_user_id),
) -> JSONResponse:
    # 切换 is_admin 布尔値，不能操作自身
```

### 3. 题库 CRUD 4 个接口（全部位于 `/api/admin/questions`）

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/admin/questions` | 列表，支持 `?subject=&topic=` 过滤 |
| POST | `/api/admin/questions` | 新增题目 |
| PUT | `/api/admin/questions/{id}` | 更新（只修改 `question`、`answer`、`topic`、`subject`、`options` 5 个字段） |
| DELETE | `/api/admin/questions/{id}` | 删除 |

**不需要分常。** 无题目时返回空数组即可。

### 4. 新增模型（`backend/models.py`）

```python
class QuestionOut(BaseModel):
    id: int
    subject: str
    topic: str
    question: str
    options: str      # 合并字段: "A. ...\nB. ...\nC. ...\nD. ..."
    answer: str
    source: str

class AdminQuestionsResponseData(BaseModel):
    items: List[QuestionOut]

class CreateQuestionRequest(BaseModel):
    subject: str
    topic: str
    question: str
    options: str      # 前端合并 textarea，后端存入 option_a~d
    answer: str
    source: str = 'manual'

class UpdateQuestionRequest(BaseModel):
    question: Optional[str] = None
    options: Optional[str] = None  # 合并字段
    answer: Optional[str] = None
    topic: Optional[str] = None
    subject: Optional[str] = None
```

**options 存储约定**：前后端统一用 `"A. ...\nB. ...\nC. ...\nD. ..."` 单字段存储；`question_bank` 表的 `option_a~d` 列即分割赋値。

### 5. 写测试（`backend/tests/test_admin_questions.py`）
- 列表：401 / 403 / 管理员 200
- 新增：少字段 422 / 管理员 201
- 更新：修改后查询可见
- 删除：二次删除同 ID 返回 404

---

## 第二阶段：F-Admin 前端实现（后端完成后再开始）

> 设计原图：`frontend/reflection/8.md`（可直接用浏览器打开查看）

### 6. GlobalHeader 新增管理员入口

- 读取 `localStorage.getItem('edu_user')` 中的 `is_admin`
- 若为 `true`，在下拉菜单**第一位**插入：
  ```jsx
  <button style={{ color: 'var(--primary)' }} onClick={() => handleAction('admin')}>
    🛡 管理后台
  </button>
  ```
- `handleAction('admin')` 跳转至 `/admin`
- 普通用户完全看不到此项

### 7. 新建 `/admin` 路由 + 页面

**路由守卫：**进入时检查 `is_admin`，否则跳转至 `/`。

**AdminPage 组件结构：**
```
frontend/src/pages/AdminPage/
  index.jsx          # 主页，含 Tab 切换逻辑
  AdminPage.module.css
```

**3 个 Tab（参考原图 `8.md`）：**

| Tab | 内容 | 调用接口 |
|-----|------|----------|
| 📊 系统概览 | 4 张统计卡 | `GET /api/admin/stats` |
| 👥 用户管理 | 表格 + 内联确认删除 + 切换管理员 | `GET/DELETE /api/admin/users` + `PUT .../admin` |
| 📚 题库管理 | 表格 + 新增表单行 + 内联编辑 + 内联删除确认 | `GET/POST/PUT/DELETE /api/admin/questions` |

**编辑装语：**
- 只修改 `question`（textarea）、`answer`（input）、`options`（合并 textarea）
- 删除点击后该行内联展开确认区（不弹层）

## 本轮不做
- ❌ 不改 `ChatPage`、`LearningPage`、`RecommendPage`、`HomePage`
- ❌ 不做分页（题库数量课题级，一次全量返回）
- ❌ 不做管理员注册 HTTP 接口

## 预期产出
- `backend/routers/auth.py` 登录响应含 `is_admin`
- `backend/routers/admin.py` 新增 5 个接口（toggle_admin + 4 个 questions CRUD）
- `backend/models.py` 新增 4 个模型
- `backend/tests/test_admin_questions.py` 新建
- `frontend/src/components/GlobalHeader/GlobalHeader.jsx` 管理员入口
- `frontend/src/pages/AdminPage/index.jsx` + CSS Module
- `frontend/src/App.jsx`（或路由文件） 注册 `/admin` 路由
- `npm run build` 通过

## 任务切换规则
- 此为项目最终任务，完成后整个项目收口
