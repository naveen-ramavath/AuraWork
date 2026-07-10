import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    # Server Settings
    PORT = int(os.getenv("PORT", 8000))
    HOST = os.getenv("HOST", "0.0.0.0")

    # WhatsApp Cloud API Settings
    WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
    PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")
    VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "sync_copilot_verify_token")
    API_VERSION = os.getenv("API_VERSION", "v25.0")

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sync_copilot.db")

    # Slack Settings
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")

    # Jira Settings
    JIRA_URL = os.getenv("JIRA_URL", "")
    JIRA_EMAIL = os.getenv("JIRA_EMAIL", "")
    JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")

    # Google OAuth 2.0 Settings
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")

    # OpenAI / Claude / Gemini API Settings (for future agent integration)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

    AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
