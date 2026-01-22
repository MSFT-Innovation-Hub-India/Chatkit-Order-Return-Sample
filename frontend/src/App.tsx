import { ChatKit, useChatKit } from '@openai/chatkit-react';
import { useState, useEffect, CSSProperties } from 'react';
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

  // Load branding from backend
  useEffect(() => {
    fetch('/api/branding')
      .then(res => res.json())
      .then(data => setBranding(data))
      .catch(err => console.error('Failed to load branding:', err));
  }, []);

  // ChatKit hook - connects to our self-hosted backend
  const { control } = useChatKit({
    api: {
      // For self-hosted ChatKit, we use url and domainKey
      url: '/chatkit',
      domainKey: 'localhost', // Local development
    },
    // Start screen customization - use branding prompts or defaults
    startScreen: {
      greeting: branding?.tagline || 'Your AI-powered returns management assistant',
      prompts: branding?.prompts || defaultPrompts,
    },
    // Header configuration
    header: {
      title: {
        text: branding?.name || 'Order Returns',
      },
    },
    // Composer configuration
    composer: {
      placeholder: branding?.prompts 
        ? "Type your message or click a prompt to start..."
        : "Try: 'I need to return an item' to start the returns process...",
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
      </header>

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
          <ChatKit control={control} className="chatkit-widget" />
        </div>
      </div>
    </div>
  );
}

export default App;
