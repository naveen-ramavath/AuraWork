import base64
import logging
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from services.google_oauth import get_user_credentials

logger = logging.getLogger(__name__)

def get_gmail_service(phone_number):
    print("Creating Gmail service for:", phone_number)

    creds = get_user_credentials(phone_number)

    print("Credentials returned:", creds)

    if not creds:
        print("NO CREDS")
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
        message = MIMEText(body)
        message["to"] = to_email
        message["subject"] = subject

        raw_msg = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode("utf-8")

        draft_body = {
            "message": {
                "raw": raw_msg
            }
        }

        service.users().drafts().create(
            userId="me",
            body=draft_body
        ).execute()

        return True

    except Exception as e:
        logger.error(f"Error creating Gmail draft for user {phone_number}: {e}")
        return False




def send_gmail_email(phone_number: str, to_email: str, subject: str, body: str) -> bool:
    """Sends an email immediately."""
    service = get_gmail_service(phone_number)
    if not service:
        return False

    try:
        message = MIMEText(body)
        message["to"] = to_email
        message["subject"] = subject

        raw_msg = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode("utf-8")

        service.users().messages().send(
            userId="me",
            body={"raw": raw_msg}
        ).execute()

        return True

    except Exception as e:
        logger.error(f"Error sending Gmail for user {phone_number}: {e}")
        return False


import re

def clean_html(html_content: str) -> str:
    """Strips HTML tags, styles, and scripts to return clean readable text."""
    # Remove script and style elements
    html_content = re.sub(r'<(script|style)\b[^>]*>([\s\S]*?)<\/\1>', '', html_content, flags=re.IGNORECASE)
    # Remove all HTML tags
    clean_text = re.sub(r'<[^>]+>', '', html_content)
    # Replace multiple spaces/newlines with single ones
    clean_text = re.sub(r'\n\s*\n', '\n', clean_text)
    clean_text = re.sub(r' +', ' ', clean_text)
    return clean_text.strip()


def parse_message_payload(payload) -> str:
    """Recursively decodes and extracts text from Gmail message parts."""
    body = ""
    mime_type = payload.get("mimeType", "")
    parts = payload.get("parts", [])

    if mime_type.startswith("text/plain"):
        data = payload.get("body", {}).get("data", "")
        if data:
            body += base64.urlsafe_b64decode(data.encode("UTF-8")).decode("utf-8", errors="replace")
    elif mime_type.startswith("text/html"):
        data = payload.get("body", {}).get("data", "")
        if data:
            html_text = base64.urlsafe_b64decode(data.encode("UTF-8")).decode("utf-8", errors="replace")
            body += html_text
    elif parts:
        plain_parts = []
        html_parts = []
        other_parts = []
        for part in parts:
            p_mime = part.get("mimeType", "")
            if p_mime.startswith("text/plain"):
                plain_parts.append(part)
            elif p_mime.startswith("text/html"):
                html_parts.append(part)
            else:
                other_parts.append(part)

        if plain_parts:
            for part in plain_parts:
                body += parse_message_payload(part)
        elif html_parts:
            for part in html_parts:
                body += parse_message_payload(part)

        for part in other_parts:
            if part.get("parts"):
                body += parse_message_payload(part)
    return body


def read_gmail_email(phone_number: str, message_id: str = None, email_index: int = None) -> dict:
    """Retrieves and reads the full content of a Gmail email."""
    service = get_gmail_service(phone_number)
    if not service:
        return {"error": "Gmail service not initialized."}

    try:
        target_id = message_id
        if not target_id and email_index is not None:
            results = service.users().messages().list(
                userId="me", maxResults=email_index
            ).execute()
            messages = results.get("messages", [])
            if len(messages) >= email_index:
                target_id = messages[email_index - 1]["id"]
            else:
                return {"error": f"Email at index {email_index} not found."}

        if not target_id:
            return {"error": "Must provide either message_id or email_index."}

        msg = service.users().messages().get(userId="me", id=target_id, format="full").execute()

        payload = msg.get("payload", {})
        headers = payload.get("headers", [])
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

        body = parse_message_payload(payload)

        if not body:
            body_data = payload.get("body", {}).get("data", "")
            if body_data:
                body = base64.urlsafe_b64decode(body_data.encode("UTF-8")).decode("utf-8", errors="replace")

        mime_type = payload.get("mimeType", "")
        if "html" in mime_type or "<body" in body or "<div" in body:
            body = clean_html(body)

        return {
            "id": target_id,
            "sender": sender,
            "subject": subject,
            "date": date,
            "body": body.strip()
        }
    except Exception as e:
        logger.error(f"Error reading Gmail message: {e}")
        return {"error": str(e)}


def search_gmail_emails(phone_number: str, query: str, max_results: int = 5) -> list:
    """Searches the user's Gmail using Gmail Query Syntax and returns metadata list."""
    service = get_gmail_service(phone_number)
    if not service:
        return []

    try:
        results = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()

        messages = results.get("messages", [])
        email_list = []

        for msg in messages:
            msg_id = msg["id"]
            thread_id = msg["threadId"]

            msg_details = service.users().messages().get(
                userId="me", id=msg_id, format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()

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
                "threadId": thread_id,
                "sender": sender,
                "subject": subject,
                "snippet": snippet,
                "date": date
            })

        return email_list
    except Exception as e:
        logger.error(f"Error searching Gmail for user {phone_number} with query '{query}': {e}")
        return []
