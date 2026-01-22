# ChatKit Order Returns Architecture

This document explains the modular architecture of this ChatKit sample project, the role of the ChatKit server, and provides a guide for implementing use cases.

## Table of Contents

1. [What is ChatKit?](#what-is-chatkit)
2. [Server-Driven UI: The Core Concept](#server-driven-ui-the-core-concept)
3. [How Widget Rendering Works](#how-widget-rendering-works)
4. [Architecture Overview](#architecture-overview)
5. [ChatKit Server: Middleware or Backend?](#chatkit-server-middleware-or-backend)
6. [Production Deployment Patterns](#production-deployment-patterns)
7. [Project Structure](#project-structure)
8. [Core Components](#core-components)
9. [How the Retail Use Case Works](#how-the-retail-use-case-works)
10. [How Widget Actions Work](#how-widget-actions-work-detailed)
11. [Dual-Input Architecture: Text + Widget Convergence](#dual-input-architecture-text--widget-convergence)
12. [Widget Orchestration: How the Flow is Controlled](#widget-orchestration-how-the-flow-is-controlled)
13. [Creating a New Use Case](#creating-a-new-use-case)
14. [Widget Reference](#widget-reference)

---

## What is ChatKit?

ChatKit is OpenAI's protocol for building **self-hosted chat applications** with rich, interactive UIs. It provides:

| Feature | Description |
|---------|-------------|
| **Streaming Protocol** | Real-time message streaming over WebSocket/SSE |
| **Interactive Widgets** | Rich UI components (buttons, forms, checkboxes, cards) |
| **Action Handling** | Server-side handling of user interactions |
| **Thread Management** | Built-in conversation thread persistence |

### ChatKit vs Standard Agent Applications

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STANDARD AGENTIC APPLICATION                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   User  ──►  REST API  ──►  Agent/LLM  ──►  Text Response                   │
│                                                                             │
│   • Text-only responses                                                     │
│   • No built-in UI framework                                                │
│   • Custom frontend needed                                                  │
│   • Request/response pattern                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                       CHATKIT APPLICATION                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   User  ──►  ChatKit UI  ◄──►  ChatKit Server  ──►  Agent/LLM               │
│                  │                    │                                     │
│                  │                    ▼                                     │
│                  │              ┌──────────┐                                │
│                  ◄──────────────┤ Widgets  │ (Buttons, Forms, Cards)        │
│                  │              └──────────┘                                │
│                  │                    │                                     │
│                  ◄────────────────────┘ Actions (Click, Submit, Toggle)     │
│                                                                             │
│   • Rich interactive widgets                                                │
│   • Real-time streaming                                                     │
│   • Built-in UI components                                                  │
│   • Bidirectional communication                                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Differences:**

| Aspect | Standard Agent App | ChatKit App |
|--------|-------------------|-------------|
| **Output** | Text only | Text + Interactive Widgets |
| **Interaction** | One-way (request → response) | Bidirectional (actions ↔ updates) |
| **UI** | Build your own | Pre-built components |
| **Streaming** | Optional | Built-in |
| **State** | Manual | Thread-based |

---

## Server-Driven UI: The Core Concept

ChatKit implements a **Server-Driven UI** architecture. This is a fundamental pattern where:

- **Server (Python)** controls **WHAT** to display
- **Client (React)** controls **HOW** to display it

### The Complete Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          YOUR CODE (Python)                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  widgets.py - Define widget structure                                 │  │
│  │                                                                       │  │
│  │  Card(children=[                                                      │  │
│  │    Title(value="Order Details"),                                      │  │
│  │    Badge(label="Delivered", color="success"),                         │  │
│  │    Button(label="Start Return", color="primary", variant="soft"),     │  │
│  │    ...                                                                │  │
│  │  ])                                                                   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                     │                                       │
│                     Python objects serialized to JSON                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ChatKit Protocol (JSON over SSE)                       │
│                                                                             │
│  {                                                                          │
│    "type": "Card",                                                          │
│    "id": "order_widget_123",                                                │
│    "children": [                                                            │
│      {"type": "Title", "value": "Order Details"},                           │
│      {"type": "Badge", "label": "Delivered", "color": "success"},           │
│      {"type": "Button", "label": "Start Return", "color": "primary", "variant": "soft"}│
│    ]                                                                        │
│  }                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    @openai/chatkit-react (React Library)                    │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  <ChatKitProvider> receives JSON and renders real HTML                │  │
│  │                                                                       │  │
│  │  JSON "Button"  →  <button class="ck-btn ck-btn--success ck-btn--soft">│ │
│  │  JSON "Card"    →  <div class="ck-card">                              │  │
│  │  JSON "Badge"   →  <span class="ck-badge ck-badge--warning">          │  │
│  │                                                                       │  │
│  │  + CSS variables define colors for success, warning, etc.             │  │
│  │  + Handles click events → sends action payloads back to server        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Browser (Final HTML/CSS)                           │
│                                                                             │
│   Actual styled buttons, cards, badges rendered to screen                   │
│   User sees: ┌───────────────────────────────────────┐                      │
│              │  � Order Details   [✅ Delivered]    │                      │
│              │  Nike Air Max 90              $149.99 │                      │
│              │  [Start Return] [Track Package]       │                      │
│              └───────────────────────────────────────┘                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why Changes in Python Affect the UI

When you change widget properties in Python, here's what happens:

```python
# Python code in widgets.py
Button(
    label="✓",
    color="success",      # You change this
    variant="soft",       # And this
)
```

1. **Python serializes**: `{"color": "success", "variant": "soft"}`
2. **React receives** this JSON over the ChatKit protocol
3. **React applies CSS classes**: `class="ck-button ck-button--success ck-button--soft"`
4. **Browser renders** a light green button with dark green checkmark

**You never write CSS.** The React library has pre-built styles for all combinations:

| Color | Variant: `solid` | Variant: `soft` | Variant: `outline` | Variant: `ghost` |
|-------|------------------|-----------------|--------------------| ---------------- |
| `success` | Green bg, white text | Light green bg, dark green text | Green border | Green text only |
| `secondary` | Gray bg, white text | Light gray bg, dark text | Gray border | Gray text only |
| `warning` | Orange bg, white text | Light orange bg, dark text | Orange border | Orange text only |
| `danger` | Red bg, white text | Light red bg, dark text | Red border | Red text only |
| `info` | Teal bg, white text | Light teal bg, dark text | Teal border | Teal text only |

### What Each Part Does

| Component | Package | Responsibilities |
|-----------|---------|------------------|
| **Python Backend** | `openai-chatkit` | Define widget structure, handle actions, integrate with LLM |
| **React Frontend** | `@openai/chatkit-react` | Render widgets, apply styling, send user interactions |
| **ChatKit Protocol** | JSON over SSE | Transport widget definitions and action events |

### Benefits of Server-Driven UI

1. **Change UI without frontend deployment**: Update Python code → restart server → new UI
2. **Consistent rendering**: React library ensures all widgets look correct
3. **Type-safe widgets**: Python classes validate widget properties at creation time
4. **Platform agnostic**: Same Python code could render on web, mobile, or desktop
5. **Simpler frontend**: No custom components needed, just use official library

### Available Widget Styling Options

**Button properties:**
```python
Button(
    label="Click me",           # Button text
    color="success",            # success, secondary, warning, danger, info, primary
    variant="soft",             # solid, soft, outline, ghost
    size="sm",                  # sm, md, lg
)
```

**Badge properties:**
```python
Badge(
    label="3 pending",          # Badge text
    color="warning",            # secondary, success, danger, warning, info, discovery
)
# Note: Badge does NOT support 'primary' color
```

**Checkbox properties:**
```python
Checkbox(
    name="task_1",
    defaultChecked=True,
    onChangeAction=ActionConfig(type="toggle", handler="server", payload={...})
)
# Note: Checkbox styling is controlled by ChatKit React theme, not server
```

---

## How Widget Rendering Works

This is a crucial concept to understand: **widgets are NOT HTML sent from the server**. Instead:

### The Widget Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. SERVER: Build Widget (Python)                                           │
│                                                                             │
│     widget = Card(                                                          │
│         id="order_widget",                                                  │
│         children=[                                                          │
│             Title(id="t1", value="Order #12345", size="lg"),                │
│             Button(id="b1", label="Start Return", color="primary", ...)     │
│         ]                                                                   │
│     )                                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼ SSE Stream (JSON)
┌──────────────────────────────────────────────────────────────────────────────────────┐
│  2. WIRE FORMAT: JSON Widget Definition                                              │
│                                                                                      │
│     {                                                                                │
│       "type": "Card",                                                                │
│       "id": "order_widget",                                                          │
│       "children": [                                                                  │
│         { "type": "Title", "id": "t1", "value": "Order #12345", "size": "lg" },      │
│         { "type": "Button", "id": "b1", "label": "Start Return", "color": "primary" }│
│       ]                                                                              │
│     }                                                                                │
└──────────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼ JavaScript parses JSON
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. CLIENT: Render to HTML (JavaScript)                                     │
│                                                                             │
│     function renderWidgetComponent(component) {                             │
│       switch (component.type.toLowerCase()) {                               │
│         case 'title':                                                       │
│           const h3 = document.createElement('h3');                          │
│           h3.textContent = component.value;                                 │
│           return h3;                                                        │
│         case 'button':                                                      │
│           const btn = document.createElement('button');                     │
│           btn.textContent = component.label;                                │
│           btn.onclick = () => handleWidgetAction(component.onClickAction);  │
│           return btn;                                                       │
│       }                                                                     │
│     }                                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼ DOM elements created
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. BROWSER: Final HTML                                                     │
│                                                                             │
│     <div class="widget-card">                                               │
│       <h3 class="widget-title lg">Order #12345</h3>                         │
│       <button class="widget-button primary">Add</button>                    │
│     </div>                                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Points

1. **Server sends JSON, not HTML** - Widgets are serialized as JSON objects with `type`, `id`, and properties
2. **Client interprets JSON** - The frontend JavaScript has a renderer (`renderWidgetComponent`) that creates DOM elements
3. **Widgets are part of the thread** - Widget data is streamed as thread events alongside text messages
4. **Styling is client-side** - CSS classes are applied by the frontend based on widget properties

### Where is the Frontend Served From?

This project uses **official ChatKit React components** (`@openai/chatkit-react`) for the frontend:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ARCHITECTURE                                        │
│                                                                             │
│   ┌─────────────────────────┐           ┌──────────────────────────────┐    │
│   │  React Frontend         │           │  Python Backend              │    │
│   │  (Vite + TypeScript)    │  HTTP     │  (FastAPI)                   │    │
│   │                         │           │                              │    │
│   │  @openai/chatkit-react  │ ◄────────►│  openai-chatkit              │    │
│   │  <ChatKit control={...}>│  /chatkit │  ChatKitServer               │    │
│   │  useChatKit() hook      │           │  (Protocol + Streaming)      │    │
│   └─────────────────────────┘           └──────────────────────────────┘    │
│                                                  │                          │
│                                                  ▼                          │
│                                         ┌──────────────────────────────┐    │
│                                         │  Azure OpenAI (GPT-4o)       │    │
│                                         └──────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

**FastAPI serves both the React build and API:**

```python
# main.py

# Serve React build (production)
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    # Priority: React build, then fallback to vanilla JS
    if os.path.exists("static/dist/index.html"):
        return FileResponse("static/dist/index.html")
    return FileResponse("static/index.html")

# Serve static assets (JS, CSS, images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ChatKit API endpoint
@app.post("/chatkit")
async def chatkit_endpoint(request: Request):
    result = await server.process(body, {})
    return StreamingResponse(result, media_type="text/event-stream")
```

### Do You Need a Separate Web Server?

| Scenario | Separate Server Needed? | Recommendation |
|----------|------------------------|----------------|
| **This sample (React + ChatKit)** | ❌ No | FastAPI serves React build from `static/dist/` |
| **Development mode** | ⚠️ Two processes | Vite dev server (port 3000) + FastAPI (port 8000) |
| **Production with CDN** | ✅ Yes (recommended) | Static assets on CDN, API on containers |
| **Next.js / SSR frameworks** | ✅ Yes | Needs Node.js server for SSR |

### Official ChatKit React Components

This project uses the **official ChatKit React library** instead of custom widget rendering:

```tsx
// frontend/src/App.tsx
import { ChatKit, useChatKit } from '@openai/chatkit-react';

function App() {
  const { control } = useChatKit({
    api: { apiURL: '/chatkit' },  // Points to Python backend
    theme: 'light',
    newThreadView: {
      greeting: {
        title: 'Order Returns Assistant',
        description: 'I help you with returns and refunds'
      },
      starterPrompts: [
        { label: 'Start a return', prompt: 'I want to return an item' },
        { label: 'Track my order', prompt: 'Where is my order?' }
      ]
    }
  });

  return <ChatKit control={control} />;
}
```

**Key benefits of official ChatKit React:**
- Built-in widget rendering (no custom JavaScript needed)
- TypeScript types for all components
- Automatic theme support
- Thread management built-in
- Sidebar and header components included

### Development Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DEVELOPMENT MODE                                    │
│                                                                             │
│   Terminal 1:                        Terminal 2:                            │
│   python main.py                     cd frontend && npm run dev             │
│   (Backend on :8000)                 (Vite on :3000 with proxy)             │
│                                                                             │
│   Browser: http://localhost:3000                                            │
│   Vite proxies /chatkit and /api to :8000                                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                         PRODUCTION MODE                                      │
│                                                                              │
│   Build: cd frontend && npm run build                                        │
│   (Outputs to static/dist/)                                                  │
│                                                                              │
│   Run: python main.py                                                        │
│   (Serves React build + API on :8000)                                        │
│                                                                              │
│   Browser: http://localhost:8000                                             │
└──────────────────────────────────────────────────────────────────────────────┘
```

### React/Vue Implementation Pattern

If using React or another framework:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     OPTION 1: Single Server (Simple)                        │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    FastAPI Container                                │   │
│   │  ┌──────────────────────┐  ┌─────────────────────────────────────┐  │   │
│   │  │  /chatkit endpoint   │  │  /static (React build output)       │  │   │
│   │  │  (ChatKit API)       │  │  - index.html                       │  │   │
│   │  │                      │  │  - bundle.js (widget renderer)      │  │   │
│   │  │                      │  │  - styles.css                       │  │   │
│   │  └──────────────────────┘  └─────────────────────────────────────┘  │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│   Build: npm run build → copy dist/ to static/                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                 OPTION 2: Separate Hosting (Production)                     │
│                                                                             │
│   ┌─────────────────────────────┐     ┌─────────────────────────────────┐   │
│   │  CDN / Static Hosting       │     │  Container (Azure, AWS, etc.)   │   │
│   │  (Vercel, Cloudflare, S3)   │     │                                 │   │
│   │                             │     │  ┌───────────────────────────┐  │   │
│   │  - index.html               │────►│  │  /chatkit endpoint        │  │   │
│   │  - bundle.js (React app)    │ API │  │  (ChatKit Server + Agent) │  │   │
│   │  - Widget renderer code     │     │  └───────────────────────────┘  │   │
│   └─────────────────────────────┘     └─────────────────────────────────┘   │
│                                                                             │
│   Pros: Global CDN caching, independent deployments                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The Widget Renderer is Client-Side

The critical piece is the **widget renderer** - JavaScript code that converts JSON to DOM:

```javascript
// This is what makes widgets work - must be in your frontend code
function renderWidgetComponent(component) {
    const type = component.type.toLowerCase();
    
    switch (type) {
        case 'card':
            const card = document.createElement('div');
            card.className = 'widget-card';
            for (const child of component.children) {
                card.appendChild(renderWidgetComponent(child));
            }
            return card;
            
        case 'button':
            const btn = document.createElement('button');
            btn.textContent = component.label;
            btn.className = `widget-button ${component.color}`;
            btn.onclick = () => handleWidgetAction(component.onClickAction);
            return btn;
            
        // ... other component types
    }
}
```

If you use React, you'd write this as React components:

```jsx
// React equivalent
function WidgetRenderer({ component }) {
  switch (component.type.toLowerCase()) {
    case 'card':
      return (
        <div className="widget-card">
          {component.children.map(child => 
            <WidgetRenderer key={child.id} component={child} />
          )}
        </div>
      );
    case 'button':
      return (
        <button 
          className={`widget-button ${component.color}`}
          onClick={() => handleWidgetAction(component.onClickAction)}
        >
          {component.label}
        </button>
      );
  }
}
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT TIER                                       │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        ChatKit Frontend                               │  │
│  │                    (JavaScript/React/HTML)                            │  │
│  │  • Renders messages and widgets                                       │  │
│  │  • Sends user messages                                                │  │
│  │  • Handles widget actions (clicks, form submits)                      │  │
│  │  • Receives streaming updates                                         │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                      WebSocket / Server-Sent Events                         │
│                                    │                                        │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    APPLICATION TIER (ChatKit Server)                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     FastAPI + ChatKit Server                          │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐    │  │
│  │  │  BaseChatKit    │  │   Use Case      │  │     Agent +         │    │  │
│  │  │  Server         │──│   (Retail)      │──│     Tools           │    │  │
│  │  │                 │  │                 │  │                     │    │  │
│  │  │  • respond()    │  │  • agent.py     │  │  • lookup_order     │    │  │
│  │  │  • action()     │  │  • widgets.py   │  │  • start_return     │    │  │
│  │  │  • streaming    │  │  • tools.py     │  │  • process_refund   │    │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘    │  │
│  │           │                                          │                │  │
│  │           ▼                                          │                │  │
│  │  ┌─────────────────┐                                 │                │  │
│  │  │  Cosmos DB      │◄────────────────────────────────┘                │  │
│  │  │(Threads, Retail)│                                                  │  │
│  │  └─────────────────┘                                                  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                          Azure AD / Managed Identity                        │
│                                    │                                        │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI SERVICES TIER                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        Azure OpenAI                                   │  │
│  │                        (GPT-4o Model)                                 │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ChatKit Server: Middleware or Backend?

### The Short Answer

**The ChatKit Server is your backend application tier**, not traditional middleware. It:

- **Hosts your agent logic** (tools, instructions, business logic)
- **Manages state** (threads, messages, user data)
- **Orchestrates AI calls** (Azure OpenAI integration)
- **Renders widgets** (builds and streams UI components)
- **Handles actions** (processes button clicks, form submissions)

### Why Co-location is Required

The ChatKit server and agent code **must be co-located** (same process/container) because:

1. **Streaming Dependency**: Agent responses stream token-by-token; the ChatKit server must intercept and forward these in real-time
2. **Context Sharing**: Tools set flags on the agent context (e.g., `_show_order_widget`) that trigger widget streaming
3. **Action → Agent Loop**: Widget actions may need to invoke agent tools or update agent state

```
┌──────────────────────────────────────────────────────────────────┐
│                    SINGLE DEPLOYMENT UNIT                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                                                            │  │
│  │   ChatKit Server  ◄───────►  Agent + Tools                 │  │
│  │        │                          │                        │  │
│  │        │        Shared Context    │                        │  │
│  │        └──────────────────────────┘                        │  │
│  │                                                            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ✓ Co-located in same process                                   │
│  ✓ Share memory/context                                         │
│  ✓ Real-time streaming                                          │
└──────────────────────────────────────────────────────────────────┘
```

### What Could Be Separated?

| Component | Can Separate? | Notes |
|-----------|---------------|-------|
| **Frontend (ChatKit UI)** | ✅ Yes | Static files can be hosted on CDN |
| **Data Store** | ✅ Yes | Use external database (PostgreSQL, Cosmos DB) |
| **Agent/Tools** | ❌ No* | Must be in same process for streaming |
| **Azure OpenAI** | ✅ Yes | Already external service |

*You could theoretically separate the agent via gRPC streaming, but this adds significant complexity.

---

## Production Deployment Patterns

### Pattern 1: Simple (Recommended for Most Cases)

All components in a single container, horizontally scaled:

```
                    Load Balancer
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
    ┌─────────┐     ┌─────────┐     ┌─────────┐
    │Container│     │Container│     │Container│
    │   #1    │     │   #2    │     │   #3    │
    │         │     │         │     │         │
    │ ChatKit │     │ ChatKit │     │ ChatKit │
    │ +Agent  │     │ +Agent  │     │ +Agent  │
    └────┬────┘     └────┬────┘     └────┬────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
                         ▼
                ┌─────────────────┐
                │  Shared State   │
                │  (Redis/SQL/    │
                │   Cosmos DB)    │
                └─────────────────┘
                         │
                         ▼
                ┌─────────────────┐
                │  Azure OpenAI   │
                └─────────────────┘
```

**Pros:**
- Simple deployment
- Easy horizontal scaling
- Shared state via external store

**Cons:**
- All components scale together
- Larger container images

### Pattern 2: Separated Frontend

Static frontend on CDN, API on containers:

```
    ┌─────────────────────────────────────────────┐
    │              CDN / Static Hosting           │
    │         (Azure Static Web Apps, S3)         │
    │                                             │
    │   ┌──────────────────────────────────────┐  │
    │   │          ChatKit Frontend            │  │
    │   │          (index.html, JS)            │  │
    │   └──────────────────────────────────────┘  │
    └─────────────────────────────────────────────┘
                          │
                          │ WebSocket/SSE
                          ▼
    ┌─────────────────────────────────────────────┐
    │          Azure Container Apps               │
    │                                             │
    │   ┌──────────────────────────────────────┐  │
    │   │    ChatKit Server + Agent + Tools    │  │
    │   └──────────────────────────────────────┘  │
    └─────────────────────────────────────────────┘
```

**Pros:**
- Frontend cached globally
- Reduced backend load for static assets
- Independent frontend deployments

### Pattern 3: Multi-Tenant / Enterprise

Multiple use cases, shared infrastructure:

```
    ┌─────────────────────────────────────────────────────────────┐
    │                    API Gateway / Router                     │
    └─────────────────────────────────────────────────────────────┘
                │                    │                    │
                ▼                    ▼                    ▼
    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
    │ Retail Returns  │  │  Support Bot    │  │  Sales Agent    │
    │                 │  │                 │  │                 │
    │  ChatKit+Agent  │  │  ChatKit+Agent  │  │  ChatKit+Agent  │
    │  (Return tools) │  │  (FAQ tools)    │  │  (CRM tools)    │
    └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
             │                    │                    │
             └────────────────────┼────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
           ┌─────────────────┐         ┌─────────────────┐
           │  Shared State   │         │  Azure OpenAI   │
           │  (Cosmos DB)    │         │  (Shared Pool)  │
           └─────────────────┘         └─────────────────┘
```

**Pros:**
- Independent scaling per use case
- Isolated failures
- Different SLAs per service

---

## Project Structure

```
chatkit-order-returns/
├── main.py                 # FastAPI application entry point
├── base_server.py          # Reusable base server with Azure OpenAI integration
├── azure_client.py         # Azure OpenAI client management
├── config.py               # Environment configuration (Azure + branding settings)
│
├── shared/                 # Shared configuration modules
│   └── cosmos_config.py    # Centralized Cosmos DB configuration
│
├── scripts/                # Utility scripts
│   └── populate_cosmosdb.py # Script to populate Cosmos DB with sample data
│
├── data/
│   └── sample/             # Sample data definitions
│       └── retail_data.py  # Products, customers, orders, returns data
│
├── use_cases/
│   └── retail/             # Retail order returns use case
│       ├── __init__.py     # Exports RetailChatKitServer + components
│       ├── server.py       # RetailChatKitServer (extends BaseChatKitServer)
│       ├── agent.py        # Agent definition with retail tools
│       ├── widgets.py      # Widget builders for order/return UI
│       ├── tools.py        # Tools for order lookup, returns, etc.
│       ├── cosmos_client.py # Cosmos DB client for retail data
│       └── cosmos_store.py # ChatKit thread storage in Cosmos DB
│
├── frontend/               # React frontend (official ChatKit UI)
│   ├── package.json
│   └── src/App.tsx         # Main ChatKit React component
│
├── static/
│   ├── index.html          # Vanilla JS frontend (fallback)
│   ├── branding.css        # Customizable brand colors/styles
│   └── logo.svg            # Default logo (replaceable)
│
└── infra/
    ├── main.bicep          # Azure infrastructure as code
    └── main.parameters.json
```

## Data Architecture: Threads vs. Retail Data

Understanding the difference between **thread-scoped** and **retail** data is crucial:

### Thread-Scoped Data (Conversation Context)
- **Chat messages**: Each conversation thread has its own message history
- **Thread metadata**: Title, timestamps, status per conversation
- **Purpose**: Enables multiple independent customer service conversations

### Retail Data (Application State in Cosmos DB)
- **Customers**: Customer profiles with membership tiers
- **Orders**: Order history with products and statuses
- **Products**: Product catalog with return eligibility
- **Returns**: Active and completed return requests
- **Purpose**: Shared retail data accessible across all conversations

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA ARCHITECTURE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Thread A (Customer A)            Thread B (Customer B)                     │
│  ┌─────────────────────┐          ┌─────────────────────┐                   │
│  │ "Where's my order?" │          │ "I want to return"  │                   │
│  │ Order lookup result │          │ Return eligibility  │                   │
│  │ Tracking info       │          │ Return processed    │                   │
│  └─────────────────────┘          └─────────────────────┘                   │
│            │                                │                               │
│            └────────────┬───────────────────┘                               │
│                         ▼                                                   │
│         ┌───────────────────────────────────────────┐                       │
│         │        AZURE COSMOS DB                    │                       │
│         │  ┌─────────┐ ┌─────────┐ ┌─────────────┐  │                       │
│         │  │Customers│ │ Orders  │ │   Returns   │  │                       │
│         │  └─────────┘ └─────────┘ └─────────────┘  │                       │
│         │  ┌─────────┐ ┌─────────┐ ┌─────────────┐  │                       │
│         │  │Products │ │ Threads │ │   Items     │  │                       │
│         │  └─────────┘ └─────────┘ └─────────────┘  │                       │
│         └───────────────────────────────────────────┘                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Session Management

The frontend uses `localStorage` to persist the thread ID across page refreshes:

```javascript
// Thread ID persists in browser localStorage
let threadId = localStorage.getItem('chatkit_thread_id');
if (!threadId) {
    threadId = 'thread_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('chatkit_thread_id', threadId);
}
```

- **Page refresh**: Same thread, conversation history preserved
- **"New Chat" button**: Creates new thread, clears conversation (retail data persists in Cosmos DB)

## Core Components

### 1. BaseChatKitServer (`base_server.py`)

The base server provides reusable infrastructure for all ChatKit use cases:

```python
class BaseChatKitServer(ChatKitServer):
    """Base server with Azure OpenAI integration."""
    
    @abstractmethod
    def get_agent(self) -> Agent:
        """Return the agent for this use case."""
        pass
    
    @abstractmethod
    async def action(self, thread, action, sender, context):
        """Handle widget actions."""
        pass
    
    async def post_respond_hook(self, thread, agent_context):
        """Optional: Stream widgets after agent response."""
        pass
    
    async def respond(self, thread, input, context):
        """Handles message flow - DO NOT OVERRIDE."""
        pass
```

**What it handles:**
- Azure OpenAI client initialization
- Agent context creation
- Response streaming
- Widget streaming helper methods

### 2. Use Case Modules (`use_cases/`)

Each use case is a self-contained module with:

| File | Purpose |
|------|---------|
| `agent.py` | Agent definition with tools (function_tool decorators) |
| `widgets.py` | Functions that build ChatKit widgets |
| `actions.py` | Handlers for widget button clicks, form submissions, etc. |
| `database.py` | Data persistence (optional, if use case needs storage) |
| `__init__.py` | Public exports for the use case |

### 3. Specific ChatKit Server (e.g., `server.py`)

Your use-case-specific server extends `BaseChatKitServer`:

```python
class RetailChatKitServer(BaseChatKitServer):
    def get_agent(self) -> Agent:
        return create_retail_agent()
    
    async def post_respond_hook(self, thread, agent_context):
        if getattr(agent_context, '_show_order_widget', False):
            widget = build_order_widget(...)
            async for event in stream_widget(thread, widget):
                yield event
    
    async def action(self, thread, action, sender, context):
        # Handle widget actions (start_return, confirm_return, etc.)
        ...
```

## How the Retail Use Case Works

### Flow Diagram

```
User Message
     │
     ▼
┌──────────────────────────────────────┐
│  RetailChatKitServer.respond()       │
│  (inherited from BaseChatKitServer)  │
└──────────────────────────────────────┘
     │
     ▼
┌─────────────────┐
│  Azure OpenAI   │ ◄── create_retail_agent() provides Agent with tools
└─────────────────┘
     │
     ▼
┌─────────────────┐
│  Agent Tools    │ ──► lookup_order, start_return, check_eligibility, etc.
│  (agent.py)     │     Set agent_context._show_order_widget = True
└─────────────────┘
     │
     ▼
┌───────────────────────┐
│  post_respond_hook()  │ ──► build_order_widget() → stream_widget()
└───────────────────────┘
     │
     ▼
Widget Streamed to Client
```

### Widget Action Flow

```
User Clicks Button/Checkbox
     │
     ▼
Frontend sends: threads.custom_action
     │
     ▼
┌───────────────────────────────┐
│  RetailChatKitServer.action() │
└───────────────────────────────┘
     │
     ▼
┌───────────────────────────────────┐
│  Update Database                  │
│  (cosmos_store operations, etc.)  │
└───────────────────────────────────┘
     │
     ▼
┌────────────────────────┐
│  build_order_widget()  │
│  stream_widget()       │
└────────────────────────┘
     │
     ▼
Updated Widget Streamed to Client
```

### How Widget Actions Work (Detailed)

This section explains the complete journey of a button click from the UI to your server handler.

#### Step 1: Define Action in Widget (Python)

When building a widget, you attach an `ActionConfig` to interactive elements:

```python
# use_cases/retail/widgets.py
Button(
    id="return_button",
    label="🔄 Start Return",
    onClickAction=ActionConfig(
        type="start_return",       # Your custom action identifier
        handler="server",          # Route to server (always "server")
        payload={"order_id": "12345"}  # Optional static data
    )
)
```

#### Step 2: Serialized to JSON (Wire Format)

The widget is serialized and streamed to the client:

```json
{
  "type": "Button",
  "id": "return_button", 
  "label": "🔄 Start Return",
  "onClickAction": {
    "type": "start_return",
    "handler": "server",
    "payload": {"order_id": "12345"}
  }
}
```

#### Step 3: Client Renders and Attaches Handler (JavaScript)

The frontend creates the button and stores the action config:

```javascript
// static/index.html
case 'button':
    const btn = document.createElement('button');
    btn.textContent = component.label;
    btn.onclick = () => handleWidgetAction(
        component.onClickAction,  // Stored action config
        component.id
    );
    return btn;
```

#### Step 4: User Clicks → Client Sends Action

When clicked, the client collects form data and sends to server:

```javascript
// static/index.html
async function handleWidgetAction(action, componentId) {
    // Collect form data if button is inside a form
    const formData = collectFormData(componentId);  // {return_reason: "wrong_size"}
    
    // Merge form data with action payload
    const payload = { ...action.payload, ...formData };
    // Result: {order_id: "12345", return_reason: "wrong_size"}
    
    // Send via ChatKit protocol
    await fetch('/chatkit', {
        method: 'POST',
        body: JSON.stringify({
            type: "threads.custom_action",  // ChatKit protocol message
            params: {
                thread_id: currentThreadId,
                item_id: widgetId,
                action: {
                    type: "start_return",     // Your action type
                    payload: payload          // Merged data
                }
            }
        })
    });
}
```

#### Step 5: ChatKit Routes to Your Handler

The ChatKit library parses the request and calls your `action()` method:

```python
# ChatKit library internal (you don't write this)
if request.type == "threads.custom_action":
    await your_server.action(thread, action, sender, context)
```

#### Step 6: Your Action Handler (Your Code)

You implement the business logic:

```python
# server.py - YOU write this
async def action(self, thread, action, sender, context):
    action_type = action.type    # "start_return"
    payload = action.payload     # {"order_id": "12345", "return_reason": "wrong_size"}
    
    if action_type == "start_return":
        order_id = payload.get("order_id")
        reason = payload.get("return_reason")
        await self.cosmos_client.create_return(order_id, reason)
    
    elif action_type == "confirm_return":
        return_id = payload.get("return_id")
        await self.cosmos_client.confirm_return(return_id)
    
    # Stream updated widget back to client
    order = await self.cosmos_client.get_order(order_id)
    widget = build_order_widget(order)
    async for event in stream_widget(thread, widget):
        yield event
```

#### Key Insight: Agent is NOT Involved

**Actions bypass the LLM entirely.** This is crucial to understand:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  TEXT MESSAGE FLOW (uses Agent/LLM)                                         │
│                                                                             │
│  User types: "I want to return my Nike shoes"                               │
│       │                                                                     │
│       ▼                                                                     │
│  respond() → Agent → LLM → Tool call (start_return) → Widget                │
│                  ▲                                                          │
│                  │ $$$  LLM tokens consumed                                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  WIDGET ACTION FLOW (NO Agent/LLM)                                          │
│                                                                             │
│  User clicks: [Add] button                                                  │
│       │                                                                     │
│       ▼                                                                     │
│  action() → Your code → Database → Widget                                   │
│                                                                             │
│  ✓ No LLM call                                                              │
│  ✓ No token cost                                                            │
│  ✓ Instant response                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Summary: Action Components

| Component | Location | Role |
|-----------|----------|------|
| `ActionConfig` | `widgets.py` | Defines action type and static payload |
| `onClickAction` | JSON wire format | Carried to client with widget |
| `handleWidgetAction` | `index.html` (JS) | Collects form data, sends request |
| `threads.custom_action` | ChatKit protocol | Request type that routes to `action()` |
| `action()` method | `chatkit_server.py` | **Your handler** - all business logic |
| Agent/LLM | N/A | **NOT used** for widget actions |

---

## Dual-Input Architecture: Text + Widget Convergence

This section explains how the system handles **both text-based natural language input and widget button clicks**, and how they converge into a unified processing flow.

### The Challenge: Two Input Paths, One Flow

Users can interact with the system in two ways:
1. **Widget Buttons**: Click a button like "Full Refund" or "Schedule Pickup"
2. **Natural Language**: Type "I want a full refund" or "schedule the pickup please"

Both must result in the same outcome—recording the selection and advancing the return flow.

### Architecture Overview: Input Convergence

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DUAL-INPUT CONVERGENCE ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   USER INPUT                                                                │
│   ══════════                                                                │
│        │                                                                    │
│        ├──────────────────────────┬─────────────────────────────┐           │
│        ▼                          ▼                             │           │
│   ┌──────────────┐         ┌──────────────┐                     │           │
│   │ WIDGET CLICK │         │  TEXT INPUT  │                     │           │
│   │              │         │              │                     │           │
│   │ [Full Refund]│         │ "I want a    │                     │           │
│   │    button    │         │ full refund" │                     │           │
│   └──────┬───────┘         └──────┬───────┘                     │           │
│          │                        │                             │           │
│          ▼                        ▼                             │           │
│   ┌──────────────┐         ┌──────────────┐                     │           │
│   │   action()   │         │   respond()  │                     │           │
│   │    method    │         │    method    │                     │           │
│   │              │         │  + Agent/LLM │                     │           │
│   └──────┬───────┘         └──────┬───────┘                     │           │
│          │                        │                             │           │
│          │                        ▼                             │           │
│          │                 ┌──────────────┐                     │           │
│          │                 │ set_user_    │                     │           │
│          │                 │ selection()  │                     │           │
│          │                 │    tool      │                     │           │
│          │                 └──────┬───────┘                     │           │
│          │                        │                             │           │
│          ▼                        ▼                             │           │
│   ┌─────────────────────────────────────────────────────────┐   │           │
│   │              SESSION CONTEXT (Unified State)            │   │           │
│   │                                                         │   │           │
│   │   {                                                     │   │           │
│   │     "customer_id": "CUST-1001",                         │   │           │
│   │     "selected_items": [...],                            │   │           │
│   │     "reason_code": "DAMAGED",        ← Both paths       │   │           │
│   │     "resolution": "FULL_REFUND",       update this!     │   │           │
│   │     "shipping_method": "SCHEDULE_PICKUP"                │   │           │
│   │   }                                                     │   │           │
│   └─────────────────────────────────────────────────────────┘   │           │
│                              │                                  │           │
│                              ▼                                  │           │
│   ┌─────────────────────────────────────────────────────────┐   │           │
│   │         finalize_return_from_session()                  │   │           │
│   │         Creates return using session data               │   │           │
│   └─────────────────────────────────────────────────────────┘   │           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Path 1: Widget Button Click

When a user clicks a widget button:

```python
# server.py - action() method handles widget clicks directly

async def action(self, thread, action, sender, context):
    action_type = getattr(action, 'type', '')
    payload = getattr(action, 'payload', {})
    
    if action_type == "select_resolution":
        # Extract resolution from button payload
        resolution_code = payload.get("resolution")
        
        # Store in session context
        session = self._session_context
        session["resolution"] = resolution_code
        
        # Show next widget (shipping options)
        result = get_shipping_options()
        widget = build_shipping_widget(result["options"], thread.id)
        async for event in stream_widget(thread, widget):
            yield event
```

**Key Points:**
- No LLM involved—direct mapping from button payload to action
- Fast and deterministic
- Payload carries all needed data (resolution code, item ID, etc.)

### Path 2: Natural Language Text Input

When a user types their selection:

```python
# server.py - respond() method handles text input through the agent

async def respond(self, thread, context):
    # 1. Build context summary for the agent
    context_summary = self._build_context_summary()
    
    # 2. Prepend session state to user's message
    user_input = thread.messages[-1].content
    augmented_input = f"""
[CURRENT SESSION STATE]
{context_summary}

User message: {user_input}
"""
    
    # 3. Agent processes with tools available
    async for event in Runner.run(agent, augmented_input):
        yield event
```

The agent then uses the `set_user_selection` tool to record the typed choice:

```python
# Tool used by agent when user types their selection

@function_tool
async def tool_set_user_selection(
    ctx: RunContextWrapper,
    selection_type: str,     # "reason", "resolution", or "shipping"
    selection_code: str,     # "FULL_REFUND", "DAMAGED", etc.
) -> str:
    session = ctx.context._session_context
    
    if selection_type == "resolution":
        session["resolution"] = selection_code
        return "Recorded. Now show shipping options."
    
    # ... similar for reason and shipping
```

**Key Points:**
- LLM interprets natural language ("full refund" → `FULL_REFUND`)
- `set_user_selection` tool records the choice in session
- Agent then calls the next step (e.g., `get_shipping_options`)

### The Session Context: Where Both Paths Converge

The **session context** is the shared state that both input paths write to:

```python
# Session context structure (stored on server instance)
self._session_context = {
    # Customer identification
    "customer_id": "CUST-1001",
    "customer_name": "Jane Smith",
    "customer_tier": "Gold",
    
    # What was shown to user (for NL reference)
    "displayed_orders": [
        {
            "order_id": "ORD-78234",
            "items": [
                {"product_id": "PROD-001", "name": "Blue Wireless Widget", ...},
                {"product_id": "PROD-002", "name": "Premium Protective Case", ...}
            ]
        }
    ],
    
    # User's selections (updated by EITHER path)
    "selected_items": [...],
    "reason_code": "DAMAGED",           # Set by widget OR tool
    "resolution": "FULL_REFUND",        # Set by widget OR tool
    "shipping_method": "SCHEDULE_PICKUP" # Set by widget OR tool
}
```

### Natural Language Understanding with Session Context

When the user types natural language, the agent receives the session state as context:

```
[CURRENT SESSION STATE]
Customer: Jane Smith (ID: CUST-1001)

Items shown to customer (available for return):
  Order ORD-78234:
    - Blue Wireless Widget (Product ID: PROD-001, Price: $49.99, Qty: 2)
    - Premium Protective Case (Product ID: PROD-002, Price: $19.99, Qty: 1)

Items selected for return:
  - Blue Wireless Widget from order ORD-78234

Return reason: DAMAGED
Resolution: (not yet selected)

User message: I want a full refund please
```

With this context, the agent:
1. Understands "full refund" refers to the `FULL_REFUND` resolution option
2. Calls `set_user_selection(selection_type="resolution", selection_code="FULL_REFUND")`
3. Then calls `get_shipping_options` to show the next widget

### Avoiding Redundant Widgets

When the user types their selection, we **don't show the widget again**:

```python
# System prompt instructs the agent:

"""
HANDLING USER TYPED SELECTIONS (CRITICAL):
When the user TYPES their selection instead of clicking a button:

1. Match their input to the closest option code
2. Use set_user_selection tool to record it
3. Then proceed to the NEXT step - don't show the same widget again!

Example:
- User types "full refund" 
- Call set_user_selection(selection_type="resolution", selection_code="FULL_REFUND")
- Then call get_shipping_options (NOT get_resolution_options!)
"""
```

### Finalizing the Return: Using Session Data

Both paths lead to `finalize_return_from_session()` which reads from session:

```python
@function_tool
async def tool_finalize_return_from_session(ctx):
    session = ctx.context._session_context
    
    # All data comes from session - works for both input paths!
    customer_id = session.get("customer_id")
    selected_items = session.get("selected_items", [])
    reason_code = session.get("reason_code")
    resolution = session.get("resolution")
    shipping_method = session.get("shipping_method")
    
    # Create the return
    result = create_return_request(
        customer_id=customer_id,
        order_id=selected_items[0]["order_id"],
        items=selected_items,
        reason_code=reason_code,
        resolution=resolution,
        shipping_method=shipping_method,
    )
    
    return f"Return {result['id']} created!"
```

### Summary: Dual-Input Components

| Component | Role | Used By |
|-----------|------|---------|
| `action()` method | Handles widget button clicks directly | Widget Path |
| `respond()` method | Routes text to agent/LLM | Text Path |
| `set_user_selection` tool | Records typed selections | Text Path |
| `_session_context` | Shared state for both paths | Both |
| `finalize_return_from_session` | Creates return from session | Both |
| System prompt | Guides agent on NL interpretation | Text Path |

### Best Practices for Dual-Input Design

1. **Session is the Source of Truth**: Both paths write to session context
2. **Payload Carries All Data**: Widget buttons include all needed IDs/codes
3. **Agent Has Full Context**: Session state is injected into agent input
4. **Don't Duplicate Widgets**: When user types selection, proceed to next step
5. **Use Tools for NL**: `set_user_selection` bridges NL to session state
6. **Finalize from Session**: Final action reads from session, not parameters

---

## Widget Orchestration: How the Flow is Controlled

This section explains **where the orchestration logic lives** and **how to make it dynamic**.

### The Orchestration Layer: `action()` Method

The **`action()` method in `server.py`** is the orchestration hub. It receives widget clicks and **decides what happens next**:

```python
# use_cases/retail/server.py

async def action(self, thread, action, sender, context):
    action_type = getattr(action, 'type', '')
    payload = getattr(action, 'payload', {})
    
    # ═══════════════════════════════════════════════════════════════
    # ORCHESTRATION LOGIC: What widget comes next?
    # ═══════════════════════════════════════════════════════════════
    
    if action_type == "select_return_item":
        # User selected an item → Show reasons widget
        result = get_return_reasons()
        widget = build_reasons_widget(result["reasons"], thread.id)
        async for event in stream_widget(thread, widget):
            yield event
    
    elif action_type == "select_reason":
        # User selected reason → Show resolution options
        result = get_resolution_options()
        widget = build_resolution_widget(result["options"], thread.id)
        async for event in stream_widget(thread, widget):
            yield event
    
    elif action_type == "select_resolution":
        # User selected resolution → Show shipping options
        result = get_shipping_options()
        widget = build_shipping_widget(result["options"], thread.id)
        async for event in stream_widget(thread, widget):
            yield event
    
    elif action_type == "select_shipping":
        # Final step → Create return and show confirmation
        result = create_return_request(...)
        widget = build_confirmation_widget(result, thread.id)
        async for event in stream_widget(thread, widget):
            yield event
```

### Visual Flow: The Orchestration Chain

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    WIDGET-DRIVEN ORCHESTRATION FLOW                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐     click      ┌──────────────┐     click                 │
│  │   Customer   │ ─────────────► │   Reasons    │ ─────────────►            │
│  │   Widget     │                │   Widget     │                           │
│  │              │                │              │                           │
│  │  [Item A]    │                │  [Defective] │                           │
│  │  [Item B] ←──┼── user clicks  │  [Wrong Size]│                           │
│  │  [Item C]    │                │  [Changed]←──┼── user clicks             │
│  └──────────────┘                └──────────────┘                           │
│         │                               │                                   │
│         ▼                               ▼                                   │
│  action("select_return_item")    action("select_reason")                    │
│         │                               │                                   │
│         ▼                               ▼                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    action() METHOD (server.py)                       │   │
│  │                                                                      │   │
│  │   if action_type == "select_return_item":                            │   │
│  │       → build_reasons_widget() → stream to client                    │   │
│  │                                                                      │   │
│  │   if action_type == "select_reason":                                 │   │
│  │       → build_resolution_widget() → stream to client                 │   │
│  │                                                                      │   │
│  │   ... and so on for each step                                        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Is the Flow Hardcoded?

**Yes and No:**

| Aspect | Hardcoded? | Where? | How to Make Dynamic? |
|--------|------------|--------|----------------------|
| **Action types** | Yes | Widget definitions (`ActionConfig`) | Use variables for action types |
| **Next widget** | Partially | `action()` method if/elif chain | Move to config/database |
| **Available options** | No | Fetched from Cosmos DB at runtime | Already dynamic |
| **Conditional branches** | Yes | `action()` method logic | Use state machine pattern |

### Making the Flow Dynamic: Strategy Patterns

#### 1. **Data-Driven Flow Definition**

Instead of hardcoding the flow, define it in configuration:

```python
# Define flow transitions in config (could be in Cosmos DB)
RETURN_FLOW = {
    "start": {
        "widget": "returnable_items",
        "next_on": {
            "select_return_item": "reasons",
        }
    },
    "reasons": {
        "widget": "reasons",
        "next_on": {
            "select_reason": {
                "CHANGED_MIND": "retention_offers",  # Conditional!
                "default": "resolution",
            }
        }
    },
    "retention_offers": {
        "widget": "retention",
        "next_on": {
            "accept_offer": "confirmation_kept",
            "decline_offers": "resolution",
        }
    },
    "resolution": {
        "widget": "resolution",
        "next_on": {
            "select_resolution": "shipping",
        }
    },
    "shipping": {
        "widget": "shipping",
        "next_on": {
            "select_shipping": "confirmation",
        }
    },
    "confirmation": {
        "widget": "confirmation",
        "next_on": {}  # Terminal state
    }
}

# Then in action():
async def action(self, thread, action, sender, context):
    current_state = self._session_context.get("flow_state", "start")
    flow_config = RETURN_FLOW.get(current_state, {})
    
    # Determine next state
    transitions = flow_config.get("next_on", {})
    next_state = transitions.get(action_type, transitions.get("default"))
    
    # Handle conditional transitions
    if isinstance(next_state, dict):
        condition_value = payload.get("reason_code", "default")
        next_state = next_state.get(condition_value, next_state.get("default"))
    
    # Update state
    self._session_context["flow_state"] = next_state
    
    # Build and stream next widget
    widget = self._build_widget_for_state(next_state, thread.id)
    async for event in stream_widget(thread, widget):
        yield event
```

#### 2. **Conditional Branching Example: Retention Offers**

The current implementation already has conditional logic for "Changed Mind" returns:

```python
# In action() - current implementation
if action_type == "select_reason":
    reason_code = payload.get("reason_code")
    
    if reason_code == "CHANGED_MIND":
        # Branch: Offer retention discounts first
        offers = get_retention_offers(customer_id)
        widget = build_retention_widget(offers, thread.id)
    else:
        # Normal path: Go directly to resolution options
        options = get_resolution_options()
        widget = build_resolution_widget(options, thread.id)
    
    async for event in stream_widget(thread, widget):
        yield event
```

### Two Entry Points for Widget Display

Widgets can be triggered in **two ways**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TWO PATHS TO WIDGET DISPLAY                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PATH 1: LLM-Driven (Agent Tools)                                           │
│  ════════════════════════════════                                           │
│                                                                             │
│  User types message → Agent → Tool call → Set context flag                  │
│                                               │                             │
│                                               ▼                             │
│                                      post_respond_hook()                    │
│                                               │                             │
│                                               ▼                             │
│                                      if _show_widget: stream_widget()       │
│                                                                             │
│  EXAMPLE: "I want to return something"                                      │
│           → lookup_customer() sets _show_customer_widget = True             │
│           → post_respond_hook() streams customer widget                     │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PATH 2: Direct Action (Widget Clicks)                                      │
│  ═════════════════════════════════════                                      │
│                                                                             │
│  User clicks button → action() → Business logic → stream_widget()           │
│                                                                             │
│  EXAMPLE: User clicks [Start Return] button                                 │
│           → action() receives type="select_return_item"                     │
│           → Stores context, determines next step                            │
│           → Streams reasons widget directly                                 │
│                                                                             │
│  ✓ No LLM call                                                              │
│  ✓ Instant response                                                         │
│  ✓ Deterministic flow                                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Session Context: Tracking State Across Actions

The server maintains session state to track the return flow:

```python
class RetailChatKitServer(BaseChatKitServer):
    def __init__(self, data_store):
        self._session_context = {}  # Tracks flow state
    
    async def action(self, thread, action, sender, context):
        # Store selections as user progresses
        if action_type == "select_return_item":
            self._session_context["customer_id"] = payload.get("customer_id")
            self._session_context["selected_order_id"] = payload.get("order_id")
            self._session_context["selected_product_id"] = payload.get("product_id")
        
        elif action_type == "select_reason":
            self._session_context["reason_code"] = payload.get("reason_code")
        
        elif action_type == "select_resolution":
            self._session_context["resolution"] = payload.get("resolution")
        
        elif action_type == "select_shipping":
            # Final step: Use all accumulated context to create return
            result = create_return_request(
                customer_id=self._session_context["customer_id"],
                order_id=self._session_context["selected_order_id"],
                product_id=self._session_context["selected_product_id"],
                reason_code=self._session_context["reason_code"],
                resolution=self._session_context["resolution"],
                shipping_method=payload.get("shipping_method"),
            )
```

### Key Design Decisions

| Decision | Current Implementation | Alternative |
|----------|----------------------|-------------|
| **Flow control** | If/elif in `action()` | State machine, config-driven |
| **State storage** | In-memory `_session_context` | Cosmos DB per-thread state |
| **Next widget** | Determined by action type | Lookup from flow config |
| **Conditional branches** | Inline if statements | Rule engine, decision table |
| **LLM involvement** | Only for initial message | Could re-involve for complex decisions |

### Summary: Where Orchestration Lives

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ORCHESTRATION LOCATIONS                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────────────┐                                                 │
│  │  server.py             │                                                 │
│  │  ──────────            │                                                 │
│  │                        │                                                 │
│  │  action() method       │ ◄── Main orchestration hub                      │
│  │    • Receives clicks   │     Decides: what widget comes next?            │
│  │    • Stores context    │     Contains: flow logic, conditionals          │
│  │    • Builds next widget│                                                 │
│  │                        │                                                 │
│  │  post_respond_hook()   │ ◄── Secondary path (after LLM response)         │
│  │    • Checks flags      │     Used for: initial widget display            │
│  │    • Streams widgets   │                                                 │
│  └────────────────────────┘                                                 │
│                                                                             │
│  ┌────────────────────────┐                                                 │
│  │  tools.py / agent.py   │                                                 │
│  │  ───────────────────   │                                                 │
│  │                        │                                                 │
│  │  Tool functions set    │ ◄── Triggers widgets via context flags          │
│  │  context flags like:   │     _show_customer_widget = True                │
│  │  _show_reasons_widget  │     _show_returnable_items_widget = True        │
│  │                        │                                                 │
│  └────────────────────────┘                                                 │
│                                                                             │
│  ┌────────────────────────┐                                                 │
│  │  widgets.py            │                                                 │
│  │  ──────────            │                                                 │
│  │                        │                                                 │
│  │  ActionConfig defines  │ ◄── Declares action types and payloads          │
│  │  what data is sent     │     type="select_reason"                        │
│  │  when user clicks      │     payload={"reason_code": "DEFECTIVE"}        │
│  │                        │                                                 │
│  └────────────────────────┘                                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Creating a New Use Case

```bash
mkdir use_cases/my_use_case
```

### Step 2: Define Your Agent (`use_cases/my_use_case/agent.py`)

```python
from agents import Agent, function_tool
from agents.run_context import RunContextWrapper
from chatkit.agents import AgentContext

MyContext = AgentContext[Any]

@function_tool(description_override="Do something useful")
async def my_tool(ctx: RunContextWrapper["MyContext"], param: str) -> str:
    """Tool implementation."""
    # Access thread: ctx.context.thread.id
    # Access store: ctx.context.store
    
    # Trigger widget display
    ctx.context._show_my_widget = True
    ctx.context._my_data = some_data
    
    return "Done!"

MY_AGENT_INSTRUCTIONS = """You are a helpful assistant..."""

def create_my_agent() -> Agent["MyContext"]:
    return Agent["MyContext"](
        name="My Assistant",
        instructions=MY_AGENT_INSTRUCTIONS,
        tools=[my_tool],
    )
```

### Step 3: Build Your Widgets (`use_cases/my_use_case/widgets.py`)

```python
from chatkit.widgets import Card, Row, Text, Button, Title
from chatkit.actions import ActionConfig

def build_my_widget(data: list, thread_id: str) -> Card:
    children = [
        Title(id="title", value="My Widget", size="lg"),
    ]
    
    for item in data:
        children.append(
            Row(
                id=f"item_{item['id']}",
                children=[
                    Text(id=f"text_{item['id']}", value=item['name']),
                    Button(
                        id=f"btn_{item['id']}",
                        label="Action",
                        onClickAction=ActionConfig(
                            type="my_action",
                            handler="server",
                            payload={"item_id": item['id']}
                        ),
                    ),
                ]
            )
        )
    
    return Card(id=f"my_widget_{thread_id}", children=children)
```

### Step 4: Handle Actions (`use_cases/my_use_case/actions.py`)

```python
def handle_my_action(action_type: str, payload: dict):
    if action_type == "my_action":
        item_id = payload.get("item_id")
        # Do something with the item
        return {"success": True}
    return {"success": False}
```

### Step 5: Create Your Server (`my_chatkit_server.py`)

```python
from base_server import BaseChatKitServer
from use_cases.my_use_case import create_my_agent, build_my_widget

class MyChatKitServer(BaseChatKitServer):
    def get_agent(self):
        return create_my_agent()
    
    async def post_respond_hook(self, thread, agent_context):
        if getattr(agent_context, '_show_my_widget', False):
            data = getattr(agent_context, '_my_data', [])
            widget = build_my_widget(data, thread.id)
            async for event in stream_widget(thread, widget):
                yield event
    
    async def action(self, thread, action, sender, context):
        action_type = action.type
        payload = action.payload or {}
        
        # Handle the action
        if action_type == "my_action":
            # Update data
            ...
        
        # Stream updated widget
        widget = build_my_widget(updated_data, thread.id)
        async for event in stream_widget(thread, widget):
            yield event
```

### Step 6: Register in `main.py`

```python
from my_chatkit_server import MyChatKitServer

chatkit_server = MyChatKitServer(data_store)
```

## Widget Reference

### Available Widget Components

| Component | Key Properties |
|-----------|---------------|
| `Card` | `id`, `children` |
| `Row` | `id`, `children` |
| `Title` | `id`, `value`, `size` ('sm', 'md', 'lg') |
| `Text` | `id`, `value`, `color`, `textAlign`, `lineThrough` |
| `Button` | `id`, `label`, `color`, `size`, `onClickAction` |
| `Checkbox` | `id`, `name`, `defaultChecked`, `onChangeAction` |
| `Input` | `id`, `name`, `placeholder` |
| `Form` | `id`, `children` |
| `Badge` | `id`, `label`, `color` |
| `Divider` | `id` |
| `Spacer` | `id` |
| `Box` | `id`, `children` |

### ActionConfig

```python
ActionConfig(
    type="action_type",        # String identifier for the action
    handler="server",          # Always "server" for backend handling
    payload={"key": "value"}   # Optional data to pass with action
)
```

---

## Branding & Customization

The application supports full branding customization via environment variables and CSS:

### Environment Variables

```env
BRAND_NAME=Order Returns         # Header title
BRAND_TAGLINE=AI-Powered Returns # Header subtitle
BRAND_LOGO_URL=/static/logo.svg  # Logo image URL
BRAND_PRIMARY_COLOR=#0078d4      # Primary brand color
BRAND_FAVICON_URL=/static/favicon.ico
```

### Branding API

The `/api/branding` endpoint returns branding configuration as JSON:

```json
{
  "name": "Order Returns",
  "tagline": "AI-Powered Returns",
  "logoUrl": "/static/logo.svg",
  "primaryColor": "#0078d4",
  "faviconUrl": "/static/favicon.ico"
}
```

### CSS Customization

Edit `static/branding.css` to customize colors, typography, and spacing:

```css
:root {
    /* Primary brand colors */
    --brand-primary: #0078d4;
    --brand-primary-hover: #106ebe;
    
    /* Header gradient */
    --header-gradient-start: #0078d4;
    --header-gradient-end: #005a9e;
    
    /* Status colors */
    --color-success: #28a745;
    --color-danger: #dc3545;
    
    /* Logo sizing */
    --logo-width: 32px;
    --logo-height: 32px;
}
```

### Branding Flow

```
Page Load → fetch(/api/branding) → Apply to DOM
                  │
                  ▼
            config.py reads
            env variables
```

---

## Best Practices

1. **Separation of Concerns**: Keep agent, widgets, and actions in separate files
2. **Trigger Flags**: Use `agent_context._show_*` flags to trigger widget display
3. **Streaming**: Always use `async for event in stream_widget(...)` for widget updates
4. **IDs**: Every widget component needs a unique `id` property
5. **Action Types**: Use descriptive action type strings (e.g., `"add_item"`, `"delete_item"`)
6. **Error Handling**: Handle missing payloads gracefully in action handlers

---

## Summary: Why Use ChatKit?

### When to Use ChatKit

| Use ChatKit When... | Use Standard Agent When... |
|---------------------|---------------------------|
| You need interactive UI elements | Text responses are sufficient |
| Users need to take actions (click, submit) | Read-only chat experience |
| Real-time streaming is important | Request/response is fine |
| You want consistent UI components | Custom frontend is preferred |
| Building user-facing applications | Building API-first services |

### Key Takeaways

1. **ChatKit is not middleware** — it's your application backend that happens to speak the ChatKit protocol
2. **Agent and ChatKit must be co-located** — streaming requires tight integration
3. **Widgets are server-rendered** — the backend builds the UI, not the frontend
4. **Actions are server-handled** — user interactions go to your backend, not just the LLM
5. **The pattern is reusable** — extend `BaseChatKitServer` for new use cases

### The Value Proposition

```
Traditional Agent App:
  User → [Your Frontend] → [Your API] → [Agent] → Text → [Your Frontend renders it]
                    ↑
            You build ALL of this

ChatKit App:
  User → [ChatKit UI] → [ChatKit Server] → [Agent] → Text + Widgets
                    ↑                              ↑
         Pre-built UI              Your business logic here
```

ChatKit lets you focus on your **agent logic and business rules** while providing a **production-ready chat interface** out of the box.
