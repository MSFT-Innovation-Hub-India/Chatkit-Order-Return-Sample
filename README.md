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
- **Return Confirmation**: Complete return request creation with tracking ID and shipping instructions
- **Return Policy Info**: Ask about return policies and get accurate answers via vector search (RAG)

> **Note**: Policy questions are answered using Azure OpenAI's file_search tool with a configured vector store (`POLICY_DOCS_VECTOR_STORE_ID`). Upload your policy documents to an Azure OpenAI vector store and configure the ID in `.env` to enable RAG-based policy responses.

## 👤 User Features

This application provides a personalized experience with the following user-facing capabilities:

### Authentication & Login
- **User Login**: Sign in with email and password to access your personalized experience
- **Sample Accounts**: Pre-configured test accounts for different membership tiers (Standard, Silver, Gold, Platinum)
- **Session Persistence**: Stay logged in across browser sessions with secure cookie-based authentication

### Customer Profile
- **View Customer Card**: Ask the agent "show my customer card" or "show my profile" to see your membership details
- **Membership Benefits**: See your tier status and associated perks (e.g., Platinum members get fee-free returns)

### Conversation Management
- **Start New Conversations**: Click "New Chat" to begin a fresh conversation thread at any time
- **View Past Threads**: Access your conversation history from the sidebar to review previous interactions
- **Thread Isolation**: Your conversations are private—only you can see threads associated with your account
- **Persistent History**: All conversations are stored in Azure Cosmos DB and available across sessions

### Smart Agent Behavior
- **Contextual Greetings**: The agent greets you by name and responds naturally to casual messages
- **Intent Detection**: The agent waits for you to indicate what you need before showing widgets

### Extensible Architecture

This solution follows a **practical, extensible architecture** that separates business logic from infrastructure. While this sample demonstrates a retail order returns use case, the same patterns can be adapted for other scenarios:

- **Healthcare**: Appointment scheduling, prescription refills, patient inquiries
- **Banking**: Account inquiries, transaction disputes, loan applications
- **Travel**: Booking management, itinerary changes, loyalty programs
- **HR/Internal**: Employee onboarding, IT helpdesk, policy questions

See [docs/ADDING_USE_CASES.md](docs/ADDING_USE_CASES.md) for guidance on creating new use cases by copying the `use_cases/retail/` reference implementation.

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

#### Key Components

| Component | Purpose |
|-----------|---------|
| **`action()` method** | Handles widget button clicks directly (no LLM) |
| **`respond()` method** | Routes text input through the Agent/LLM |
| **`set_user_selection` tool** | Agent tool to record typed selections |
| **Session Context** | Shared state that both paths write to |

#### Widget-Driven Flow (Fast Path)

When a user clicks a widget button (e.g., selects a return reason):
1. The click triggers a **direct tool call**—bypassing the LLM entirely
2. The session state is updated immediately
3. The **next widget in the workflow** is automatically presented

#### Text Input Flow (LLM Path)

When a user types instead of clicking (e.g., "I want a full refund"):
1. The text is sent to the **Agent/LLM** for interpretation
2. The Agent identifies intent and calls the appropriate tool
3. The session state converges to the **same state** as the widget path
4. The next widget is presented

> 💡 **Performance Note**: Widget clicks are faster (~50-100ms) since they skip the LLM inference step, but both paths result in identical outcomes.

📖 **[Full implementation details with code examples →](docs/DUAL_INPUT_ARCHITECTURE.md)**

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

📖 **[Implementation guide for tool execution status →](docs/WORKFLOW_STATUS.md)**

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
- **User Authentication**: Login-based thread isolation with per-user conversation history

### User Feedback (Thumbs Up/Down)

The application includes **ChatKit's built-in feedback feature** that allows users to rate assistant responses with thumbs up 👍 or thumbs down 👎 buttons.

| Feature | Details |
|---------|---------|
| **UI** | Thumbs up/down buttons appear on assistant text responses |
| **When Available** | Feedback is available when the agent responds with text (e.g., Q&A using vector search, policy questions, general inquiries) |
| **Storage** | Feedback is persisted to Azure Cosmos DB (`ChatKit_Feedback` container) |
| **Thread Association** | Each feedback record includes `thread_id` and `item_ids` for full conversation context |
| **User Tracking** | Feedback is linked to the authenticated user who provided it |

**How it works:**
1. User clicks 👍 or 👎 on an assistant text response
2. ChatKit sends an `items.feedback` request to the server
3. Server's `add_feedback()` method saves to Cosmos DB with thread reference
4. Reviewers can query feedback and see the full conversation context

