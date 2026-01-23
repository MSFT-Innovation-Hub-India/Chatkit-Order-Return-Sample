import { ChatKit, useChatKit } from '@openai/chatkit-react';
import { useState, useEffect, CSSProperties, FormEvent } from 'react';
import './App.css';

// Branding configuration type
interface Branding {
  name: string;
  tagline: string;
  logoUrl: string;
  primaryColor: string;
  faviconUrl: string;
  prompts?: { label: string; prompt: string }[];
  howToUse?: string[];
  features?: string[];
}

// User type
interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  membership_tier: string;
}

// Auth state
interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
}

// Default prompts for Order Returns (fallback)
const defaultPrompts = [
  { label: '📦 Check order status', prompt: 'I want to check the status of my order' },
  { label: '🔄 Start a return', prompt: 'I need to return an item from my order' },
  { label: '💬 Track my return', prompt: 'What is the status of my return?' },
  { label: '❓ What can you do?', prompt: 'What can you help me with?' },
];

const defaultHowToUse = [
  '💬 Ask about your orders or returns',
  '📦 Provide your order number to look up details',
  '🔄 Request returns for eligible items',
  '✅ Follow the guided return process',
];

const defaultFeatures = [
  '🎨 Interactive widget UI',
  '📦 Order lookup and details',
  '🔄 Easy returns processing',
  '📋 Return status tracking',
  '💾 Persistent storage',
  '☁️ Azure OpenAI powered',
];

// Helper to adjust color brightness
function adjustColor(color: string, amount: number): string {
  const hex = color.replace('#', '');
  const num = parseInt(hex, 16);
  const r = Math.min(255, Math.max(0, (num >> 16) + amount));
  const g = Math.min(255, Math.max(0, ((num >> 8) & 0x00FF) + amount));
  const b = Math.min(255, Math.max(0, (num & 0x0000FF) + amount));
  return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
}

