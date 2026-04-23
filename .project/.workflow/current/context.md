# 当前任务补充背景

> 维护责任：`Leader Agent`

## Leader Agent 指令（2026-04-22）

**任务：B-Admin-2 + F-Admin 合并任务**

**指派给：Coding Agent（先后端后前端）**

> 设计原图：`frontend/reflection/8.md`，可直接用浏览器打开交互式查看。

---

### 现有代码结构（B-Admin 基础版已完成）

| 文件 | 当前状态 | 本轮改动 |
|------|----------|----------|
| `backend/routers/auth.py` | 登录响应无 `is_admin` | 新增 `is_admin` 至 `UserOut` |
| `backend/routers/admin.py` | 已有 users CRUD + stats | 新增 toggle_admin + 4 个 questions 接口 |
| `backend/models.py` | 已有 AdminUserOut 等 | 新增 QuestionOut / CreateQuestionRequest / UpdateQuestionRequest / AdminQuestionsResponseData |
| `backend/tests/test_admin_questions.py` | 不存在 | 新建 |
| `frontend/.../GlobalHeader.jsx` | 无管理员入口 | 条件渲染蓝色菜单项 |
| `frontend/src/pages/AdminPage/` | 不存在 | 新建，3 个 Tab |
| `frontend/src/App.jsx` | 无 `/admin` 路由 | 注册路由 |

---

### question_bank 表结构（必读）

```sql
CREATE TABLE question_bank (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    topic TEXT NOT NULL,
    question TEXT NOT NULL,
    option_a TEXT,
    option_b TEXT,
    option_c TEXT,
    option_d TEXT,
    answer TEXT NOT NULL,
    explanation TEXT DEFAULT '',
    source TEXT NOT NULL DEFAULT 'ceval'
);
```

**options 合并/拆分约定：**
- 前端 textarea 内容格式：`"A. ...\nB. ...\nC. ...\nD. ..."`
- 后端 GET 时：拼接 `option_a~d` → `options` 字段返回给前端
- 后端 POST/PUT 时：按行解析 `options`，去掉 `A. ` 前缀后分别存入 `option_a~d`

```python
def _split_options(options_str: str) -> tuple[str, str, str, str]:
    """'A. x\nB. y\nC. z\nD. w' -> ('x','y','z','w')"""
    lines = [l.strip() for l in options_str.strip().splitlines() if l.strip()]
    vals = []
    for line in lines:
        # 去掉 'A. ' 'B. ' 等前缀
        if len(line) >= 3 and line[1] in '.、':
            vals.append(line[3:].strip() if line[2] == ' ' else line[2:].strip())
        else:
            vals.append(line)
    while len(vals) < 4:
        vals.append('')
    return tuple(vals[:4])
```

---

### 登录接口 is_admin 补充方式

`UserOut` 模型新增 `is_admin: bool = False`，登录时从 DB 查到 `is_admin` 列赋値即可。前端登录后将完整 user 对象写入 `localStorage('edu_user')`，GlobalHeader 读取 `user.is_admin`。

---

### 前端 AdminPage 关键实现细节

**路由守卫模式（在 AdminPage 顶部）：**
```jsx
useEffect(() => {
  const user = JSON.parse(localStorage.getItem('edu_user') || '{}');
  if (!user.is_admin) navigate('/', { replace: true });
}, []);
```

**3 个 Tab 共用一套 `activeTab` state：**
```jsx
const [activeTab, setActiveTab] = useState('overview'); // 'overview'|'users'|'questions'
```

**题库编辑行模式（各行独立 state，存在 Map 中）：**
- `editingId`：当前内联编辑的题目 id（null=无）
- `confirmDeleteId`：当前内联确认删除的题目 id（null=无）
- `showAddForm`：是否显示新增行

**前端调用 admin 接口需要 Bearer token**，直接复用 `requestJson`（已自动携带）。

---

### 关键约束

1. **严格先后顺序**：所有后端接口 + 测试通过后，再开始写前端
2. **不改现有其他路由**：只改 `auth.py`（加 is_admin）和 `admin.py`（加接口）
3. **CSS 变量复用**：AdminPage 使用 `:root` 中已有变量，不引入新颜色体系
4. **管理员入口颜色**：用 `var(--color-primary)` 或等效蓝色，不 hardcode

## 使用规则
- 只写会影响当前任务执行的补充背景
