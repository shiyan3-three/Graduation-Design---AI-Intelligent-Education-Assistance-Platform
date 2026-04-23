import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { fetchRecommend, submitRecommendFeedback } from '../../services/api.js';
import styles from './RecommendPage.module.css';

function stripHtml(html) {
  return (html ?? '')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<[^>]+>/g, '');
}

export function RecommendPage() {
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [questionStates, setQuestionStates] = useState({});
  const [feedbackLoading, setFeedbackLoading] = useState({});
  const [error, setError] = useState('');

  const loadRecommend = useCallback(() => {
    setLoading(true);
    setItems([]);
    setCurrentIndex(0);
    setQuestionStates({});
    setFeedbackLoading({});
    setError('');
    fetchRecommend()
      .then(({ payload }) => {
        setItems(payload?.data?.items ?? []);
      })
      .catch(() => {
        setError('推荐题目加载失败，请稍后重试');
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadRecommend();
  }, [loadRecommend]);

  const getQState = (id) =>
    questionStates[id] ?? { selectedOption: null, showAnswer: false };

  const patchQState = (id, patch) => {
    setQuestionStates((prev) => ({
      ...prev,
      [id]: { ...getQState(id), ...patch },
    }));
  };

  const handleSelectOption = (itemId, optKey) => {
    patchQState(itemId, { selectedOption: optKey });
  };

  const handleToggleAnswer = (itemId) => {
    const state = getQState(itemId);
    patchQState(itemId, { showAnswer: !state.showAnswer });
  };

  const handleFeedback = async (item, status) => {
    if (feedbackLoading[item.id]) return;
    setFeedbackLoading((prev) => ({ ...prev, [item.id]: true }));
    try {
      const { payload } = await submitRecommendFeedback(item.id, status);
      if (payload?.success) {
        setItems((prev) =>
          prev.map((i) => (i.id === item.id ? { ...i, status } : i))
        );
      }
    } finally {
      setFeedbackLoading((prev) => ({ ...prev, [item.id]: false }));
    }
  };

  const allProcessed =
    items.length > 0 && items.every((i) => i.status !== 'pending');
  const uniqueTopics = [...new Set(items.map((i) => i.recommended_topic))];

  /* ── Loading skeleton ────────────────────────────────────────────────── */
  if (loading) {
    return (
      <div className={styles.pageWrapper}>
        <div className={styles.headerArea}>
          <div>
            <h1>专属题目推荐</h1>
            <p>基于知识点追踪，今日为您生成了巩固练习</p>
          </div>
        </div>
        <div className={styles.splitLayout}>
          <div className={styles.section}>
            <div className={styles.sectionTitle}>
              <div className={styles.sectionTitleLeft}>待办任务列</div>
            </div>
            <div className={styles.taskListContainer}>
              <div className={styles.skeletonItem} />
              <div className={styles.skeletonItem} />
            </div>
          </div>
          <div className={`${styles.section} ${styles.detailPanel}`}>
            <div className={styles.skeletonLine} style={{ width: '35%', height: '14px' }} />
            <div className={styles.skeletonLine} style={{ width: '85%', height: '22px' }} />
            <div className={styles.skeletonLine} style={{ height: '54px' }} />
            <div className={styles.skeletonLine} style={{ height: '54px' }} />
            <div className={styles.skeletonLine} style={{ height: '54px' }} />
          </div>
        </div>
      </div>
    );
  }

  /* ── Empty state ─────────────────────────────────────────────────────── */
  if (items.length === 0) {
    return (
      <div className={styles.pageWrapper}>
        <div className={styles.headerArea}>
          <div>
            <h1>专属题目推荐</h1>
            <p>基于知识点追踪，今日为您生成了巩固练习</p>
          </div>
        </div>
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}>📚</div>
          <p className={styles.emptyText}>{error || '暂无推荐题目'}</p>
          <p className={styles.emptyHint}>
            {error || '先与 AI 对话，积累知识点后即可生成专属练习'}
          </p>
          {error ? (
            <button className={styles.btnPrimary} onClick={loadRecommend}>
              重新加载
            </button>
          ) : (
            <Link to="/chat" className={styles.btnPrimary}>去和 AI 对话</Link>
          )}
        </div>
      </div>
    );
  }

  /* ── All-done state ──────────────────────────────────────────────────── */
  if (allProcessed) {
    return (
      <div className={styles.pageWrapper}>
        <div className={styles.headerArea}>
          <div>
            <h1>专属题目推荐</h1>
            <p>基于知识点追踪，今日为您生成了巩固练习</p>
          </div>
        </div>
        <div className={styles.doneState}>
          <div className={styles.doneIcon}>🎉</div>
          <h2>本轮推荐已全部处理</h2>
          <p>继续与 AI 对话，积累更多知识点后可刷新推荐</p>
          <button className={styles.btnPrimary} onClick={loadRecommend}>
            刷新推荐
          </button>
        </div>
      </div>
    );
  }

  /* ── Main split layout ───────────────────────────────────────────────── */
  const currentItem = items[currentIndex] ?? items[0];
  const qState = getQState(currentItem.id);
  const effectiveShowAnswer =
    qState.showAnswer || currentItem.status !== 'pending';
  const options = Object.entries(currentItem.question_payload.options);
  const correctAnswer = currentItem.question_payload.answer;

  const getOptClass = (key) => {
    const classes = [styles.optBtn];
    if (qState.selectedOption === key) {
      if (effectiveShowAnswer) {
        classes.push(key === correctAnswer ? styles.correct : styles.wrong);
      } else {
        classes.push(styles.selected);
      }
    } else if (effectiveShowAnswer && key === correctAnswer) {
      classes.push(styles.correct);
    }
    return classes.join(' ');
  };

  const isPending = currentItem.status === 'pending';
  const isFeedbackBusy = !!feedbackLoading[currentItem.id];

  return (
    <div className={styles.pageWrapper}>
      {/* Header */}
      <div className={styles.headerArea}>
        <div>
          <h1>专属题目推荐</h1>
          <p>基于知识点追踪，今日为您生成了巩固练习</p>
        </div>
      </div>

      {/* Context banner */}
      <div className={styles.contextBanner}>
        <span className={styles.contextLabel}>本轮基于：</span>
        <div className={styles.contextTags}>
          {uniqueTopics.map((topic) => (
            <span key={topic} className={styles.contextTag}>{topic}</span>
          ))}
        </div>
      </div>

      <div className={styles.splitLayout}>
        {/* Left: task list */}
        <div className={styles.section}>
          <div className={styles.sectionTitle}>
            <div className={styles.sectionTitleLeft}>
              待办任务列 ({items.length})
            </div>
          </div>
          <div className={styles.taskListContainer}>
            <div className={styles.taskList}>
              {items.map((item, index) => {
                const tagClass = [
                  styles.taskItemTag,
                  item.status === 'completed' ? styles.tagCompleted : '',
                  item.status === 'skipped' ? styles.tagSkipped : '',
                ].filter(Boolean).join(' ');

                const itemClass = [
                  styles.taskItem,
                  index === currentIndex ? styles.active : '',
                  item.status === 'completed' ? styles.completed : '',
                  item.status === 'skipped' ? styles.skipped : '',
                ].filter(Boolean).join(' ');

                const statusIcon =
                  item.status === 'completed' ? '✔' :
                  item.status === 'skipped'   ? '→' : '●';

                const titlePreview = item.question_payload.question.length > 36
                  ? item.question_payload.question.slice(0, 36) + '…'
                  : item.question_payload.question;

                return (
                  <div
                    key={item.id}
                    className={itemClass}
                    onClick={() => setCurrentIndex(index)}
                  >
                    <div className={tagClass}>
                      {statusIcon} {item.recommended_topic}
                    </div>
                    <div className={styles.taskItemTitle}>{titlePreview}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right: question detail */}
        <div className={`${styles.section} ${styles.detailPanel}`}>
          <div className={styles.qType}>{currentItem.recommended_topic}</div>

          {!isPending && (
            <div className={currentItem.status === 'completed' ? styles.badgeCompleted : styles.badgeSkipped}>
              {currentItem.status === 'completed' ? '✔ 已完成' : '→ 已跳过'}
            </div>
          )}
          <div className={styles.qTitle}>{currentItem.question_payload.question}</div>

          <div className={styles.optionsList}>
            {options.map(([key, text]) => (
              <button
                key={key}
                className={getOptClass(key)}
                onClick={() => isPending && handleSelectOption(currentItem.id, key)}
                disabled={!isPending}
              >
                <span className={styles.optLetter}>{key}.</span>
                <span>{text}</span>
              </button>
            ))}
          </div>

          {effectiveShowAnswer && (
            <div className={styles.aiAnalysis}>
              <div className={styles.aiHeader}>✨ Agent 解析与知识链接</div>
              <div
                className={styles.aiBody}
              >
                {stripHtml(currentItem.question_payload.explanation)}
              </div>
            </div>
          )}

          <div className={styles.actionBar}>
            {isPending && (
              <button
                className={styles.btnGhost}
                onClick={() => handleToggleAnswer(currentItem.id)}
              >
                {qState.showAnswer ? '收起答案' : '查看答案'}
              </button>
            )}
            <button
              className={styles.btnGhost}
              onClick={() => handleFeedback(currentItem, 'skipped')}
              disabled={!isPending || isFeedbackBusy}
            >
              跳过
            </button>
            <button
              className={styles.btnPrimary}
              onClick={() => handleFeedback(currentItem, 'completed')}
              disabled={!isPending || isFeedbackBusy}
            >
              ✓ 完成
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
