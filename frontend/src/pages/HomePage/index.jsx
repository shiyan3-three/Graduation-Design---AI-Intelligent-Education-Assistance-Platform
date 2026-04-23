import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  fetchAnalyticsReport,
  fetchAnalyticsSummary,
  fetchAnalyticsTags,
  fetchRecommend,
  fetchSessions,
} from '../../services/api.js';
import { getRecommendPreview } from '../../home-dashboard.js';
import styles from './HomePage.module.css';

const RANK_SEVERITY = { 1: 'danger', 2: 'warning', 3: 'success' };
const RANK_LABEL   = { 1: '急需攻克', 2: '强化练习', 3: '巩固提升' };

function extractData(result, key) {
  if (!result || result.status !== 'fulfilled') return undefined;
  const data = result.value && result.value.payload && result.value.payload.data;
  return key ? (data && data[key]) : data;
}

function formatSessionTime(dateStr) {
  if (!dateStr) return '未知时间';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '未知时间';
  const diffDays = Math.floor((Date.now() - d.getTime()) / 86400000);
  if (diffDays === 0) {
    const h = String(d.getHours()).padStart(2, '0');
    const m = String(d.getMinutes()).padStart(2, '0');
    return `今天 ${h}:${m}`;
  }
  if (diffDays === 1) return '昨天';
  if (diffDays < 30) return `${diffDays} 天前`;
  return `${Math.floor(diffDays / 30)} 个月前`;
}

export function HomePage() {
  const [user, setUser] = useState({ username: 'User', grade: '', subject: '' });
  const [summary, setSummary]           = useState(null);
  const [tagItems, setTagItems]         = useState(null);
  const [focusAreas, setFocusAreas]     = useState(null);
  const [sessionItems, setSessionItems] = useState(null);
  const [pendingRecs, setPendingRecs]   = useState(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem('edu_user');
      if (raw) setUser(JSON.parse(raw));
    } catch (_) {}
  }, []);

  useEffect(() => {
    Promise.allSettled([
      fetchAnalyticsTags(),
      fetchAnalyticsSummary(),
      fetchAnalyticsReport(),
      fetchSessions(),
      fetchRecommend(),
    ]).then(([tagsRes, summaryRes, reportRes, sessionsRes, recommendRes]) => {
      setTagItems(extractData(tagsRes, 'items') || []);
      setSummary(extractData(summaryRes) || {});
      setFocusAreas(extractData(reportRes, 'focus_areas') || []);
      setSessionItems((extractData(sessionsRes, 'items') || []).slice(0, 4));
      const allRecs = extractData(recommendRes, 'items') || [];
      setPendingRecs(allRecs.filter((i) => i.status === 'pending').slice(0, 2));
    });
  }, []);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? '上午好' : hour < 18 ? '下午好' : '晚上好';
  const gradeStr = user.grade ? ` ${user.grade}` : '';
  const subjectStr = user.subject ? ` ${user.subject}` : '';

  const studyDays     = summary ? String(summary.total_study_days !== undefined ? summary.total_study_days : '—') : '—';
  const tagCount      = tagItems ? String(tagItems.length) : '—';
  const completeRate  = summary
    ? (summary.recommend_complete_rate != null ? `${summary.recommend_complete_rate}%` : '--')
    : '—';
  const streakDays    = summary ? String(summary.streak_days !== undefined ? summary.streak_days : '—') : '—';

  return (
    <div className={styles.dashboardContainer}>
      <header className={styles.pageHeader}>
        <h1 className={styles.greeting}>{greeting}，{user.username}{gradeStr}{subjectStr}</h1>
        <p className={styles.subtitle}>
          基于您最近的学习数据，您的知识掌握度正在稳步提升。继续保持！
        </p>
      </header>

      <section className={styles.metricsGrid}>
        <MetricCard title="累计学习天数" value={studyDays}    unit="天" iconColor="blue"   icon="📅" />
        <MetricCard title="掌握知识点"   value={tagCount}     unit="个" iconColor="green"  icon="📚" />
        <MetricCard title="推荐完成率"   value={completeRate}       iconColor="orange" icon="🎯" />
        <MetricCard title="连续打卡天数" value={streakDays}   unit="天" iconColor="purple" icon="🔥" />
      </section>

      <div className={styles.mainLayout}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>薄弱点诊断</h2>
              <NavLink to="/learning" className={styles.actionLink}>查看完整图谱</NavLink>
            </div>
            <div className={styles.list}>
              {focusAreas === null ? (
                <><div className={styles.skeletonItem} /><div className={styles.skeletonItem} /><div className={styles.skeletonItem} /></>
              ) : focusAreas.length === 0 ? (
                <p className={styles.emptyText}>暂无薄弱点数据，继续对话后将自动分析。</p>
              ) : (
                focusAreas.map((area) => <FocusAreaItem key={area.tag} area={area} />)
              )}
            </div>
          </section>

          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>靶向推荐任务</h2>
              <NavLink to="/recommend" className={styles.actionLink}>全部任务</NavLink>
            </div>
            <div className={styles.list}>
              {pendingRecs === null ? (
                <><div className={styles.skeletonItem} /><div className={styles.skeletonItem} /></>
              ) : pendingRecs.length === 0 ? (
                <p className={styles.emptyText}>
                  暂无待完成的推荐任务。
                  <NavLink to="/chat" className={styles.actionLink}>去对话获取推荐</NavLink>
                </p>
              ) : (
                pendingRecs.map((item) => {
                  const preview = getRecommendPreview(item);
                  return (
                    <RecommendItem key={item.id} title={preview.title} meta={preview.meta} />
                  );
                })
              )}
            </div>
          </section>

        </div>

        <div>
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>最新学习动态</h2>
            </div>
            <div className={styles.timeline}>
              {sessionItems === null ? (
                <><div className={styles.skeletonTimeline} /><div className={styles.skeletonTimeline} /><div className={styles.skeletonTimeline} /></>
              ) : sessionItems.length === 0 ? (
                <p className={styles.emptyText}>
                  暂无学习记录。
                  <NavLink to="/chat" className={styles.actionLink}>去开启第一次对话</NavLink>
                </p>
              ) : (
                sessionItems.map((session) => (
                  <TimelineItem
                    key={session.id}
                    time={formatSessionTime(session.updated_at || session.created_at)}
                    content={session.title || '未命名会话'}
                  />
                ))
              )}
            </div>
          </section>
        </div>

      </div>
    </div>
  );
}

