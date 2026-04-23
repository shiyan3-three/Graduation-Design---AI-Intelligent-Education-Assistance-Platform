import { useState, useRef, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useOnClickOutside } from '../../hooks/useOnClickOutside.js';
import { clearAuthSession } from '../../services/api.js';
import { isStoredAdmin, readStoredUser } from '../../admin-access.js';
import styles from './GlobalHeader.module.css';

export function GlobalHeader({ theme, onToggleTheme }) {
  const [isOpen, setIsOpen] = useState(false);
  const [user, setUser] = useState(() => readStoredUser());
  const dropdownRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    const refreshUser = () => setUser(readStoredUser());
    refreshUser();
    window.addEventListener('storage', refreshUser);
    window.addEventListener('edu-user-updated', refreshUser);
    return () => {
      window.removeEventListener('storage', refreshUser);
      window.removeEventListener('edu-user-updated', refreshUser);
    };
  }, []);

  useOnClickOutside(dropdownRef, () => {
    setIsOpen(false);
  });

  const toggleDropdown = (event) => {
    event.stopPropagation();
    setIsOpen((prev) => !prev);
  };

  const handleAction = (action) => {
    setIsOpen(false);
    switch (action) {
      case 'admin':
        navigate('/admin');
        break;
      case 'settings':
        console.log('Open settings');
        break;
      case 'preferences':
        console.log('Open preferences');
        break;
      case 'switch_account':
        console.log('Switch account');
        break;
      case 'logout':
        clearAuthSession();
        navigate('/login', { replace: true });
        break;
      default:
        break;
    }
  };

  const username = user.username || 'User';
  const canShowAdminEntry = user.is_admin === true && isStoredAdmin();

  return (
    <>
      <header className={styles.globalHeader}>
        <div className={styles.headerContent}>
          <NavLink to="/" className={styles.logo}>AI 智能辅导平台</NavLink>

          <nav className={styles.navLinks}>
            <NavLink
              to="/"
              className={({ isActive }) => isActive ? `${styles.navLink} ${styles.active}` : styles.navLink}
              end
            >
              首页
            </NavLink>
            <NavLink
              to="/chat"
              className={({ isActive }) => isActive ? `${styles.navLink} ${styles.active}` : styles.navLink}
            >
              智能辅导
            </NavLink>
            <NavLink
              to="/learning"
              className={({ isActive }) => isActive ? `${styles.navLink} ${styles.active}` : styles.navLink}
            >
              学习记录
            </NavLink>
            <NavLink
              to="/recommend"
              className={({ isActive }) => isActive ? `${styles.navLink} ${styles.active}` : styles.navLink}
            >
              靶向推荐
            </NavLink>
          </nav>

          <div className={`${styles.userDropdownContainer} ${isOpen ? styles.isOpen : ''}`} ref={dropdownRef}>
            <button className={styles.usernameBtn} onClick={toggleDropdown}>
              <span>{username}</span>
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
              </svg>
            </button>

            <div className={styles.dropdownMenu}>
              {canShowAdminEntry && (
                <>
                  <button
                    className={`${styles.dropdownItem} ${styles.adminItem}`}
                    onClick={() => handleAction('admin')}
                  >
                    🛡 管理后台
                  </button>
                  <div className={styles.dropdownDivider}></div>
                </>
              )}
              <button className={styles.dropdownItem} onClick={() => handleAction('settings')}>个人设置</button>
              <button className={styles.dropdownItem} onClick={() => handleAction('preferences')}>系统偏好</button>
              <div className={styles.dropdownDivider}></div>
              <button className={styles.dropdownItem} onClick={() => handleAction('switch_account')}>切换账号</button>
              <button className={`${styles.dropdownItem} ${styles.danger}`} onClick={() => handleAction('logout')}>退出账号</button>
            </div>
          </div>
        </div>
      </header>

      {onToggleTheme && (
        <button
          className={styles.themeToggle}
          onClick={onToggleTheme}
          aria-label="Toggle Theme"
        >
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
      )}
    </>
  );
}
