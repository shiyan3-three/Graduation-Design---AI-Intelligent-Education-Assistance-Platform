import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { loginUser, registerUser, saveAuthSession } from '../services/api.js';
import { getNextTheme, resolveInitialTheme, THEME_STORAGE_KEY } from '../theme-state.js';
import styles from './AuthPage.module.css';

export function AuthPage() {
  const navigate = useNavigate();
  const location = useLocation();
  // Using two separate states allows us to delay the enter animation!
  const [showLogin, setShowLogin] = useState(location.pathname !== '/register');
  const [showRegister, setShowRegister] = useState(location.pathname === '/register');

  const [loginForm, setLoginForm] = useState({ username: '', password: '' });
  const [registerForm, setRegisterForm] = useState({ 
    username: '', 
    password: '', 
    confirmPassword: '',
    grade: '', 
    subject: '' 
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Theme Management
  const [theme, setTheme] = useState(() => resolveInitialTheme(() => localStorage.getItem(THEME_STORAGE_KEY)));

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => getNextTheme(prev));
  };

  // Sync state with url changes without delay if routed externally
  useEffect(() => {
    const isLoginPage = location.pathname !== '/register';
    setShowLogin(isLoginPage);
    setShowRegister(!isLoginPage);
    setError('');
  }, [location.pathname]);

  const handleSwitch = (target) => {
    setError('');
    
    // Delayed switch to create the staggered waterfall effect
    if (target === 'register') {
      setShowLogin(false);
      setTimeout(() => {
        setShowRegister(true);
        navigate('/register', { replace: true });
      }, 500);
    } else {
      setShowRegister(false);
      setTimeout(() => {
        setShowLogin(true);
        navigate('/login', { replace: true });
      }, 500);
    }
  };

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    if (!loginForm.username || !loginForm.password) {
      setError('请输入账号和密码');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const { response, payload } = await loginUser(loginForm.username, loginForm.password);
      setLoading(false);

      if (response?.ok && payload?.success) {
        // payload.data.user contains the full user profile per backend contract
        const user = payload.data?.user ?? {};
        saveAuthSession(payload.data.token, {
          id: user.id,
          username: user.username ?? loginForm.username,
          grade: user.grade ?? '',
          subject: user.subject ?? '',
          is_admin: user.is_admin === true,
        });
        navigate('/', { replace: true });
      } else {
        setError(payload?.message || '登录失败，请检查账号与密码');
      }
    } catch (_) {
      setLoading(false);
      setError('无法连接后端服务，请确认后端已启动');
    }
  };

  const passwordMismatch = registerForm.confirmPassword && registerForm.password !== registerForm.confirmPassword;
  const isRegisterFormValid = registerForm.username && registerForm.password && !passwordMismatch;

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    if (!registerForm.username || !registerForm.password || !registerForm.confirmPassword) {
      setError('请提供账户名、密码和确认密码');
      return;
    }
    if (passwordMismatch) {
      setError('两次填写的密码不一致，请重试');
      return;
    }

    setLoading(true);
    setError('');
    const finalGrade = registerForm.grade.trim() || '未提供';
    const finalSubject = registerForm.subject.trim() || '未提供';

    try {
      const { response, payload } = await registerUser(
        registerForm.username,
        registerForm.password,
        finalGrade,
        finalSubject
      );
      setLoading(false);

      if (response?.ok && payload?.success) {
        setLoginForm((prev) => ({ ...prev, username: registerForm.username, password: '' }));
        handleSwitch('login');
        setTimeout(() => setError('注册成功，请使用新账号登录。'), 700);
      } else {
        setError(payload?.message || '注册失败');
      }
    } catch (_) {
      setLoading(false);
      setError('无法连接后端服务，请确认后端已启动');
    }
  };

  return (
    <div className={styles.pageContainer}>
      <div className={styles.container}>
        
        {error && <div className={styles.errorMessage}>{error}</div>}

        {/* LOGIN FORM */}
        <div className={`${styles.formWrapper} ${showLogin ? styles.active : styles.exit}`} id="login">
          <form onSubmit={handleLoginSubmit}>
            <h1 className={styles.item}>登录账号</h1>
            <p className={styles.item}>Access your account</p>
            
            <input 
              type="text" 
              placeholder="账号" 
              className={styles.item}
              value={loginForm.username}
              onChange={e => setLoginForm(p => ({ ...p, username: e.target.value }))}
              disabled={loading}
              autoComplete="username"
            />
            <input 
              type="password" 
              placeholder="密码" 
              className={styles.item}
              value={loginForm.password}
              onChange={e => setLoginForm(p => ({ ...p, password: e.target.value }))}
              disabled={loading}
              autoComplete="current-password"
            />
            
            <button type="submit" className={styles.item} disabled={loading}>
              {loading ? 'Processing...' : 'Sign In'}
            </button>
            <div className={`${styles.switchText} ${styles.item}`} onClick={() => handleSwitch('register')}>
              去注册 <span>→</span>
            </div>
          </form>
        </div>

        {/* REGISTER FORM */}
        <div className={`${styles.formWrapper} ${showRegister ? styles.active : styles.exit}`} id="register">
          <form onSubmit={handleRegisterSubmit}>
            <h1 className={styles.item}>注册账号</h1>
            <p className={styles.item}>Create new account</p>
            
            <input 
              type="text" 
              placeholder="账号 *" 
              className={styles.item}
              value={registerForm.username}
              onChange={e => {
                setRegisterForm(p => ({ ...p, username: e.target.value }));
                setError('');
              }}
              disabled={loading}
            />
            <input 
              type="password" 
              placeholder="设置密码 *" 
              className={styles.item}
              value={registerForm.password}
              onChange={e => {
                setRegisterForm(p => ({ ...p, password: e.target.value }));
                setError('');
              }}
              disabled={loading}
            />
            <input 
              type="password" 
              placeholder="重复检查密码 *" 
              className={`${styles.item} ${passwordMismatch ? styles.inputError : ''}`}
              value={registerForm.confirmPassword}
              onChange={e => {
                setRegisterForm(p => ({ ...p, confirmPassword: e.target.value }));
                setError('');
              }}
              disabled={loading}
            />
            {passwordMismatch && (
              <div className={`${styles.item} ${styles.inlineError}`}>
                两次填写的密码不一致
              </div>
            )}
            
            <div style={{ display: 'flex', gap: '8px', marginTop: '16px' }} className={styles.item}>
               <input 
                type="text" 
                placeholder="所属年级 (可选)" 
                style={{ marginBottom: '16px' }}
                value={registerForm.grade}
                onChange={e => setRegisterForm(p => ({ ...p, grade: e.target.value }))}
                disabled={loading}
              />
              <input 
                type="text" 
                placeholder="主修学科 (可选)" 
                style={{ marginBottom: '16px' }}
                value={registerForm.subject}
                onChange={e => setRegisterForm(p => ({ ...p, subject: e.target.value }))}
                disabled={loading}
              />
            </div>
            
            <button type="submit" className={styles.item} disabled={loading || passwordMismatch}>
               {loading ? 'Processing...' : 'Create Account'}
            </button>
            <div className={`${styles.switchText} ${styles.item}`} onClick={() => handleSwitch('login')}>
              <span>←</span> 返回登录
            </div>
          </form>
        </div>

      </div>

      <button className={styles.themeToggle} onClick={toggleTheme} aria-label="Toggle Theme">
        🌓
      </button>
    </div>
  );
}
