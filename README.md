# ChatKit Order Returns Sample with Azure OpenAI

A self-hosted ChatKit order returns management application powered by OpenAI Agents SDK, Azure OpenAI, featuring interactive widgets and a modular architecture designed for retail customer service.

## 🛒 Order Returns Capabilities

This sample implements a complete **retail order returns workflow** with the following features:

- **Customer Lookup**: Search and identify customers by email, name, or customer ID
- **Order History**: View recent orders with product details, prices, and order status
- **Return Eligibility**: Automatic validation of return windows and product eligibility
- **Return Reasons**: Guided selection of return reasons (defective, wrong item, changed mind, etc.)
- **Resolution Options**: Support for full refunds, exchanges, and store credit
- **Shipping Methods**: Multiple return shipping options (prepaid label, drop-off, scheduled pickup)
- **Return Confirmation**: Complete return request creation with tracking ID and shipping label

### Extensible Architecture

This solution follows a **layered, extensible architecture** that separates business logic from infrastructure. While this sample demonstrates a retail order returns use case, the same patterns can be adapted for other scenarios:

- **Healthcare**: Appointment scheduling, prescription refills, patient inquiries
- **Banking**: Account inquiries, transaction disputes, loan applications
- **Travel**: Booking management, itinerary changes, loyalty programs
- **HR/Internal**: Employee onboarding, IT helpdesk, policy questions

See the `core/` framework module and `use_cases/healthcare/` skeleton for guidance on creating new use cases.

## ⚡ Technical Capabilities

### Immersive Widget-Driven Workflow

Instead of requiring users to type their choices at every step, this application presents **interactive UI widgets** that guide users through the workflow. This creates an immersive, point-and-click experience while still supporting natural language when preferred.

### Dual-Input Architecture: Widgets + Text

Users can **interchangeably** use either input mode at any point in the conversation:

| Input Mode | How It Works | Response Time |
|------------|--------------|---------------|
| **Widget Click** | Direct action execution—no LLM call needed | ⚡ Immediate |
| **Text Input** | Agent interprets intent via LLM, then executes | 🔄 Slightly longer |

Both modes converge to the **same application state**, ensuring a consistent experience regardless of how the user interacts.

### Widget-Driven Flow Navigation

When a user clicks a widget button (e.g., selects a return reason):
1. The click triggers a **direct tool call**—bypassing the LLM entirely
2. The session state is updated immediately
3. The **next widget in the workflow** is automatically presented

This creates a fast, guided experience where each action seamlessly leads to the next step.

### Text Input Convergence

When a user types instead of clicking (e.g., "I want a full refund"):
1. The text is sent to the **Agent/LLM** for interpretation
2. The Agent identifies intent and calls the appropriate tool
3. The session state converges to the **same state** as the widget path
4. The next widget is presented

> 💡 **Performance Note**: Widget clicks are faster since they skip the LLM inference step, but both paths result in identical outcomes.

### Real-Time Tool Execution Status

Like ChatGPT, this application shows **live status indicators** when the agent executes tools:

```
🔍 Looking up customer...
📦 Fetching your orders...
✅ Customer found
✅ Orders retrieved
```

This provides transparency into what the agent is doing, especially when:
- Looking up customer information
- Fetching order history and returnable items
- Checking return eligibility
- Creating return requests

The status indicators use ChatKit's **Workflow API** and appear as collapsible progress sections.

### Extensible Tool Architecture

The function tools can be extended beyond local implementations:
- Current tools use **OpenAI Agents SDK** `@function_tool` decorators
- Tools can be extended to connect to **MCP (Model Context Protocol) Servers** for distributed tool execution
- This enables integration with external services and enterprise systems

### Azure Cosmos DB Integration

Every action in the workflow involves **Azure Cosmos DB** operations:
- **Customer Lookup**: Query customers by email, name, or ID
- **Order Retrieval**: Fetch order history and product details
- **Eligibility Checks**: Validate return windows and policies
- **Return Creation**: Insert new return requests with tracking IDs
- **Thread Persistence**: Store conversation history and session state

## 🛠️ Technology Stack

- **Official ChatKit React UI**: Uses OpenAI's `@openai/chatkit-react` components
- **ChatKit Protocol**: Backend uses `openai-chatkit` Python library
- **OpenAI Agents SDK**: Built with `openai-agents` for tool orchestration and agent workflows (uses Responses API, not Chat Completions)
- **Azure OpenAI**: Powered by Azure OpenAI with GPT-4o model
- **Azure Cosmos DB**: Persistent storage for orders, customers, and returns
- **Interactive Widgets**: Rich UI with buttons, forms, order details, and status badges
- **Tool Execution Status**: ChatGPT-style progress indicators showing real-time tool activity
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
   
   Edit `.env` with your Azure settings:
   ```env
   # Azure OpenAI Configuration
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT=gpt-4o
   AZURE_OPENAI_API_VERSION=2025-01-01-preview
   
   # Azure Cosmos DB Configuration
   COSMOS_ENDPOINT=https://your-cosmosdb.documents.azure.com:443/
   COSMOS_DATABASE=db001
   
   # Optional: Branding
   BRAND_NAME=Order Returns
   BRAND_TAGLINE=AI-Powered Returns Management
   ```

5. **Login to Azure (for authentication)**
   ```bash
   az login
   ```

6. **Start the backend server**
   ```bash
   python main.py
   ```
   The backend will start on `http://localhost:8000`

7. **Start the frontend development server** (in a new terminal)
   ```bash
   cd frontend
   npm run dev
   ```
   The frontend will start on `http://localhost:3000`

8. **Open your browser**
   Navigate to `http://localhost:3000`

## 💬 Using the Order Returns Assistant

The ChatKit Order Returns app understands natural language commands:

- **Check orders**: "Show me my recent orders" or "I want to check order #12345"
- **Start returns**: "I need to return an item" or "This product is defective"
- **Track returns**: "What's the status of my return?" or "Where is my refund?"
- **Get help**: "What's your return policy?" or "How long do refunds take?"

### Example Conversation

```
You: I need to return an item from my recent order
Assistant: I'd be happy to help you with a return! Could you please provide your email address or name so I can look up your account?

You: I'm jane.smith@email.com
Assistant: Thanks, Jane! I found your account. Let me pull up your recent orders.
[Shows customer card with account details]
[Shows order widget with order details]

You: I want to return the wireless headphones
Assistant: I can help you return the Wireless Headphones. What's the reason for your return?
[Shows return reasons widget]
• Defective/Damaged
• Wrong Item Received
• Changed My Mind
• Better Price Found

You: They're defective - one ear isn't working
Assistant: I'm sorry to hear that! Since this is a defective item, you qualify for:
✓ Full refund
✓ Free return shipping
✓ Express processing

[Shows resolution options widget]
[Shows return confirmation widget with shipping label option]
```

## 🔄 Dual-Input Architecture: Text + Widget

This application supports **both widget button clicks AND natural language text input**, with both converging into the same processing flow.

| Input Mode | How It Works | Response Time |
|------------|--------------|---------------|
| **Widget Click** | Direct action execution—no LLM call needed | ⚡ Immediate |
| **Text Input** | Agent interprets intent via LLM, then executes | 🔄 Slightly longer |

Both modes converge to the **same application state**, ensuring a consistent experience regardless of how the user interacts.

📖 **[Read the full Dual-Input Architecture documentation →](docs/DUAL_INPUT_ARCHITECTURE.md)**

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
   from agents.models.openai_responses import OpenAIResponsesModel
   
   azure_model = OpenAIResponsesModel(
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
