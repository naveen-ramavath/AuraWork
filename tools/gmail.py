import base64
import logging
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from services.google_oauth import get_user_credentials

logger = logging.getLogger(__name__)

def get_gmail_service(phone_number: str):
    """Initializes the Gmail API service using the user's Google credentials."""
    creds = get_user_credentials(phone_number)
    if not creds:
        logger.warning(f"No Google credentials found for user {phone_number}.")
        return None
    return build("gmail", "v1", credentials=creds)

def fetch_unread_emails(phone_number: str, max_results: int = 5) -> list:
    """Fetches unread emails from the inbox and parses basic metadata."""
    service = get_gmail_service(phone_number)
    if not service:
        return []

    try:
        # Fetch list of messages
        results = service.users().messages().list(
            userId="me", q="is:unread label:INBOX", maxResults=max_results
        ).execute()
        
        messages = results.get("messages", [])
        email_list = []
        
        for msg in messages:
            msg_id = msg["id"]
            msg_details = service.users().messages().get(userId="me", id=msg_id, format="metadata").execute()
            
            headers = msg_details.get("payload", {}).get("headers", [])
            subject = "No Subject"
            sender = "Unknown Sender"
            date = ""
            
            for header in headers:
                if header["name"] == "Subject":
                    subject = header["value"]
                elif header["name"] == "From":
                    sender = header["value"]
                elif header["name"] == "Date":
                    date = header["value"]
            
            snippet = msg_details.get("snippet", "")
            
            email_list.append({
                "id": msg_id,
                "sender": sender,
                "subject": subject,
                "snippet": snippet,
                "date": date
            })
            
        return email_list
    except Exception as e:
        logger.error(f"Error fetching Gmail messages for user {phone_number}: {e}")
        return []

def create_gmail_draft(phone_number: str, to_email: str, subject: str, body: str) -> bool:
    """Creates an email draft in the user's Gmail account."""
    service = get_gmail_service(phone_number)
    if not service:
        return False

    try:
        # Build MIME Message
        message = MIMEText(body)
        message["to"] = to_email
        message["subject"] = subject
        
        # Encode to Base64 Urlsafe
        raw_msg = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        draft_body = {"message": {"raw": raw_msg}}
        
        service.users().drafts().create(userId="me", body=draft_body).execute()
        return True
    except Exception as e:
        logger.error(f"Error creating Gmail draft for user {phone_number}: {e}")
        return False
