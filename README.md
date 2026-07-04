# 🤖 AuraWork — WhatsApp AI Work Companion

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.111-green?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Google_Gemini-2.5_Flash-orange?style=for-the-badge&logo=google&logoColor=white" alt="Google Gemini" />
  <img src="https://img.shields.io/badge/WhatsApp_Cloud_API-Meta-blueviolet?style=for-the-badge&logo=whatsapp&logoColor=white" alt="WhatsApp Cloud API" />
  <img src="https://img.shields.io/badge/SQLite-Database-lightgrey?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite" />
</p>

---

## 🌟 About AuraWork

**AuraWork** is an intelligent, agent-driven WhatsApp workspace companion. It acts as a single, mobile-first interface that aggregates and automates actions across your most-used productivity tools: **Slack**, **Jira**, **Gmail**, and **Google Calendar**. 

Instead of jumping between multiple apps, desktop portals, or notifications on the go, AuraWork lets employees manage tasks, log work hours, view schedules, draft emails, and post updates directly from their mobile WhatsApp chat using natural language or structured commands.

---

## 🚀 Why AuraWork? (The Value Proposition)

*   **Zero Context Switching**: Access calendar, mail, team chat, and project boards without leaving your messaging app.
*   **Mobile-First Productivity**: Log a Jira ticket or catch up on Slack mentions while walking to a meeting, traveling, or offline from your laptop.
*   **Intelligent Execution**: Powered by an agentic LLM (Gemini 2.5 Flash), AuraWork doesn't just match keywords—it understands intent, plans multi-step actions, and executes them on your behalf.
*   **Privacy-First Encryption**: Secure storage for all OAuth tokens and API credentials using AES-128 Fernet cryptography.

---

## 🗺️ System Architecture & Workflow

AuraWork leverages a secure gateway and a model-driven execution loop to safely route and resolve requests.

```mermaid
sequenceDiagram
    autonumber
    actor User as WhatsApp Mobile
    participant Meta as Meta Cloud API
    participant Tunnel as Cloudflare Tunnel
    participant App as FastAPI Webhook Gateway
    database DB as SQLite Database
    participant Agent as Gemini Agent (Planner)
    participant API as Third-Party APIs (Slack/Jira/Google)

    User->>Meta: Sends text message ("Fetch Jira and send to Slack")
    Meta->>Tunnel: Forwards event payload (Webhook POST)
    Tunnel->>App: Relays request to local server (/webhook)
    App->>DB: Resolves user identity & decrypts OAuth tokens
    App->>Agent: Passes message and user context
    Note over Agent: Planner reads request &<br/>decides step-by-step tools to call
    Agent->>API: Executes tool: Fetch Jira Issues
    API-->>Agent: Returns active tickets
    Agent->>API: Executes tool: Send Slack message
    API-->>Agent: Confirms Slack delivery
    Agent-->>App: Generates final conversational confirmation
    App->>Meta: Calls WhatsApp Graph API (Send message)
    Meta-->>User: Delivers reply ("Issues fetched and Slack sent!")
```

---

## 📂 Project Structure

```bash
whatsapp-ai-agent/
├── agent/                   # Agent reasoning & execution loops
│   └── planner.py           # Gemini agent planner & tool-calling loop
├── database/                # Database configuration & schemas
│   ├── models.py            # SQLAlchemy Database Schemas
│   └── postgres.py          # SQLite engine and session utilities
├── scheduler/               # Background schedulers (threads)
│   └── reminder_scheduler.py# Daily standup & digest prompts
├── services/                # Core helper modules
│   ├── encryption.py        # Fernet AES token encryption
│   ├── google_oauth.py      # Google OAuth 2.0 flow & auto-refresh
│   └── whatsapp.py          # Meta Graph API sender & read markers
├── tools/                   # API Integration plugins (Agent tools)
│   ├── calendar.py          # Google Calendar integration
│   ├── gmail.py             # Gmail read & send/draft capabilities
│   ├── jira.py              # Jira issue viewer & work log manager
│   └── slack.py             # Slack messages & notifications
├── app.py                   # Main FastAPI server & webhook processor
├── config.py                # Environment configuration registry
├── check_db.py              # Database status checker (debug tool)
├── reset_db.py              # Database reset utility (debug tool)
├── requirements.txt         # Project dependencies
└── README.md                # Project documentation
```

---

## 🛠️ Getting Started

### 1. Installation

Set up a virtual environment and install the dependencies:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Copy the example environment file and fill in your integration keys:

```bash
cp .env.example .env
```

Ensure the following variables are configured in `.env`:
*   `WHATSAPP_TOKEN` & `PHONE_NUMBER_ID` (from Meta Developer Console)
*   `SLACK_BOT_TOKEN` (from Slack Developer Console)
*   `JIRA_URL`, `JIRA_EMAIL`, & `JIRA_API_TOKEN` (from Atlassian Account Settings)
*   `GOOGLE_CLIENT_ID` & `GOOGLE_CLIENT_SECRET` (from Google Cloud Console)
*   `GEMINI_API_KEY` (from Google AI Studio)
*   `ENCRYPTION_KEY` (Generate a secure key for credential encryption)

### 3. Running the Server & Exposing the Webhook

FastAPI runs locally on port 8000. WhatsApp requires a secure, public HTTPS URL. Expose it using a Cloudflare Tunnel:

```bash
# Terminal 1: Run the FastAPI Server
uvicorn app:app --reload

# Terminal 2: Start Cloudflare Tunnel
cloudflared tunnel --url http://localhost:8000
```

Use the generated Cloudflare URL (e.g., `https://xxxx.trycloudflare.com`) to register the Webhook callback in the Meta Developer Console:
*   **Callback URL**: `https://xxxx.trycloudflare.com/webhook`
*   **Verify Token**: `sync_copilot_verify_token` (must match the `VERIFY_TOKEN` in your `.env`)
*   **Webhooks Fields**: Subscribe to `messages`.

---

## 🕹️ How to Interact with AuraWork

AuraWork supports both direct slash commands (quick diagnostics) and agentic natural language processing:

### ⚙️ Diagnostic Slash Commands
Type these directly in your WhatsApp chat window to check configuration status:
*   `/login` — Get your Google OAuth authorization link (authenticates Gmail/Calendar).
*   `/emails` — Fetch your latest unread Gmail messages.
*   `/calendar` — View your upcoming Google Calendar meetings.
*   `/slack [channel] [message]` — Send a message to a specific Slack channel.
*   `/slack_mentions` — List your recent unread Slack mentions.
*   `/jira` — View active Jira tickets assigned to you.
*   `/jira_log [issue-key] [time] [comment]` — Log work directly on a ticket (e.g., `/jira_log SEC-42 1h 30m UI fix`).
*   `/help` — Display the list of diagnostic commands.

### 🧠 Agentic Natural Language
Because AuraWork runs an **Agentic execution loop** with Gemini 2.5 Flash, you can chat with it conversationally:
*   *"Do I have any meetings today?"* (Invokes Google Calendar)
*   *"Log 2 hours on issue project-102 and comment 'reviewed code'."* (Invokes Jira)
*   *"Send an email to boss@company.com with the subject 'Daily Report' saying 'Everything looks good'."* (Invokes Gmail API)
*   *"Ask the engineering channel on Slack if the build is ready."* (Invokes Slack)