function App() {
  const [branding, setBranding] = useState<Branding | null>(null);
  const [auth, setAuth] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    token: null,
  });
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [chatkitKey, setChatkitKey] = useState(0);
  const [clientError, setClientError] = useState<string | null>(null);
  const debugEnabled = new URLSearchParams(window.location.search).has('debug');
  const chatkitDomainKey = import.meta.env.VITE_CHATKIT_DOMAIN_KEY
    || (window.location.hostname === 'localhost'
      ? 'localhost'
      : window.location.hostname);

  // Load branding from backend
  useEffect(() => {
    fetch('/api/branding')
      .then(res => res.json())
      .then(data => setBranding(data))
      .catch(err => console.error('Failed to load branding:', err));
  }, []);

  // Capture client-side errors for debugging
  useEffect(() => {
    if (!debugEnabled) return;

    const onError = (event: ErrorEvent) => {
      setClientError(event.message || 'Unknown error');
    };

    const onUnhandledRejection = (event: PromiseRejectionEvent) => {
      setClientError(String(event.reason) || 'Unhandled promise rejection');
    };

    window.addEventListener('error', onError);
    window.addEventListener('unhandledrejection', onUnhandledRejection);

    return () => {
      window.removeEventListener('error', onError);
      window.removeEventListener('unhandledrejection', onUnhandledRejection);
    };
  }, [debugEnabled]);

  useEffect(() => {
    if (window.location.hostname !== 'localhost' && !import.meta.env.VITE_CHATKIT_DOMAIN_KEY) {
      const message = 'Missing VITE_CHATKIT_DOMAIN_KEY for this domain. Register the domain in OpenAI Platform and rebuild.';
      console.warn(message);
      if (debugEnabled) {
        setClientError(message);
      }
    }
  }, [debugEnabled]);

  // Check for existing session on mount
  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      // Verify token is still valid
      fetch('/api/auth/me', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
        .then(res => res.json())
        .then(data => {
          if (data.authenticated) {
            setAuth({
              isAuthenticated: true,
              user: data.user,
              token: token,
            });
          } else {
            localStorage.removeItem('auth_token');
          }
        })
        .catch(() => localStorage.removeItem('auth_token'));
    }
  }, []);

  // Handle login
  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    setLoginError(null);
    setIsLoggingIn(true);

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loginForm),
      });
      const data = await res.json();

      if (data.success) {
        localStorage.setItem('auth_token', data.token);
        // Also set cookie for ChatKit requests (which can't use custom headers)
        const secureFlag = window.location.protocol === 'https:' ? '; Secure' : '';
        document.cookie = `auth_token=${data.token}; path=/; max-age=86400; SameSite=Lax${secureFlag}`;
        setAuth({
          isAuthenticated: true,
          user: data.user,
          token: data.token,
        });
        setLoginForm({ email: '', password: '' });
        // Reinitialize ChatKit without full page reload
        setChatkitKey(prev => prev + 1);
      } else {
        setLoginError(data.message || 'Login failed');
      }
    } catch (err) {
      setLoginError('An error occurred. Please try again.');
    } finally {
      setIsLoggingIn(false);
    }
  };

  // Handle logout
  const handleLogout = async () => {
    if (auth.token) {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${auth.token}` },
      });
    }
    localStorage.removeItem('auth_token');
    // Clear the auth cookie
    document.cookie = 'auth_token=; path=/; max-age=0; SameSite=Lax';
    setAuth({ isAuthenticated: false, user: null, token: null });
    // Reinitialize ChatKit without full page reload
    setChatkitKey(prev => prev + 1);
  };

  // ChatKit hook - connects to our self-hosted backend
  // Auth token is passed via cookie (set on login) for ChatKit requests
  const { control } = useChatKit({
    api: {
      // For self-hosted ChatKit, we use url and domainKey
      url: '/chatkit',
      domainKey: chatkitDomainKey,
    },
    // Start screen customization - use branding prompts or defaults
    startScreen: {
      greeting: auth.isAuthenticated && auth.user
        ? `Welcome back, ${auth.user.first_name}! How can I help with your returns today?`
        : (branding?.tagline || 'Your AI-powered returns management assistant'),
      prompts: branding?.prompts || defaultPrompts,
    },
    // Header configuration - minimal since we have our own custom header
    header: {
      title: {
        text: '',
      },
    },
    // Thread item actions - enable feedback buttons (thumbs up/down)
    threadItemActions: {
      feedback: true,  // Show thumbs up/down on assistant messages
      retry: true,     // Allow retrying failed responses
    },
    // Composer configuration
    composer: {
      placeholder: auth.isAuthenticated
        ? "Ask about your orders or start a return..."
        : (branding?.prompts 
            ? "Type your message or click a prompt to start..."
            : "Try: 'I need to return an item' to start the returns process..."),
    },
  });

  // Dynamic header styles
  const headerStyle: CSSProperties = {
    background: branding?.primaryColor
      ? `linear-gradient(135deg, ${branding.primaryColor}, ${adjustColor(branding.primaryColor, -20)})`
      : 'linear-gradient(135deg, #0078d4, #005a9e)',
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header" style={headerStyle}>
        <div className="header-logo">
          {branding?.logoUrl ? (
            <img src={branding.logoUrl} alt="Logo" />
          ) : (
            <span>📦</span>
          )}
        </div>
        <h1 className="header-title">{branding?.name || 'Order Returns'}</h1>
        <span className="header-tagline">{branding?.tagline || 'AI-Powered Returns Management'}</span>
        
        {/* User info / Login button */}
        <div className="header-auth">
          {auth.isAuthenticated && auth.user ? (
            <div className="user-info">
              <span className="user-badge" data-tier={auth.user.membership_tier}>
                {auth.user.membership_tier}
              </span>
              <span className="user-name">
                {auth.user.first_name} {auth.user.last_name}
              </span>
              <button className="logout-btn" onClick={handleLogout}>
                Logout
              </button>
            </div>
          ) : (
            <span className="guest-label">Guest Mode</span>
          )}
        </div>
      </header>

      {/* Login Modal - Show if not authenticated */}
      {!auth.isAuthenticated && (
        <div className="login-overlay">
          <div className="login-modal">
            <div className="login-header">
              <h2>🔐 Sign In</h2>
              <p>Sign in to access your order history and manage returns</p>
            </div>
            
            <form onSubmit={handleLogin} className="login-form">
              <div className="form-group">
                <label htmlFor="email">Email</label>
                <input
                  type="email"
                  id="email"
                  value={loginForm.email}
                  onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })}
                  placeholder="jane.smith@email.com"
                  required
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="password">Password</label>
                <input
                  type="password"
                  id="password"
                  value={loginForm.password}
                  onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                  placeholder="Enter password"
                  required
                />
              </div>
              
              {loginError && (
                <div className="login-error">
                  ⚠️ {loginError}
                </div>
              )}
              
              <button type="submit" className="login-btn" disabled={isLoggingIn}>
                {isLoggingIn ? 'Signing in...' : 'Sign In'}
              </button>
            </form>
            
            <div className="login-hint">
              <p><strong>Demo Accounts:</strong></p>
              <ul>
                <li>jane.smith@email.com (Gold)</li>
                <li>rjohnson@company.com (Platinum)</li>
                <li>m.garcia@inbox.com (Silver)</li>
              </ul>
              <p>Password for all: <code>demo123</code></p>
            </div>
          </div>
        </div>
      )}

      {/* Main content with sidebar and ChatKit */}
      <div className="main-content">
        {/* Sidebar */}
        <aside className="sidebar">
          <section>
            <h2>📖 How to Use</h2>
            <ul>
              {(branding?.howToUse || defaultHowToUse).map((item, index) => (
                <li key={index}>{item}</li>
              ))}
            </ul>
          </section>

          <section>
            <h2>💡 Try These Prompts</h2>
            <div className="prompt-buttons">
              {(branding?.prompts || defaultPrompts).map((p, index) => (
                <button 
                  key={index} 
                  className="prompt-button"
                  onClick={() => {
                    // Find the composer input and set the value
                    const input = document.querySelector('.chatkit-widget textarea, .chatkit-widget input[type="text"]') as HTMLInputElement | HTMLTextAreaElement;
                    if (input) {
                      input.value = p.prompt;
                      input.dispatchEvent(new Event('input', { bubbles: true }));
                      input.focus();
                    }
                  }}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </section>

          <section>
            <h2>✨ Features</h2>
            <ul>
              {(branding?.features || defaultFeatures).map((item, index) => (
                <li key={index}>{item}</li>
              ))}
            </ul>
          </section>
        </aside>

        {/* ChatKit Component - Official OpenAI ChatKit UI */}
        <div className="chat-container">
          <ChatKit key={chatkitKey} control={control} className="chatkit-widget" />
        </div>
      </div>

      {debugEnabled && (
        <div className="debug-panel">
          <div><strong>Debug:</strong></div>
          <div>Auth: {auth.isAuthenticated ? 'true' : 'false'}</div>
          <div>User: {auth.user?.email || 'none'}</div>
          <div>Hostname: {window.location.hostname}</div>
          <div>ChatKit key: {chatkitKey}</div>
          {clientError && <div style={{ color: '#d00' }}>Error: {clientError}</div>}
        </div>
      )}
    </div>
  );
}

export default App;
