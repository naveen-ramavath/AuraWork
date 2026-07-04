# from prompt_toolkit.layout import mouse_handlers
import logging
from fastapi import FastAPI, Request, Response, Query, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from config import Config
from database.postgres import get_db, init_db
from database.models import User, SessionState
from services.whatsapp import send_text, mark_read
from services.google_oauth import get_google_auth_url, handle_oauth_callback
from tools.slack import post_message_to_slack, get_slack_unread_mentions
from tools.jira import get_assigned_jira_issues, log_jira_work, create_jira_ticket
from tools.gmail import fetch_unread_emails
from tools.calendar import fetch_calendar_events
from agent.planner import SyncCopilotAgent
from scheduler.reminder_scheduler import start_scheduler

print("=" * 60)
print("SYNCCOPILOT APP STARTED")
print("=" * 60)

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="SyncCopilot AI Webhook Gateway")

@app.on_event("startup")
def on_startup():
    """Initializes the database tables and launches the background scheduler."""
    init_db()
    logger.info("Database initialized successfully.")
    start_scheduler()
    logger.info("Background scheduler started successfully.")

@app.get("/")
def read_root():
    return {"status": "running", "service": "SyncCopilot AI Webhook Gateway"}

@app.get("/webhook")
def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """Handles Meta Cloud API Webhook Challenge Verification."""
    if hub_mode == "subscribe" and hub_verify_token == Config.VERIFY_TOKEN:
        logger.info("Webhook verified successfully.")
        return Response(content=hub_challenge, media_type="text/plain")
    logger.warning("Webhook verification failed. Token mismatch.")
    return Response(content="Verification failed", status_code=403)
print("************ POST /webhook HIT ************")
@app.post("/webhook")
async def process_webhook(request: Request, db: Session = Depends(get_db)):
    print(">>> INSIDE process_webhook() <<<")
    """Receives inbound messages and events from Meta WhatsApp Cloud API."""
    try:
        body = await request.json()
        print("=" * 80)
        print(body)
        print("=" * 80)

        logger.info(f"Received Webhook Event: {body}")
        
        # Check if this is a message delivery / receipt update
        entry = body.get("entry", [])
        if not entry:
            return "OK"
        
        changes = entry[0].get("changes", [])
        if not changes:
            return "OK"
            
        value = changes[0].get("value", {})
        if "messages" not in value:
            # Status updates (read, sent, delivered) are ignored to avoid infinite loops
            return "OK"
            
        message = value["messages"][0]
        sender = message["from"]  # WhatsApp ID / Phone number of sender
        msg_id = message["id"]
        print("MARK READ")
        mark_read(msg_id)
        print("MARK READ DONE")
                
        # Extract message body
        if "text" in message:
            text_body = message["text"]["body"].strip()
            logger.info(f"Received text message from {sender}: {text_body}")
            
            # Check if this is a manual diagnostics override slash command
            print("COMMAND =", text_body)
            if text_body.startswith("/"):
                print("STEP 1: Inside command handler")
                
                response_text = handle_direct_commands(sender, text_body, db)
                print("STEP 2: Command handler completed")

            else:
                print("STEP 3: Creating SyncCopilotAgent")
                agent = SyncCopilotAgent(sender, db)

                print("STEP 4: Running agent")
                response_text = agent.run(text_body)

                print("STEP 5: Agent finished")
                print("Agent Response:", response_text)

            print("STEP 6: Calling send_text()")
            success = send_text(sender, response_text)

            print("STEP 7: send_text returned:", success)

            logger.info(f"Sending reply to {sender}")
            logger.info(f"Reply: {response_text}")
            logger.info(f"Message sent: {success}")
            
        else:
            # Handle media, documents, or location updates
            send_text(sender, "I currently only support text commands. Media support coming soon!")
            
    except Exception as e:
        logger.exception("Error handling WhatsApp Webhook")
        
    # Always return HTTP 200 to prevent Meta from retrying and causing duplicates
    return "OK"

@app.get("/auth/login")
def google_login(phone: str = Query(..., description="The user WhatsApp phone number to bind credentials to")):
    """Generates the Google OAuth link for a specific phone number."""
    auth_url = get_google_auth_url(phone)
    return {
        "message": f"Redirect user to this URL to authenticate Google Workspace.",
        "url": auth_url
    }

