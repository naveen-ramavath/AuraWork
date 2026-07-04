import json
import time
import logging
import datetime
import threading
from sqlalchemy.orm import Session

from database.postgres import SessionLocal
from database.models import User, SessionState
from services.whatsapp import send_text
from tools.slack import get_slack_unread_mentions
from tools.gmail import fetch_unread_emails

logger = logging.getLogger(__name__)

def run_scheduler_loop():
    """Infinite loop executing scheduler checks once every minute."""
    logger.info("SyncCopilot Background Scheduler started.")
    while True:
        try:
            db = SessionLocal()
            check_and_send_alerts(db)
            db.close()
        except Exception as e:
            logger.error(f"Error in scheduler execution cycle: {e}")
        # Wait 60 seconds before next check
        time.sleep(60)

def start_scheduler():
    """Starts the background scheduler as a daemon thread."""
    thread = threading.Thread(target=run_scheduler_loop, daemon=True)
    thread.start()

def check_and_send_alerts(db: Session):
    """Checks all registered users and triggers morning standups and evening summaries."""
    users = db.query(User).all()
    now = datetime.datetime.utcnow()
    
    # Calculate local hours based on simple offset (defaulting to IST UTC+5:30)
    # Real-world system utilizes py tz to support user-specific timezones
    local_offset = datetime.timedelta(hours=5, minutes=30)
    local_now = now + local_offset
    current_date_str = local_now.strftime("%Y-%m-%d")
    current_hour = local_now.hour
    current_minute = local_now.minute

    for user in users:
        # Load or create session state for user
        state = db.query(SessionState).filter(SessionState.phone_number == user.phone_number).first()
        if not state:
            state = SessionState(phone_number=user.phone_number, state="idle")
            db.add(state)
            db.commit()
            db.refresh(state)

        # Parse context metadata
        context = {}
        if state.context_data:
            try:
                context = json.loads(state.context_data)
            except Exception:
                context = {}

        # 1. Morning Standup Ping: Triggers at 9:00 AM
        if current_hour == 9 and current_minute == 0:
            if context.get("last_standup_ping_date") != current_date_str:
                logger.info(f"Sending morning standup alert to user {user.phone_number}...")
                
                # Send message
                msg = ("👋 *Good morning!* It is 9:00 AM. Time to log your standup.\n\n"
                       "Reply directly to this chat with your accomplishments (e.g. Completed auth tests, starting deployment today) "
                       "and I will automatically update Jira and Slack for you!")
                
                success = send_text(user.phone_number, msg)
                if success:
                    # Update session state metadata to prevent double-sending
                    context["last_standup_ping_date"] = current_date_str
                    state.context_data = json.dumps(context)
                    db.commit()

        # 2. Evening Summary Digest: Triggers at 5:00 PM (17:00)
        if current_hour == 17 and current_minute == 0:
            if context.get("last_evening_digest_date") != current_date_str:
                logger.info(f"Generating evening digest for user {user.phone_number}...")
                
                # Fetch Slack notifications and Gmail messages
                slack_mentions = get_slack_unread_mentions()
                emails = fetch_unread_emails(user.phone_number, limit=3)
                
                digest = "🔔 *Your SyncCopilot Evening Digest:*\n\n"
                
                # Add Slack notifications
                if slack_mentions:
                    digest += "*Slack Mentions:*\n"
                    for m in slack_mentions[:3]:
                        digest += f"- *@{m['username']}* in #{m['channel']}: \"{m['text']}\"\n"
                else:
                    digest += "*Slack*: No unread mentions.\n"
                    
                digest += "\n"
                
                # Add Gmail notifications
                if emails:
                    digest += "*Unread Emails:*\n"
                    for em in emails:
                        digest += f"- *From*: {em['sender']}\n  *Subj*: {em['subject']}\n"
                else:
                    digest += "*Gmail*: No unread emails.\n"
                
                success = send_text(user.phone_number, digest)
                if success:
                    context["last_evening_digest_date"] = current_date_str
                    state.context_data = json.dumps(context)
                    db.commit()