function MetricCard({ title, value, unit, iconColor, icon }) {
  const displayValue = (value === '—' || value === '--') ? value : `${value}${unit ? ` ${unit}` : ''}`;
  return (
    <div className={styles.metricCard}>
      <div className={styles.metricHeader}>
        <span className={styles.metricTitle}>{title}</span>
        <div className={`${styles.metricIcon} ${styles[iconColor]}`}>{icon}</div>
      </div>
      <div className={styles.metricValue}>{displayValue}</div>
    </div>
  );
}

function FocusAreaItem({ area }) {
  const severity     = RANK_SEVERITY[area.rank] || 'success';
  const severityText = RANK_LABEL[area.rank]    || '巩固提升';
  return (
    <div className={styles.listItem}>
      <div className={styles.itemInfo}>
        <div className={styles.itemTitle}>{area.tag}</div>
        <div className={styles.itemMeta}><span>提问 {area.count} 次</span></div>
      </div>
      <span className={`${styles.badge} ${styles[severity]}`}>{severityText}</span>
    </div>
  );
}

function RecommendItem({ title, meta }) {
  return (
    <div className={styles.listItem}>
      <div className={styles.itemInfo}>
        <div className={styles.itemTitle}>{title}</div>
        {meta ? <div className={styles.itemMeta}><span>{meta}</span></div> : null}
      </div>
      <NavLink to="/recommend" className={styles.primaryBtn}>去练习</NavLink>
    </div>
  );
}

function TimelineItem({ time, content }) {
  return (
    <div className={styles.timelineItem}>
      <div className={styles.timelineTime}>{time}</div>
      <div className={styles.timelineContent}>{content}</div>
    </div>
  );
}
