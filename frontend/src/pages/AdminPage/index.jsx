import { Fragment, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { isStoredAdmin, readStoredUser } from '../../admin-access.js';
import {
  createAdminQuestion,
  deleteAdminQuestion,
  deleteAdminUser,
  fetchAdminQuestions,
  fetchAdminStats,
  fetchAdminUsers,
  toggleAdminUser,
  updateAdminQuestion,
} from '../../services/api.js';
import { runAdminRequest } from './admin-request.js';
import styles from './AdminPage.module.css';

const PAGE_SIZE = 10;
const QUESTIONS_PAGE_SIZE = 5;

const EMPTY_STATS = {
  total_users: 0,
  total_sessions: 0,
  total_messages: 0,
  total_recommendations: 0,
};

const EMPTY_QUESTION_FORM = {
  subject: '',
  topic: '',
  question: '',
  options: 'A. \nB. \nC. \nD. ',
  answer: '',
};

const TABS = [
  { id: 'overview', label: '系统概览' },
  { id: 'users', label: '用户管理' },
  { id: 'questions', label: '题库管理' },
];

export function AdminPage() {
  const navigate = useNavigate();
  const [canAccessAdmin] = useState(() => isStoredAdmin());
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState(EMPTY_STATS);
  const [users, setUsers] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [confirmUserDeleteId, setConfirmUserDeleteId] = useState(null);
  const [confirmQuestionDeleteId, setConfirmQuestionDeleteId] = useState(null);
  const [editingQuestionId, setEditingQuestionId] = useState(null);
  const [editDraft, setEditDraft] = useState(EMPTY_QUESTION_FORM);
  const [showAddForm, setShowAddForm] = useState(false);
  const [addDraft, setAddDraft] = useState(EMPTY_QUESTION_FORM);
  const [subjectFilter, setSubjectFilter] = useState('');
  const [topicFilter, setTopicFilter] = useState('');
  const [usersPage, setUsersPage] = useState(1);
  const [questionsPage, setQuestionsPage] = useState(1);
  const currentUser = useMemo(() => readStoredUser(), []);
  const currentUserId = Number(currentUser.id);

  const subjectDistribution = useMemo(() => {
    const counts = {};
    for (const q of questions) {
      counts[q.subject] = (counts[q.subject] || 0) + 1;
    }
    const total = questions.length;
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .map(([subject, count]) => ({
        subject,
        count,
        pct: total > 0 ? Math.round((count / total) * 100) : 0,
      }));
  }, [questions]);

  const recentUsers = useMemo(
    () => [...users].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 5),
    [users]
  );

  useEffect(() => {
    if (!canAccessAdmin) {
      navigate('/', { replace: true });
    }
  }, [canAccessAdmin, navigate]);

  useEffect(() => {
    if (!canAccessAdmin) return;
    loadStats();
    loadUsers();
  }, [canAccessAdmin]);

  useEffect(() => {
    if (!canAccessAdmin) return;
    loadQuestions();
    setQuestionsPage(1);
  }, [canAccessAdmin, subjectFilter, topicFilter]);

  if (!canAccessAdmin) {
    return null;
  }

  const avgSessions =
    stats.total_users > 0 ? (stats.total_sessions / stats.total_users).toFixed(1) : '0';

  const statCards = [
    { label: '注册用户数', value: stats.total_users },
    { label: '学习会话数', value: stats.total_sessions },
    { label: '对话消息数', value: stats.total_messages },
    { label: '推荐任务数', value: stats.total_recommendations },
    { label: '题库总题数', value: questions.length },
    { label: '人均会话数', value: loading ? '—' : avgSessions },
  ];

  const paginatedUsers = users.slice((usersPage - 1) * PAGE_SIZE, usersPage * PAGE_SIZE);
  const paginatedQuestions = questions.slice(
    (questionsPage - 1) * QUESTIONS_PAGE_SIZE,
    questionsPage * QUESTIONS_PAGE_SIZE
  );

  async function loadStats() {
    setLoading(true);
    const result = await runAdminRequest(fetchAdminStats, '系统统计加载失败');
    setLoading(false);
    if (result.ok) {
      setStats(result.data || EMPTY_STATS);
      return;
    }
    setStatusMessage(result.message);
  }

  async function loadUsers() {
    const result = await runAdminRequest(fetchAdminUsers, '用户列表加载失败');
    if (result.ok) {
      setUsers((result.data && result.data.items) || []);
      return;
    }
    setStatusMessage(result.message);
  }

  async function loadQuestions() {
    const result = await runAdminRequest(
      () => fetchAdminQuestions({
        subject: subjectFilter.trim(),
        topic: topicFilter.trim(),
      }),
      '题库列表加载失败'
    );
    if (result.ok) {
      setQuestions((result.data && result.data.items) || []);
      return;
    }
    setStatusMessage(result.message);
  }

  async function handleToggleAdmin(user) {
    const result = await runAdminRequest(
      () => toggleAdminUser(user.id),
      '管理员状态切换失败'
    );
    if (result.ok) {
      setStatusMessage(`已更新 ${user.username} 的管理员状态`);
      await loadUsers();
      return;
    }
    setStatusMessage(result.message);
  }

  async function handleDeleteUser(userId) {
    const result = await runAdminRequest(
      () => deleteAdminUser(userId),
      '用户删除失败'
    );
    if (result.ok) {
      setConfirmUserDeleteId(null);
      setStatusMessage('用户已删除');
      await Promise.all([loadUsers(), loadStats()]);
      return;
    }
    setStatusMessage(result.message);
  }

  async function handleCreateQuestion() {
    if (!addDraft.subject || !addDraft.topic || !addDraft.question || !addDraft.answer) {
      setStatusMessage('请补全题目、学科、专题和答案');
      return;
    }
    const result = await runAdminRequest(
      () => createAdminQuestion(addDraft),
      '新增题目失败'
    );
    if (result.ok) {
      setAddDraft(EMPTY_QUESTION_FORM);
      setShowAddForm(false);
      setStatusMessage('题目已新增');
      await loadQuestions();
      return;
    }
    setStatusMessage(result.message);
  }

  function startEditQuestion(question) {
    setEditingQuestionId(question.id);
    setConfirmQuestionDeleteId(null);
    setEditDraft({
      subject: question.subject,
      topic: question.topic,
      question: question.question,
      options: question.options,
      answer: question.answer,
    });
  }

  async function handleUpdateQuestion(questionId) {
    const result = await runAdminRequest(
      () => updateAdminQuestion(questionId, {
        question: editDraft.question,
        options: editDraft.options,
        answer: editDraft.answer,
      }),
      '更新题目失败'
    );
    if (result.ok) {
      setEditingQuestionId(null);
      setStatusMessage('题目已更新');
      await loadQuestions();
      return;
    }
    setStatusMessage(result.message);
  }

  async function handleDeleteQuestion(questionId) {
    const result = await runAdminRequest(
      () => deleteAdminQuestion(questionId),
      '删除题目失败'
    );
    if (result.ok) {
      setConfirmQuestionDeleteId(null);
      setStatusMessage('题目已删除');
      await loadQuestions();
      return;
    }
    setStatusMessage(result.message);
  }

  return (
    <div className={styles.adminShell}>
      <section className={styles.topBar}>
        <div>
          <p className={styles.eyebrow}>Administrator Console</p>
          <h1>管理后台</h1>
        </div>
        <button type="button" className={styles.backButton} onClick={() => navigate('/')}>
          返回首页
        </button>
      </section>

      <div className={styles.adminLayout}>
        <aside className={styles.sidebar}>
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={`${styles.tabButton} ${activeTab === tab.id ? styles.active : ''}`}
              onClick={() => {
                setActiveTab(tab.id);
                setUsersPage(1);
                setQuestionsPage(1);
              }}
            >
              {tab.label}
            </button>
          ))}
        </aside>

        <section className={styles.contentPanel}>
          {statusMessage && (
            <div className={styles.statusBar}>
              <span>{statusMessage}</span>
              <button type="button" onClick={() => setStatusMessage('')}>关闭</button>
            </div>
          )}

          {activeTab === 'overview' && (
            <div>
              <h2 className={styles.sectionTitle}>系统概览</h2>
              <div className={styles.statsGrid}>
                {statCards.map((card) => (
                  <article key={card.label} className={styles.statCard}>
                    <span>{card.label}</span>
                    <strong>{loading ? '—' : card.value}</strong>
                  </article>
                ))}
              </div>

              <div className={styles.overviewGrid}>
                <div className={styles.overviewSection}>
                  <h3 className={styles.subSectionTitle}>题库学科分布</h3>
                  {subjectDistribution.length === 0 ? (
                    <p className={styles.emptyCell}>暂无题目数据</p>
                  ) : (
                    <table className={styles.distributionTable}>
                      <thead>
                        <tr><th>学科</th><th>题目数</th><th>占比</th></tr>
                      </thead>
                      <tbody>
                        {subjectDistribution.map((row) => (
                          <tr key={row.subject}>
                            <td>{row.subject}</td>
                            <td>{row.count}</td>
                            <td>{row.pct}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>

                <div className={styles.overviewSection}>
                  <h3 className={styles.subSectionTitle}>最近注册用户</h3>
                  {recentUsers.length === 0 ? (
                    <p className={styles.emptyCell}>暂无用户数据</p>
                  ) : (
                    <ul className={styles.recentUsersList}>
                      {recentUsers.map((u) => (
                        <li key={u.id} className={styles.recentUserItem}>
                          <span className={styles.recentUserName}>{u.username}</span>
                          <span className={styles.recentUserTime}>{formatDate(u.created_at)}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'users' && (
            <div>
              <h2 className={styles.sectionTitle}>用户管理</h2>
              <div className={styles.tableWrap}>
                <table>
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>用户名</th>
                      <th>年级</th>
                      <th>学科</th>
                      <th>注册时间</th>
                      <th>角色</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedUsers.map((user, index) => {
                      const isSelf = Number(user.id) === currentUserId;
                      const absIndex = (usersPage - 1) * PAGE_SIZE + index + 1;
                      return (
                        <Fragment key={user.id}>
                          <tr>
                            <td>{absIndex}</td>
                            <td><strong>{user.username}</strong></td>
                            <td>{user.grade}</td>
                            <td>{user.subject}</td>
                            <td>{user.created_at}</td>
                            <td>
                              <span className={`${styles.badge} ${user.is_admin ? styles.adminBadge : styles.userBadge}`}>
                                {user.is_admin ? '管理员' : '普通用户'}
                              </span>
                            </td>
                            <td>
                              <div className={styles.actions}>
                                <button
                                  type="button"
                                  className={styles.primaryAction}
                                  disabled={isSelf}
                                  onClick={() => handleToggleAdmin(user)}
                                >
                                  {user.is_admin ? '取消管理员' : '设为管理员'}
                                </button>
                                <button
                                  type="button"
                                  className={styles.dangerAction}
                                  disabled={isSelf}
                                  onClick={() => setConfirmUserDeleteId(user.id)}
                                >
                                  删除
                                </button>
                              </div>
                            </td>
                          </tr>
                          {confirmUserDeleteId === user.id && (
                            <tr className={styles.confirmRow}>
                              <td colSpan={7}>
                                <span>确认删除用户"{user.username}"？其会话、消息和推荐记录会级联删除。</span>
                                <button type="button" onClick={() => setConfirmUserDeleteId(null)}>取消</button>
                                <button type="button" className={styles.dangerAction} onClick={() => handleDeleteUser(user.id)}>
                                  确认删除
                                </button>
                              </td>
                            </tr>
                          )}
                        </Fragment>
                      );
                    })}
                    {users.length === 0 && (
                      <tr><td colSpan={7} className={styles.emptyCell}>暂无用户</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
              <Pagination page={usersPage} total={users.length} pageSize={PAGE_SIZE} onChange={setUsersPage} />
            </div>
          )}

          {activeTab === 'questions' && (
            <div>
              <div className={styles.sectionHeader}>
                <h2 className={styles.sectionTitle}>题库管理</h2>
                <button type="button" className={styles.addButton} onClick={() => setShowAddForm((value) => !value)}>
                  + 新增题目
                </button>
              </div>

              <div className={styles.toolbar}>
                <input
                  value={subjectFilter}
                  onChange={(event) => { setSubjectFilter(event.target.value); setQuestionsPage(1); }}
                  placeholder="按学科过滤"
                />
                <input
                  value={topicFilter}
                  onChange={(event) => { setTopicFilter(event.target.value); setQuestionsPage(1); }}
                  placeholder="按专题搜索"
                />
              </div>

              <div className={styles.tableWrap}>
                <table className={styles.questionsTable}>
                  <colgroup>
                    <col style={{ width: '48px' }} />
                    <col style={{ width: '80px' }} />
                    <col style={{ width: '120px' }} />
                    <col />
                    <col style={{ width: '64px' }} />
                    <col style={{ width: '140px' }} />
                  </colgroup>
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>学科</th>
                      <th>专题</th>
                      <th>题目预览</th>
                      <th>答案</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {showAddForm && (
                      <tr className={styles.inlineEditRow}>
                        <td colSpan={6}>
                          <div className={styles.addGrid}>
                            <input
                              value={addDraft.subject}
                              onChange={(event) => setAddDraft({ ...addDraft, subject: event.target.value })}
                              placeholder="学科"
                            />
                            <input
                              value={addDraft.topic}
                              onChange={(event) => setAddDraft({ ...addDraft, topic: event.target.value })}
                              placeholder="专题"
                            />
                            <input
                              value={addDraft.answer}
                              onChange={(event) => setAddDraft({ ...addDraft, answer: event.target.value })}
                              placeholder="答案"
                            />
                          </div>
                          <textarea
                            rows={3}
                            value={addDraft.question}
                            onChange={(event) => setAddDraft({ ...addDraft, question: event.target.value })}
                            placeholder="题目内容"
                          />
                          <textarea
                            rows={4}
                            value={addDraft.options}
                            onChange={(event) => setAddDraft({ ...addDraft, options: event.target.value })}
                            placeholder={'A. 选项\nB. 选项\nC. 选项\nD. 选项'}
                          />
                          <div className={styles.inlineActions}>
                            <button type="button" className={styles.successAction} onClick={handleCreateQuestion}>保存</button>
                            <button type="button" className={styles.ghostAction} onClick={() => setShowAddForm(false)}>取消</button>
                          </div>
                        </td>
                      </tr>
                    )}

                    {paginatedQuestions.map((question, index) => {
                      const absIndex = (questionsPage - 1) * QUESTIONS_PAGE_SIZE + index + 1;
                      return (
                        <Fragment key={question.id}>
                          {editingQuestionId === question.id ? (
                            <tr className={styles.inlineEditRow}>
                              <td colSpan={6}>
                                <textarea
                                  rows={3}
                                  value={editDraft.question}
                                  onChange={(event) => setEditDraft({ ...editDraft, question: event.target.value })}
                                />
                                <div className={styles.editGrid}>
                                <textarea
                                  rows={4}
                                  value={editDraft.options}
                                  onChange={(event) => setEditDraft({ ...editDraft, options: event.target.value })}
                                />
                                <input
                                  value={editDraft.answer}
                                  onChange={(event) => setEditDraft({ ...editDraft, answer: event.target.value })}
                                  placeholder="答案"
                                />
                              </div>
                              <div className={styles.inlineActions}>
                                <button type="button" className={styles.successAction} onClick={() => handleUpdateQuestion(question.id)}>
                                  保存修改
                                </button>
                                <button type="button" className={styles.ghostAction} onClick={() => setEditingQuestionId(null)}>
                                  取消
                                </button>
                              </div>
                            </td>
                          </tr>
                          ) : (
                            <tr>
                              <td>{absIndex}</td>
                              <td><span className={styles.cellText}>{question.subject}</span></td>
                              <td><span className={styles.cellText}>{question.topic}</span></td>
                              <td><span className={styles.questionPreview}>{question.question}</span></td>
                              <td className={styles.answerCell}><strong>{question.answer}</strong></td>
                              <td>
                                <div className={styles.actions}>
                                  <button type="button" className={styles.primaryAction} onClick={() => startEditQuestion(question)}>
                                    编辑
                                  </button>
                                  <button type="button" className={styles.dangerAction} onClick={() => setConfirmQuestionDeleteId(question.id)}>
                                    删除
                                  </button>
                                </div>
                              </td>
                            </tr>
                          )}
                          {confirmQuestionDeleteId === question.id && (
                            <tr className={styles.confirmRow}>
                              <td colSpan={6}>
                                <span>确认删除这道题目？</span>
                                <button type="button" onClick={() => setConfirmQuestionDeleteId(null)}>取消</button>
                                <button type="button" className={styles.dangerAction} onClick={() => handleDeleteQuestion(question.id)}>
                                  确认删除
                                </button>
                              </td>
                            </tr>
                          )}
                        </Fragment>
                      );
                    })}
                    {questions.length === 0 && !showAddForm && (
                      <tr>
                        <td colSpan={6} className={styles.emptyCell}>暂无题目</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              <Pagination page={questionsPage} total={questions.length} pageSize={QUESTIONS_PAGE_SIZE} onChange={setQuestionsPage} />
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function Pagination({ page, total, pageSize, onChange }) {
  const totalPages = Math.ceil(total / pageSize);
  if (totalPages <= 1) return null;
  const nums = buildPageNumbers(page, totalPages);
  return (
    <div className={styles.pagination}>
      <button type="button" className={styles.pageBtn} disabled={page === 1} onClick={() => onChange(page - 1)}>
        上一页
      </button>
      {nums.map((p, i) =>
        p === '...' ? (
          <span key={`ellipsis-${i}`} className={styles.pageEllipsis}>…</span>
        ) : (
          <button
            key={p}
            type="button"
            className={`${styles.pageBtn} ${page === p ? styles.pageActive : ''}`}
            onClick={() => onChange(p)}
          >
            {p}
          </button>
        )
      )}
      <button type="button" className={styles.pageBtn} disabled={page === totalPages} onClick={() => onChange(page + 1)}>
        下一页
      </button>
    </div>
  );
}

function buildPageNumbers(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const show = new Set([1, total]);
  for (let p = Math.max(1, current - 1); p <= Math.min(total, current + 1); p++) show.add(p);
  const sorted = [...show].sort((a, b) => a - b);
  const result = [];
  for (let i = 0; i < sorted.length; i++) {
    if (i > 0 && sorted[i] - sorted[i - 1] > 1) result.push('...');
    result.push(sorted[i]);
  }
  return result;
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
