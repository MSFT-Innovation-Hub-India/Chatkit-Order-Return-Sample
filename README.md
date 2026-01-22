# ChatKit Order Returns Sample with Azure OpenAI

A self-hosted ChatKit order returns management application powered by Azure OpenAI, featuring interactive widgets and a modular architecture designed for retail customer service.

## 🎯 Features

- **Official ChatKit React UI**: Uses OpenAI's `@openai/chatkit-react` components
- **ChatKit Protocol**: Backend uses `openai-chatkit` Python library
- **OpenAI Agents SDK**: Built with `openai-agents` for tool orchestration and agent workflows
- **Azure OpenAI**: Powered by Azure OpenAI with GPT-4o model
- **Azure Cosmos DB**: Persistent storage for orders, customers, and returns
- **Interactive Widgets**: Rich UI with buttons, forms, order details, and status badges
- **Returns Workflow**: Complete returns processing with eligibility checks
- **Customizable Branding**: Easy logo, colors, and styling customization
- **Self-Hosted**: Full control over your data and infrastructure
- **Azure Container Apps**: Cloud-native deployment with auto-scaling

## 🤔 What is ChatKit?

ChatKit consists of two parts:

| Component | Package | Description |
|-----------|---------|-------------|
| **ChatKit React UI** | `@openai/chatkit-react` | Official React components for the chat interface |
| **ChatKit Protocol** | `openai-chatkit` (Python) | Server-side library for streaming, widgets, and actions |

This project uses **both** - the official React frontend connected to a self-hosted Python backend.

### Server-Driven UI Architecture

ChatKit uses a **Server-Driven UI** pattern:

- **Server (Python)** controls **WHAT** to display (widget structure, colors, labels)
- **Client (React)** controls **HOW** to display it (CSS, animations, theming)

```
┌───────────────────────────────────────────────────────────────────────────────┐
│  Python (widgets.py)              JSON Protocol              React (ChatKit)  │
│  ───────────────────              ─────────────              ───────────────  │
│                                                                               │
│  Button(                    →    {"type": "Button",    →    <button class=    │
│    label="✓",                      "label": "✓",             "ck-btn--success│
│    color="success",                "color": "success",        ck-btn--soft">  │
│    variant="soft"                  "variant": "soft"}        ✓</button>       │
│  )                                                                            │
│                                                                               │
│  You define STRUCTURE           Serialized over SSE      React renders HTML   │
│  No CSS needed!                                          with built-in styles │
└───────────────────────────────────────────────────────────────────────────────┘
```

**Benefits:**
- Change UI by editing Python only—no frontend deployment needed
- Pre-built styles for all color/variant combinations
- Type-safe widget definitions

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Frontend (React)                  Backend (Python)                         │
│  ─────────────────                 ─────────────────                        │
│  @openai/chatkit-react      ←→     openai-chatkit + FastAPI                 │
│  • Official UI components          • ChatKit protocol server                │
│  • Streaming display               • Widget definitions                     │
│  • Action handling                 • Azure OpenAI integration               │
│                                    • Azure Cosmos DB persistence            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### How Widget Rendering Works

**Widgets are NOT HTML sent from the server.** The flow is:

1. **Server** builds widget objects in Python (`Card`, `Button`, `Row`, etc.)
2. **Server** streams widget as JSON over SSE (e.g., `{"type": "Button", "label": "Add"}`)
3. **ChatKit React** receives JSON and renders using official components
4. **Browser** displays the interactive widget

For detailed architecture, deployment patterns, and customization, see [ARCHITECTURE.md](ARCHITECTURE.md).

## 📁 Project Structure