> 💡 **Tip**: This is particularly useful for evaluating the quality of answers from vector search/RAG-based Q&A, such as when users ask about return policies or product information.

> ⚠️ **Note**: ChatKit's built-in feedback only supports positive/negative ratings. **Feedback comments** (text explaining why) are not available in ChatKit out of the box and are not implemented here. If you need comment-based feedback, you would need to build a custom solution.

#### Viewing Feedback with Conversation Context

Use the provided script to view feedback with full conversation details:

```bash
python scripts/view_feedback_context.py <thread_id>

# Example
python scripts/view_feedback_context.py thr_8dad4b9b
```

Or query Cosmos DB directly:

Run this query on the container name ChatKit_Feedback

```sql
-- Get all negative feedback (for review)
SELECT * FROM c 
WHERE c.kind = 'negative' 
ORDER BY c.created_at DESC
```

Take the thread_id for the above feedback and run this query on the container name ChatKit_Items
```
-- Get conversation context for a specific thread
SELECT * FROM c 
WHERE c.thread_id = '<thread_id>' 
ORDER BY c._ts
```

**Feedback document structure:**
```json
{
  "id": "9efada71-ec43-4ad2-b084-7a074eac1017",
  "thread_id": "thr_8dad4b9b",
  "item_ids": ["wf_c57aa63c", "msg_089308d3..."],
  "kind": "positive",
  "user_id": "CUST-1002",
  "comment": null,
  "created_at": "2026-01-23T12:20:44.070439+00:00"
}
```

## 🛠️ Technology Stack

- **Official ChatKit React UI**: Uses OpenAI's `@openai/chatkit-react` components
- **ChatKit Protocol**: Backend uses `openai-chatkit` Python library
- **OpenAI Agents SDK**: Built with `openai-agents` for tool orchestration and agent workflows (uses Responses API, not Chat Completions)
- **Azure OpenAI**: Powered by Azure OpenAI with GPT-4o model
- **Azure Cosmos DB**: Persistent storage for orders, customers, threads, returns, and user feedback
- **User Authentication**: Email/password login with session-based thread isolation
- **User Feedback**: ChatKit's built-in thumbs up/down with Cosmos DB persistence
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

