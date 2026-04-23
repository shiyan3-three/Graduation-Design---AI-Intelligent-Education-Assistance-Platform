import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchAnalyticsReport, fetchAnalyticsTags } from '../../services/api.js';
import styles from './LearningPage.module.css';

export function LearningPage() {
  const [loading, setLoading] = useState(true);
  const [hotspots, setHotspots] = useState([]);
  const [tags, setTags] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([fetchAnalyticsReport(), fetchAnalyticsTags()])
      .then(([reportRes, tagsRes]) => {
        setHotspots(reportRes.payload?.data?.focus_areas ?? []);
        setTags(tagsRes.payload?.data?.items ?? []);
      })
      .catch(() => {
        setError('学习记录加载失败，请稍后重试');
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className={styles.pageContainer}>
      <header className={styles.pageHeader}>
        <h1>学习记录</h1>
        <p>记录你与 AI 的每一次知识探索</p>
      </header>

      {error && (
        <div className={styles.errorState} role="alert">
          {error}
        </div>
      )}

      {/* 区块一：近期学习热点 */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>近期学习热点</h2>

        {loading ? (
          <div className={styles.hotspotGrid}>
            <div className={`${styles.skeleton} ${styles.skeletonCard}`} />
            <div className={`${styles.skeleton} ${styles.skeletonCard}`} />
            <div className={`${styles.skeleton} ${styles.skeletonCard}`} />
          </div>
        ) : hotspots.length === 0 ? (
          <EmptyState message="暂无热点数据" />
        ) : (
          <div className={styles.hotspotGrid}>
            {hotspots.map((item) => (
              <HotspotCard
                key={item.rank}
                tag={item.tag}
                count={item.count}
                rank={item.rank}
              />
            ))}
          </div>
        )}
      </section>

      {/* 区块二：全部知识点标签 */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>全部知识点标签</h2>
          {!loading && tags.length > 0 && (
            <span className={styles.tagTotal}>共 {tags.length} 个标签</span>
          )}
        </div>

        {loading ? (
          <div className={styles.tagList}>
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className={`${styles.skeleton} ${styles.skeletonRow}`} />
            ))}
          </div>
        ) : tags.length === 0 ? (
          <EmptyState
            message="您还没有积累知识点标签"
            linkTo="/chat"
            linkText="去和 AI 对话"
          />
        ) : (
          <div className={styles.tagList}>
            {tags.map((item) => (
              <TagListItem key={item.tag} tag={item.tag} count={item.count} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function HotspotCard({ tag, count, rank }) {
  const badgeClass =
    rank === 1 ? styles.rankBadge1 : rank === 2 ? styles.rankBadge2 : styles.rankBadge3;

  return (
    <div className={styles.hotspotCard}>
      <div className={`${styles.rankBadge} ${badgeClass}`}>No.{rank}</div>
      <div className={styles.hotspotTag}>{tag}</div>
      <div className={styles.hotspotCount}>讨论 {count} 次</div>
    </div>
  );
}

function TagListItem({ tag, count }) {
  return (
    <div className={styles.listItem}>
      <span className={styles.itemTitle}>{tag}</span>
      <span className={`${styles.badge} ${styles.primary}`}>{count} 次</span>
    </div>
  );
}

function EmptyState({ message, linkTo, linkText }) {
  return (
    <div className={styles.emptyState}>
      <p>{message}</p>
      {linkTo && (
        <Link to={linkTo} className={styles.primaryBtn}>
          {linkText}
        </Link>
      )}
    </div>
  );
}