```
chatkit-order-returns/
├── main.py                  # FastAPI application entry point
├── config.py                # Configuration management (incl. branding)
├── base_server.py           # Reusable base server with Azure OpenAI
├── azure_client.py          # Azure OpenAI client manager
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container build configuration
├── azure.yaml               # Azure Developer CLI configuration
├── ARCHITECTURE.md          # Detailed architecture documentation
├── .env.example             # Environment variables template
│
├── shared/                  # Shared configuration modules
│   └── cosmos_config.py     # Centralized Cosmos DB configuration
│
├── scripts/                 # Utility scripts
│   └── populate_cosmosdb.py # Script to populate Cosmos DB with sample data
│
├── data/
│   └── sample/              # Sample data definitions
│       └── retail_data.py   # Products, customers, orders, returns data
│
├── frontend/                # React frontend (official ChatKit UI)
│   ├── package.json         # Node.js dependencies
│   ├── src/
│   │   ├── App.tsx          # Main ChatKit React component
│   │   └── main.tsx         # React entry point
│   └── vite.config.ts       # Vite build configuration
│
├── core/                    # Extensible framework base classes
│   ├── domain.py            # PolicyEngine, DomainService, Validator
│   ├── data.py              # Repository pattern for data access
│   ├── presentation.py      # WidgetComposer, WidgetTheme
│   ├── session.py           # SessionContext, SessionManager
│   ├── orchestration.py     # UseCaseServer base class
│   └── template.py          # Documentation for creating new use cases
│
├── use_cases/
│   ├── retail/              # Retail order returns use case
│   │   ├── __init__.py      # Exports RetailChatKitServer
│   │   ├── server.py        # ChatKit server for retail returns
│   │   ├── session.py       # ReturnSessionContext
│   │   ├── tools.py         # Tools for order lookup, returns, etc.
│   │   ├── cosmos_client.py # Cosmos DB client for retail data
│   │   ├── cosmos_store.py  # ChatKit thread storage in Cosmos DB
│   │   ├── domain/          # Pure business logic (no I/O)
│   │   │   ├── policies.py  # ReturnEligibilityPolicy, RefundPolicy
│   │   │   └── services.py  # RefundCalculator, ReturnRequestBuilder
│   │   └── presentation/    # Widget composition
│   │       └── composer.py  # ReturnWidgetComposer
│   │
│   └── healthcare/          # Healthcare appointment scheduling (example)
│       ├── __init__.py      # Exports HealthcareChatKitServer
│       ├── server.py        # ChatKit server extending UseCaseServer
│       ├── session.py       # AppointmentSessionContext
│       ├── domain/          # Pure business logic
│       │   ├── policies.py  # SchedulingRules, CancellationPolicy
│       │   └── services.py  # ScheduleCalculator, ConflictChecker
│       └── presentation/    # Widget composition
│           └── composer.py  # AppointmentWidgetComposer
│
├── static/
│   ├── index.html           # Vanilla JS frontend (fallback)
│   ├── dist/                # React build output (generated)
│   ├── branding.css         # Customizable brand colors/styles
│   └── logo.svg             # Default logo (replace with your own)
│
└── infra/
    ├── main.bicep           # Azure infrastructure as code
    └── main.parameters.json # Deployment parameters
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for React frontend)
- Azure subscription with:
  - Azure OpenAI with GPT-4o deployment
  - (Optional) Azure Container Apps for deployment
- Azure CLI and Azure Developer CLI (azd)

### Local Development

1. **Clone and navigate to the project**
   ```bash
   cd chatkit-sample
   ```

2. **Create a virtual environment and install Python dependencies**
   ```bash
   python -m venv .venv
   # Windows
   .\.venv\Scripts\activate
   # Linux/macOS
   source .venv/bin/activate
   
   pip install -r requirements.txt
   ```

3. **Install React frontend dependencies**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your Azure OpenAI settings:
   ```env
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT=gpt-4o
   AZURE_OPENAI_API_VERSION=2025-01-01-preview
   ```

5. **Login to Azure (for authentication)**
   ```bash
   az login
   ```

6. **Run the application**
   ```bash
   python main.py
   ```

7. **Open your browser**
   Navigate to `http://localhost:8000`

## 🎨 Branding & Customization

Customize the app's appearance to match your organization's brand:

### Environment Variables