For detailed architecture, deployment patterns, and customization, see [ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 📁 Project Structure

```
chatkit-order-returns/
├── main.py                  # FastAPI application entry point
├── config.py                # Configuration management (incl. branding)
├── base_server.py           # Reusable base server with Azure OpenAI
├── azure_client.py          # Azure OpenAI client manager
├── workflow_status.py       # ChatGPT-style tool execution status
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container build configuration
├── azure.yaml               # Azure Developer CLI configuration
├── README.md                # This file
├── .env.example             # Environment variables template
│
├── docs/                    # Documentation
│   ├── ARCHITECTURE.md      # Detailed architecture documentation
│   ├── ADDING_USE_CASES.md  # Guide to add new domains (healthcare, etc.)
│   ├── AUTHENTICATION.md    # User login, session management, thread isolation
│   ├── AZURE_OPENAI_ADAPTATIONS.md # Azure OpenAI setup
│   ├── DIAGRAMS.md          # Mermaid architecture diagrams
│   ├── DUAL_INPUT_ARCHITECTURE.md  # Widget + text input docs
│   ├── INDUSTRY_USE_CASES.md # Example use cases (healthcare, banking, etc.)
│   └── WORKFLOW_STATUS.md   # Tool execution status guide
│
├── frontend/                # React frontend (official ChatKit UI)
│   ├── package.json         # Node.js dependencies
│   ├── src/
│   │   ├── App.tsx          # Main ChatKit React component
│   │   └── main.tsx         # React entry point
│   └── vite.config.ts       # Vite build configuration
│
├── use_cases/
│   └── retail/              # Retail order returns (reference implementation)
│       ├── __init__.py      # Exports RetailChatKitServer
│       ├── server.py        # ChatKit server for retail returns
│       ├── tools.py         # Agent function tools
│       ├── tool_status.py   # Status messages for workflow indicators
│       ├── widgets.py       # Widget building functions
│       ├── cosmos_client.py # Cosmos DB client for retail data
│       └── cosmos_store.py  # ChatKit thread storage in Cosmos DB
│
├── static/
│   ├── index.html           # Vanilla JS frontend (fallback)
│   ├── dist/                # React build output (generated)
│   ├── branding.css         # Customizable brand colors/styles
│   └── logo.svg             # Default logo (replace with your own)
│
├── scripts/
│   ├── setup_azure_resources.ps1  # Azure setup (PowerShell)
│   ├── setup_azure_resources.sh   # Azure setup (Bash)
│   ├── populate_cosmosdb.py       # Load sample data into Cosmos DB
│   └── view_feedback_context.py   # View feedback with conversation context
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
  - Azure Cosmos DB (serverless recommended)
  - (Optional) Azure Container Apps for deployment
- Azure CLI and Azure Developer CLI (azd)

### Setting Up Azure Resources (New Subscription)

If you're setting up in a new subscription, use the provided setup scripts to create all required Azure resources:

**Windows (PowerShell):**
```powershell
.\scripts\setup_azure_resources.ps1 -ResourceGroup "my-order-returns-rg" -Location "eastus"
```

**Linux/macOS (Bash):**
```bash
chmod +x scripts/setup_azure_resources.sh
./scripts/setup_azure_resources.sh --resource-group "my-order-returns-rg" --location "eastus"
```

This creates:
- Cosmos DB account (serverless)
- Database with 13 containers (10 retail + 3 ChatKit)
- RBAC permissions for your user

After running the setup script:
1. Update `shared/cosmos_config.py` with the new endpoint
2. Run `python scripts/populate_cosmosdb.py` to load sample data
3. Run `python scripts/update_order_dates.py` to make order dates recent (see below)

### Refreshing Order Dates (Return Eligibility)

The sample orders have fixed dates that will eventually fall outside the **30-day return window**, making all items ineligible for returns. Run this script whenever orders stop being returnable:

```bash
python scripts/update_order_dates.py
```

This updates all order dates in Cosmos DB to the last 1–10 days and ensures their status is `delivered`, so items are eligible for returns again.

> **Tip**: Run this script any time you see "no items eligible for return" in the demo — it means the current date has moved past the return window of the sample data.

### Setting Up the Vector Store (Policy Documents)

The application uses Azure OpenAI's vector search for policy Q&A. The policy manual is located in:
```
data/sample/QnA Manuals/
```

To set up the vector store:

1. **Open Microsoft Foundry** (Azure AI Foundry portal)
2. **Navigate to your Azure OpenAI resource** (the same endpoint as `AZURE_OPENAI_ENDPOINT` in `.env`)
3. **Create a new Vector Store**:
   - Upload the document(s) from `data/sample/QnA Manuals/`
   - Wait for indexing to complete
4. **Copy the Vector Store ID** (e.g., `vs_qJ9rnh1DRn8RQrcMs5KojUDW`)
5. **Update `.env`** with the vector store ID:
   ```env
   POLICY_DOCS_VECTOR_STORE_ID=vs_your_vector_store_id
   ```

> **Note**: The vector store must be created in the same Azure OpenAI resource that the application uses for chat completions.

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

## � Demo Login Credentials

The application requires login to isolate conversation history per user. Use these demo credentials:

| Email | Password | Name | Membership Tier |
|-------|----------|------|-----------------|
| `jane.smith@email.com` | `demo123` | Jane Smith | Gold |
| `john.doe@email.com` | `demo123` | John Doe | Basic |
| `alice.johnson@email.com` | `demo123` | Alice Johnson | Platinum |
| `bob.wilson@email.com` | `demo123` | Bob Wilson | Basic |
| `carol.davis@email.com` | `demo123` | Carol Davis | Gold |

> **Note**: These are demo accounts pre-populated in Cosmos DB with sample orders. Gold and Platinum members get fee-free returns.

## �💬 Using the Order Returns Assistant

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

### ChatKit Domain Registration (Required for Production)

The ChatKit React component (`@openai/chatkit-react`) requires **domain verification** with OpenAI Platform for production deployments. Without this, the chat UI will fail to load with a "Domain verification failed" error.

> **Note**: Domain registration is **NOT required for local development** (`localhost`). The ChatKit component automatically allows localhost.

#### How to Register Your Domain

1. **Go to the OpenAI Platform**
   
   Navigate to: https://platform.openai.com/settings/organization/security/copilot

2. **Add your production domain**
   
   Register your Azure Container App URL (e.g., `chatkit-order-returns.redflower-f47b553c.eastus2.azurecontainerapps.io`)

3. **Copy the Domain Key**
   
   After registration, you'll receive a domain key starting with `domain_pk_...`

4. **Build with the domain key**
   
   The domain key must be embedded at **build time** (not runtime) because Vite inlines environment variables during the build process.

#### How the Domain Key is Used

| Layer | Location | Purpose |
|-------|----------|---------|
| **Dockerfile** | `ARG VITE_CHATKIT_DOMAIN_KEY` | Build-time argument passed during Docker build |
| **Vite Build** | `ENV VITE_CHATKIT_DOMAIN_KEY` | Exposed to Vite as environment variable |
| **React App** | `frontend/src/App.tsx` | Reads via `import.meta.env.VITE_CHATKIT_DOMAIN_KEY` |
| **ChatKit Component** | `<ChatKit domainKey={...} />` | Passed to ChatKit for domain verification |

**Code in `frontend/src/App.tsx`:**
```tsx
const chatkitDomainKey = import.meta.env.VITE_CHATKIT_DOMAIN_KEY
  || (window.location.hostname === 'localhost'
    ? 'localhost'
    : window.location.hostname);
```

The component uses the domain key in priority order:
1. `VITE_CHATKIT_DOMAIN_KEY` environment variable (if set at build time)
2. `'localhost'` for local development
3. Falls back to hostname (will fail verification without proper key)

### Manual Deployment

1. **Build the Docker image with domain key**
   ```bash
   # For production deployment, include the domain key
   docker build \
     --build-arg VITE_CHATKIT_DOMAIN_KEY=domain_pk_your_key_here \
     -t chatkit-order-returns:latest .
   
   # For local testing (no domain key needed)
   docker build -t chatkit-order-returns:latest .
   ```

2. **Test locally with Docker**
   ```bash
   docker run -p 8000:8000 \
     -e AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/" \
     -e AZURE_OPENAI_DEPLOYMENT="gpt-4o" \
     chatkit-order-returns:latest
   ```

3. **Build and push to Azure Container Registry**
   ```bash
   # Using az acr build (recommended - builds in Azure)
   az acr build \
     --registry <your-acr-name> \
     --resource-group <your-rg> \
     --image chatkit-order-returns:latest \
     --build-arg VITE_CHATKIT_DOMAIN_KEY=domain_pk_your_key_here \
     .
   
   # Or using local Docker
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

> ⚠️ **Important**: If you change domains (e.g., add a custom domain to your Container App), you'll need to register the new domain with OpenAI Platform and rebuild the Docker image with the new domain key.

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

📖 **[Full authentication documentation →](docs/AUTHENTICATION.md)**

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

📖 **[Detailed architecture diagrams (Mermaid) →](docs/DIAGRAMS.md)**

## 🔧 Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | Required |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name | `gpt-4o` |
| `AZURE_OPENAI_API_VERSION` | API version | `2025-01-01-preview` |
| `COSMOS_ENDPOINT` | Azure Cosmos DB endpoint URL | Required |
| `COSMOS_DATABASE` | Cosmos DB database name | `db001` |
| `POLICY_DOCS_VECTOR_STORE_ID` | Azure OpenAI vector store ID for policy RAG | Optional |
| `APP_HOST` | Application bind host | `0.0.0.0` |
| `APP_PORT` | Application port | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |

> **Branding variables** (`BRAND_NAME`, `BRAND_TAGLINE`, `BRAND_LOGO_URL`, etc.) are documented in the [Branding & Customization](#-branding--customization) section below.

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

📖 **[Complete Azure OpenAI adaptation guide →](docs/AZURE_OPENAI_ADAPTATIONS.md)**

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

This project is designed to be extended for other industries and scenarios. The retail implementation serves as a **reference pattern** that you can copy and adapt.

### Adding a New Domain

1. **Copy the retail folder structure:**
   ```
   use_cases/your_domain/
   ├── __init__.py
   ├── server.py       # Your ChatKit server (copy from retail)
   ├── tools.py        # Agent function tools for your domain
   ├── tool_status.py  # Status messages for tool execution
   ├── widgets.py      # Widget builders for your domain
   └── cosmos_client.py # Data access (if needed)
   ```

2. **Customize for your domain:**
   - Replace tools with your business logic
   - Add domain-specific widgets
   - Define tool status messages

3. **Register in `main.py`** to activate your use case

### What's Reusable

| Module | Purpose |
|--------|---------|
| `workflow_status.py` | ChatGPT-style progress indicators—pass your domain's tool_status messages |
| `wrap_for_hosted_tools()` | Status for FileSearchTool, WebSearchTool |
| `cosmos_store.py` | Thread persistence to Azure Cosmos DB |

### Example Domains

| Domain | Tools | Widgets |
|--------|-------|---------|
| **Healthcare** | lookup_patient, book_appointment | Patient card, appointment slots |
| **Banking** | get_account, transfer_funds | Account summary, transaction list |
| **Travel** | search_flights, book_hotel | Flight options, hotel cards |
| **HR** | lookup_employee, submit_request | Employee card, request form |

📖 **[Detailed industry use case examples →](docs/INDUSTRY_USE_CASES.md)**

📖 **[Full step-by-step guide with code examples →](docs/ADDING_USE_CASES.md)**

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## 📄 License

This project is licensed under the MIT License.