@app.get("/auth/callback", response_class=HTMLResponse)
def google_callback(code: str = Query(...), state: str = Query(...)):
    """Handles Google OAuth redirection, state carries the phone number."""
    success = handle_oauth_callback(code, state)
    if success:
        return """
        <html>
            <head><title>Success</title></head>
            <body style="font-family: sans-serif; text-align: center; margin-top: 100px;">
                <h1 style="color: #2e7d32;">Authentication Successful!</h1>
                <p>SyncCopilot has connected to your Google Calendar & Gmail.</p>
                <p>You can close this tab and return to WhatsApp.</p>
            </body>
        </html>
        """
    else:
        return """
        <html>
            <head><title>Failed</title></head>
            <body style="font-family: sans-serif; text-align: center; margin-top: 100px;">
                <h1 style="color: #c62828;">Authentication Failed</h1>
                <p>An error occurred exchanging tokens with Google. Please try again.</p>
            </body>
        </html>
        """

def handle_direct_commands(sender: str, text: str, db: Session) -> str:
    """A direct router to test Google, Slack, and Jira integrations directly before wiring LLM."""
    cmd = text.lower()
    
    # Initialize user database registration if they don't exist
    user = db.query(User).filter(User.phone_number == sender).first()
    if not user:
        user = User(phone_number=sender)
        db.add(user)
        db.commit()
        db.refresh(user)
        
    session_state = db.query(SessionState).filter(SessionState.phone_number == sender).first()
    if not session_state:
        session_state = SessionState(phone_number=sender, state="idle")
        db.add(session_state)
        db.commit()
    
    # Command Processing
    if cmd == "/login":
        auth_url = get_google_auth_url(sender)
        return f"To connect Google Calendar and Gmail to SyncCopilot, click this link:\n\n{auth_url}"
        
    elif cmd.startswith("/slack "):
        parts = text.split(" ", 2)
        if len(parts) < 3:
            return "Usage: /slack [channel-name] [message]"
        channel = parts[1]
        msg = parts[2]
        success = post_message_to_slack(channel, msg)
        return f"Message posted to Slack channel #{channel}!" if success else "Failed to send message to Slack. Check your token."

    elif cmd == "/slack_mentions":
        mentions = get_slack_unread_mentions()
        if not mentions:
            return "No recent unread Slack mentions found!"
        reply = "🔔 *Recent Slack Mentions:*\n"
        for m in mentions:
            reply += f"- *@{m['username']}* in #{m['channel']}: \"{m['text']}\"\n"
        return reply

    elif cmd == "/jira":
        issues = get_assigned_jira_issues()
        if not issues:
            return "No assigned active Jira issues found!"
        reply = "📋 *Your Open Jira Tasks:*\n"
        for issue in issues:
            reply += f"- *{issue['key']}* [{issue['status']}]: {issue['summary']} (Priority: {issue['priority']})\n"
        return reply

    elif cmd.startswith("/jira_log "):
        parts = text.split(" ", 4)
        if len(parts) < 3:
            return "Usage: /jira_log [issue_key] [time] [optional comment]"
        key = parts[1]
        time_spent = parts[2]
        comment = parts[3] if len(parts) > 3 else "Logged via SyncCopilot WhatsApp"
        success = log_jira_work(key, time_spent, comment)
        return f"Logged {time_spent} on {key} successfully!" if success else f"Failed to log work on {key}."

    elif cmd == "/emails":
        emails = fetch_unread_emails(sender)
        if not emails:
            return "📬 No unread emails found, or you need to run /login first."
        reply = "📬 *Unread Gmail Messages:*\n"
        for em in emails:
            reply += f"- *From*: {em['sender']}\n  *Subj*: {em['subject']}\n  _{em['snippet'][:80]}..._\n\n"
        return reply

    elif cmd == "/calendar":
        events = fetch_calendar_events(sender)
        if not events:
            return "📅 No upcoming events found, or you need to run /login first."
        reply = "📅 *Your Calendar Schedule:*\n"
        for ev in events:
            reply += f"- *{ev['summary']}*\n  Time: {ev['start']} to {ev['end']}\n  [Link]({ev['htmlLink']})\n\n"
        return reply
        
    elif cmd == "/help":
        print("INSIDE HELP COMMAND")
        return ("👋 Welcome to SyncCopilot!\n\n"
                "Here are your quick developer commands:\n"
                "• `/login` : Link your Google Workspace\n"
                "• `/emails` : Show unread Gmails\n"
                "• `/calendar` : Show upcoming meetings\n"
                "• `/slack [channel] [msg]` : Post directly to Slack\n"
                "• `/slack_mentions` : Retrieve Slack notifications\n"
                "• `/jira` : Show assigned tasks\n"
                "• `/jira_log [key] [time]` : Log Jira work hours\n"
                "• `/help` : Show this list")
                
    else:
        return "Command not recognized. Type `/help` to see available commands. Full AI Agent is running! Ask me in plain English."