```env
# In your .env file
BRAND_NAME=My Company Returns
BRAND_TAGLINE=Easy Returns, Happy Customers
BRAND_LOGO_URL=/static/logo.svg
BRAND_PRIMARY_COLOR=#0078d4
BRAND_FAVICON_URL=/static/favicon.ico
```

### CSS Customization

Edit `static/branding.css` for deeper styling:

```css
:root {
    --brand-primary: #0078d4;        /* Primary brand color */
    --header-gradient-start: #0078d4; /* Header gradient */
    --header-gradient-end: #005a9e;
    --color-success: #28a745;         /* Success/complete color */
    --color-danger: #dc3545;          /* Delete/error color */
}
```

### Custom Logo

Replace `static/logo.svg` with your own logo file (SVG, PNG, or any web format).

## 💬 Using the Order Returns Assistant

The ChatKit Order Returns app understands natural language commands:

- **Check orders**: "Show me my recent orders" or "I want to check order #12345"
- **Start returns**: "I need to return an item" or "This product is defective"
- **Track returns**: "What's the status of my return?" or "Where is my refund?"
- **Get help**: "What's your return policy?" or "How long do refunds take?"

### Example Conversation

```
You: I need to return an item from my recent order
Assistant: I'd be happy to help you with a return! Let me look up your recent orders.
[Shows order widget with order details]

You: I want to return the wireless headphones
Assistant: I can help you return the Wireless Headphones. What's the reason for your return?
• Defective/Damaged
• Wrong Item Received
• Changed My Mind
• Better Price Found

You: They're defective - one ear isn't working
Assistant: I'm sorry to hear that! Since this is a defective item, you qualify for:
✓ Full refund
✓ Free return shipping
✓ Express processing

[Shows return confirmation widget with shipping label option]
```

## 🔄 Dual-Input Architecture: Text + Widget

A key feature of this ChatKit implementation is supporting **both widget button clicks AND natural language text input**, with both converging into the same processing flow.

### How It Works

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER INPUT                                      │
│                                                                         │
│   ┌─────────────────┐              ┌─────────────────┐                  │
│   │  Widget Click   │              │   Text Input    │                  │
│   │  [Full Refund]  │              │ "I want a full  │                  │
│   │     button      │              │    refund"      │                  │
│   └────────┬────────┘              └────────┬────────┘                  │
│            │                                │                           │
│            ▼                                ▼                           │
│   ┌─────────────────┐              ┌─────────────────┐                  │
│   │   action()      │              │   Agent/LLM     │                  │
│   │ Direct mapping  │              │  Interprets NL  │                  │
│   │ from payload    │              │  + uses tools   │                  │
│   └────────┬────────┘              └────────┬────────┘                  │
│            │                                │                           │
│            └────────────┬───────────────────┘                           │
│                         ▼                                               │
│            ┌─────────────────────────┐                                  │
│            │    SESSION CONTEXT      │                                  │
│            │  (Unified State Store)  │                                  │
│            │                         │                                  │
│            │  resolution: FULL_REFUND│  ← Both paths update this!       │
│            └────────────┬────────────┘                                  │
│                         ▼                                               │
│            ┌─────────────────────────┐                                  │
│            │   Next Step / Finalize  │                                  │
│            └─────────────────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose |
|-----------|---------|
| **`action()` method** | Handles widget button clicks directly (no LLM) |
| **`respond()` method** | Routes text input through the Agent/LLM |
| **`set_user_selection` tool** | Agent tool to record typed selections |
| **Session Context** | Shared state that both paths write to |
| **`finalize_return_from_session`** | Creates return using session data |

### Examples

**Widget Button Click:**
```
User clicks [Full Refund] button
  → action() receives {type: "select_resolution", payload: {resolution: "FULL_REFUND"}}
  → Stores in session: resolution = "FULL_REFUND"
  → Shows shipping widget
```

