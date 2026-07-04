# AuraWork - WhatsApp Work Companion

AuraWork is an intelligent WhatsApp assistant that aggregates Slack, Jira, Gmail, and Google Calendar into a single chat window, enabling employees to manage notifications, check schedules, log work, and draft updates on the go.

This repository currently implements the core infrastructure, database state models, and third-party API integrations (Days 1–6).

---

## 🚀 Getting Started

### 1. Installation

Create a virtual environment and install the required dependencies:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (PowerShell):
.\venv\Scripts\activate
# On Linux/macOS:
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
* `WHATSAPP_TOKEN` & `PHONE_NUMBER_ID` (from Meta Developer Console)
* `SLACK_BOT_TOKEN` (from Slack Developer Console)
* `JIRA_URL`, `JIRA_EMAIL`, & `JIRA_API_TOKEN` (from Atlassian Account Settings)
* `GOOGLE_CLIENT_ID` & `GOOGLE_CLIENT_SECRET` (from Google Cloud Console)

### 3. Expose Local Server (For WhatsApp Webhook Verification)

WhatsApp Webhooks require a secure HTTPS URL. You can expose your local server using Cloudflare Tunnel:

```bash
# Expose port 8000
cloudflared tunnel --url http://localhost:8000
```

Use the generated URL (e.g., `https://xxxx.trycloudflare.com`) to set up the Webhook configuration in the Meta Developer Console:
* **Callback URL**: `https://xxxx.trycloudflare.com/webhook`
* **Verify Token**: `sync_copilot_verify_token` (matches the `VERIFY_TOKEN` in `.env`)

---

## 🛠️ Testing Commands (Days 1-6 Routes)

You can interact with the webhook using the following slash commands in your WhatsApp chat to verify each API service is successfully configured:

* `/login` - Receive your Google OAuth link to authenticate Google Calendar and Gmail
* `/emails` - Retrieve unread Gmail messages
* `/calendar` - Retrieve upcoming Google Calendar events
* `/slack [channel-name] [message]` - Post a direct message to a Slack channel
* `/slack_mentions` - Fetch recent unread mentions/notifications on Slack
* `/jira` - View your active assigned Jira issues
* `/jira_log [issue-key] [time] [comment]` - Log work logged directly to Jira (e.g., `/jira_log SEC-42 1h 30m UI fix`)
* `/help` - Show all available diagnostic commands