**Natural Language Input:**
```
User types: "I would like a full refund please"
  → respond() sends to Agent with session context
  → Agent recognizes intent, calls set_user_selection(type="resolution", code="FULL_REFUND")
  → Stores in session: resolution = "FULL_REFUND"  
  → Agent calls get_shipping_options
  → Shows shipping widget
```

Both paths result in the same outcome! For detailed documentation, see [ARCHITECTURE.md](ARCHITECTURE.md#dual-input-architecture-text--widget-convergence).

## ☁️ Deploy to Azure Container Apps

### Using Azure Developer CLI (Recommended)

1. **Install Azure Developer CLI**
   ```bash
   # Windows
   winget install Microsoft.Azd
   
   # macOS
   brew install azure/azd/azd
   
   # Linux
   curl -fsSL https://aka.ms/install-azd.sh | bash
   ```

2. **Login and initialize**
   ```bash
   azd auth login
   azd init
   ```

3. **Configure environment variables**
   ```bash
   azd env set AZURE_OPENAI_ENDPOINT "https://your-resource.openai.azure.com/"
   azd env set AZURE_OPENAI_DEPLOYMENT "gpt-4o"
   ```

4. **Deploy**
   ```bash
   azd up
   ```

   This will:
   - Provision Azure Container Registry, Container Apps Environment, and Container App
   - Build and push the Docker image
   - Deploy the application
   - Output the application URL

### Manual Deployment

1. **Build the Docker image**
   ```bash
   docker build -t chatkit-order-returns:latest .
   ```

2. **Test locally with Docker**
   ```bash
   docker run -p 8000:8000 \
     -e AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/" \
     -e AZURE_OPENAI_DEPLOYMENT="gpt-4o" \
     chatkit-order-returns:latest
   ```

3. **Deploy to Azure Container Registry**
   ```bash
   az acr login --name <your-acr-name>
   docker tag chatkit-order-returns:latest <your-acr-name>.azurecr.io/chatkit-order-returns:latest
   docker push <your-acr-name>.azurecr.io/chatkit-order-returns:latest
   ```

4. **Deploy infrastructure with Bicep**
   ```bash
   az deployment group create \
     --resource-group <your-rg> \
     --template-file infra/main.bicep \
     --parameters baseName=chatkit azureOpenAIEndpoint="https://..." azureOpenAIDeployment=gpt-4o
   ```

## 🔐 Authentication

The application uses **Azure DefaultAzureCredential** which supports:

- **Local Development**: Azure CLI credentials (`az login`)
- **Azure-Hosted**: Managed Identity (automatically configured)
- **CI/CD**: Service Principal with environment variables

### Required Azure OpenAI RBAC Role

Grant the identity `Cognitive Services OpenAI User` role on your Azure OpenAI resource:

```bash
az role assignment create \
  --assignee <identity-principal-id> \
  --role "Cognitive Services OpenAI User" \
  --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<aoai-resource>
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Azure Container Apps                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                 Order Returns App                   │    │
│  │  ┌───────────────┐  ┌──────────────────────────┐    │    │
│  │  │   FastAPI     │  │    ChatKit Server        │    │    │
│  │  │   (main.py)   │──│  (retail/server.py)      │    │    │
│  │  └───────────────┘  └──────────────────────────┘    │    │
│  │          │                      │                   │    │
│  │          │              ┌───────┴────────┐          │    │
│  │          │              │  Retail Tools  │          │    │
│  │          │              │ (lookup/return/│          │    │
│  │          │              │  track/refund) │          │    │
│  │          ▼              └───────┬────────┘          │    │
│  │  ┌───────────────┐              │                   │    │
│  │  │ Cosmos DB     │◄─────────────┘                   │    │
│  │  │ (cosmos_store)│                                  │    │
│  │  └───────────────┘                                  │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                 │
└───────────────────────────┼─────────────────────────────────┘
                            │ Managed Identity
                            ▼
                 ┌─────────────────────┐
                 │   Azure OpenAI      │
                 │   (GPT-4o model)    │
                 └─────────────────────┘
```

### Components

| Component | Description |
|-----------|-------------|
| **FastAPI** | Web framework serving the ChatKit endpoint and static files |
| **ChatKit Server** | Implements OpenAI's ChatKit protocol for self-hosted chat |
| **Azure OpenAI Client** | Manages Azure OpenAI connections with auto-refresh tokens |
| **Cosmos DB Store** | Persists threads, messages, orders, and return data |
| **Retail Tools** | Function tools for order lookup, returns, tracking, and refunds |

## 🔧 Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | Required |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name | `gpt-4o` |
| `AZURE_OPENAI_API_VERSION` | API version | `2025-01-01-preview` |
| `COSMOS_ENDPOINT` | Azure Cosmos DB endpoint URL | Required |
| `COSMOS_DATABASE` | Cosmos DB database name | `db001` |
| `APP_HOST` | Application bind host | `0.0.0.0` |
| `APP_PORT` | Application port | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `BRAND_NAME` | App title in header | `Order Returns` |
| `BRAND_TAGLINE` | Subtitle in header | `AI-Powered Returns Management` |
| `BRAND_LOGO_URL` | Logo image URL | `/static/logo.png` |
| `BRAND_PRIMARY_COLOR` | Primary brand color (hex) | `#0078d4` |
| `BRAND_FAVICON_URL` | Favicon URL | `/static/favicon.ico` |

## 🎨 Branding & Customization

Customize the UI to match your organization's brand identity.

### Environment Variables

The easiest way to customize branding is through environment variables in your `.env` file:

```env
# Branding Configuration
BRAND_NAME=My Company Assistant
BRAND_TAGLINE=Your AI-Powered Helper
BRAND_LOGO_URL=/static/my-logo.png
BRAND_PRIMARY_COLOR=#ff6600
BRAND_FAVICON_URL=/static/my-favicon.ico
```

### Adding Your Logo

1. **Add your logo file** to the `static/` directory:
   ```
   static/
   ├── logo.png          # Your company logo (recommended: 32x32 or 40x40px)
   ├── favicon.ico       # Browser favicon
   └── index.html
   ```

2. **Update environment variables**:
   ```env
   BRAND_LOGO_URL=/static/logo.png
   BRAND_FAVICON_URL=/static/favicon.ico
   ```

3. **External logos** are also supported:
   ```env
   BRAND_LOGO_URL=https://mycompany.com/logo.png
   ```

### CSS Theme Customization

For advanced customization, edit `static/branding.css`:

```css
:root {
    /* Primary brand color - affects buttons, links, accents */
    --brand-primary: #0078d4;
    
    /* Header gradient */
    --header-gradient-start: #1a1a2e;
    --header-gradient-end: #16213e;
    
    /* Background colors */
    --background-primary: #0f0f23;
    --background-secondary: #1a1a2e;
    
    /* Text colors */
    --text-primary: #ffffff;
    --text-secondary: #a0a0b0;
    
    /* Logo dimensions */
    --logo-width: 32px;
    --logo-height: 32px;
}
```

### Example Brand Themes

The `branding.css` file includes commented examples for popular brands:

- **Microsoft** - Blue primary (#0078d4)
- **GitHub** - Purple primary (#8b5cf6)
- **Slack** - Green primary (#4a154b)
- **Salesforce** - Blue primary (#00a1e0)

### API Endpoint

Branding configuration is served at `/api/branding`:

```json
{
    "name": "Order Returns",
    "tagline": "AI-Powered Returns Management",
    "logoUrl": "/static/logo.png",
    "primaryColor": "#0078d4",
    "faviconUrl": "/static/favicon.ico"
}
```

This allows frontend applications (including React/Vue) to dynamically load branding at runtime.

## 📚 Resources

- [OpenAI ChatKit Documentation](https://platform.openai.com/docs/guides/custom-chatkit)
- [Azure OpenAI Documentation](https://learn.microsoft.com/azure/ai-services/openai/)
- [Azure Container Apps Documentation](https://learn.microsoft.com/azure/container-apps/)
- [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/)

## 🔄 Azure OpenAI vs Standard OpenAI

This project uses **Azure OpenAI** instead of the standard OpenAI endpoints. Here are the key differences:

### Configuration Changes

| Aspect | Standard OpenAI | Azure OpenAI |
|--------|-----------------|--------------|
| **Endpoint** | `https://api.openai.com/v1` | `https://your-resource.openai.azure.com/` |
| **Authentication** | API Key (`OPENAI_API_KEY`) | Azure AD / Managed Identity |
| **Model Reference** | Model name (`gpt-4o`) | Deployment name (custom) |
| **Client** | `AsyncOpenAI` | `AsyncAzureOpenAI` |

### Code Changes Made

1. **Azure Client Manager** (`azure_client.py`):
   ```python
   # Uses Azure-specific client with DefaultAzureCredential
   from openai import AsyncAzureOpenAI
   from azure.identity.aio import DefaultAzureCredential
   
   self.client = AsyncAzureOpenAI(
       azure_endpoint=settings.azure_openai_endpoint,
       azure_ad_token_provider=self._get_token,
       api_version=settings.azure_openai_api_version,
   )
   ```

2. **Model Wrapper** (`base_server.py`):
   ```python
   # Wraps Azure client for OpenAI Agents SDK
   azure_model = OpenAIChatCompletionsModel(
       model=settings.azure_openai_deployment,  # Deployment name, not model name
       openai_client=client,
   )
   ```

3. **Authentication**:
   - Local: Uses `az login` credentials via Azure CLI
   - Azure-hosted: Uses Managed Identity automatically
   - No API keys required in code

### Environment Variables

```env
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o          # Your deployment name
AZURE_OPENAI_API_VERSION=2025-01-01-preview

# Note: No OPENAI_API_KEY needed - uses Azure AD authentication
```

### RBAC Requirements

Grant your identity the `Cognitive Services OpenAI User` role:
```bash
az role assignment create \
  --assignee <your-identity> \
  --role "Cognitive Services OpenAI User" \
  --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<resource>
```

## 🧩 Extending with New Use Cases

This project uses a **layered architecture** that separates concerns and enables easy extension. See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed documentation.

### Layered Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ORCHESTRATION LAYER - UseCaseServer (extends ChatKitServer)               │
│    • Wires all layers together                                              │
│    • Handles ChatKit protocol (respond, action, widgets)                    │
└─────────────────────────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  DOMAIN LAYER   │ │  DATA LAYER     │ │  PRESENTATION   │
│  PolicyEngine   │ │  Repository     │ │  WidgetComposer │
│  DomainService  │ │  CosmosClient   │ │  WidgetTheme    │
│                 │ │                 │ │                 │
│  Pure logic     │ │  Data access    │ │  Widget build   │
│  No I/O         │ │  CRUD ops       │ │  Formatting     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Quick Guide to Create a New Use Case

1. **Create the folder structure:**
   ```
   use_cases/my_use_case/
   ├── __init__.py
   ├── server.py           # Extend UseCaseServer
   ├── session.py          # Extend SessionContext
   ├── domain/
   │   ├── policies.py     # Extend PolicyEngine
   │   └── services.py     # Extend DomainService
   └── presentation/
       └── composer.py     # Extend WidgetComposer
   ```

2. **Implement each layer:**
   - **Domain Layer**: Pure business rules (no I/O, easily unit tested)
   - **Data Layer**: Repository pattern for Cosmos DB access
   - **Presentation Layer**: WidgetComposer with theme support
   - **Session**: Track conversation state and flow steps

3. **Extend base classes from `core/`:**
   - `UseCaseServer` - Main server class
   - `PolicyEngine` - Business rules
   - `WidgetComposer` - Widget building
   - `SessionContext` - State management

4. **See the healthcare example** in `use_cases/healthcare/` for a complete skeleton.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## 📄 License

This project is licensed under the MIT License.
