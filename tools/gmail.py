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




import os
from email.mime.base import MIMEBase
from email import encoders

def send_gmail_email(phone_number: str, to_email: str, subject: str, body: str, attachments: list = None) -> bool:
    """Sends an email immediately, optionally including local file attachments."""
    service = get_gmail_service(phone_number)
    if not service:
        return False

    try:
        if attachments:
            message = MIMEMultipart()
            message["to"] = to_email
            message["subject"] = subject
            message.attach(MIMEText(body, "plain"))
            
            for att in attachments:
                path = att.get("path")
                filename = att.get("filename")
                mime_type = att.get("mime_type", "application/octet-stream")
                
                if path and os.path.exists(path):
                    with open(path, "rb") as f:
                        part_data = f.read()
                    
                    mime_part = MIMEBase(*mime_type.split("/"))
                    mime_part.set_payload(part_data)
                    encoders.encode_base64(mime_part)
                    mime_part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={filename}"
                    )
                    message.attach(mime_part)
        else:
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


from email.mime.multipart import MIMEMultipart

def reply_gmail_email(phone_number: str, reply_body: str, message_id: str = None, email_index: int = None, attachments: list = None) -> bool:
    """Replies to a specific email in the same thread using proper In-Reply-To and References headers, supporting attachments."""
    service = get_gmail_service(phone_number)
    if not service:
        return False

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
                logger.error(f"Email at index {email_index} not found for replying.")
                return False

        if not target_id:
            logger.error("Must provide either message_id or email_index to reply.")
            return False

        orig_msg = service.users().messages().get(
            userId="me", id=target_id, format="full"
        ).execute()

        thread_id = orig_msg.get("threadId")
        payload = orig_msg.get("payload", {})
        headers = payload.get("headers", [])

        orig_message_id = None
        orig_subject = ""
        orig_from = ""
        orig_references = ""

        for header in headers:
            name = header["name"].lower()
            if name == "message-id":
                orig_message_id = header["value"]
            elif name == "subject":
                orig_subject = header["value"]
            elif name == "from":
                orig_from = header["value"]
            elif name == "references":
                orig_references = header["value"]

        if orig_subject and not orig_subject.lower().startswith("re:"):
            subject = "Re: " + orig_subject
        else:
            subject = orig_subject

        to_email = orig_from

        message = MIMEMultipart()
        message["to"] = to_email
        message["subject"] = subject

        if orig_message_id:
            message["In-Reply-To"] = orig_message_id
            if orig_references:
                message["References"] = f"{orig_references} {orig_message_id}"
            else:
                message["References"] = orig_message_id

        message.attach(MIMEText(reply_body, "plain"))

        # Attach local files if any
        if attachments:
            for att in attachments:
                path = att.get("path")
                filename = att.get("filename")
                mime_type = att.get("mime_type", "application/octet-stream")

                if path and os.path.exists(path):
                    with open(path, "rb") as f:
                        part_data = f.read()

                    mime_part = MIMEBase(*mime_type.split("/"))
                    mime_part.set_payload(part_data)
                    encoders.encode_base64(mime_part)
                    mime_part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={filename}"
                    )
                    message.attach(mime_part)

        raw_msg = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode("utf-8")

        service.users().messages().send(
            userId="me",
            body={
                "raw": raw_msg,
                "threadId": thread_id
            }
        ).execute()

        return True
    except Exception as e:
        logger.error(f"Error replying to Gmail message: {e}")
        return False


from email.mime.base import MIMEBase
from email import encoders

def forward_gmail_email(phone_number: str, to_email: str, message_id: str = None, email_index: int = None) -> bool:
    """Forwards an email to a recipient, including body text and attachments."""
    service = get_gmail_service(phone_number)
    if not service:
        return False

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
                logger.error(f"Email at index {email_index} not found for forwarding.")
                return False

        if not target_id:
            logger.error("Must provide either message_id or email_index to forward.")
            return False

        orig_msg = service.users().messages().get(
            userId="me", id=target_id, format="full"
        ).execute()

        payload = orig_msg.get("payload", {})
        headers = payload.get("headers", [])

        orig_subject = "No Subject"
        orig_sender = "Unknown Sender"
        orig_date = ""
        orig_to = ""

        for header in headers:
            name = header["name"].lower()
            if name == "subject":
                orig_subject = header["value"]
            elif name == "from":
                orig_sender = header["value"]
            elif name == "date":
                orig_date = header["value"]
            elif name == "to":
                orig_to = header["value"]

        orig_body = parse_message_payload(payload)
        if not orig_body:
            body_data = payload.get("body", {}).get("data", "")
            if body_data:
                orig_body = base64.urlsafe_b64decode(body_data.encode("UTF-8")).decode("utf-8", errors="replace")

        fwd_header = (
            f"\n\n---------- Forwarded message ---------\n"
            f"From: {orig_sender}\n"
            f"Date: {orig_date}\n"
            f"Subject: {orig_subject}\n"
            f"To: {orig_to}\n\n"
        )

        full_body = fwd_header + orig_body

        mime_type = payload.get("mimeType", "")
        if "html" in mime_type or "<body" in full_body or "<div" in full_body:
            full_body = clean_html(full_body)

        message = MIMEMultipart()
        message["to"] = to_email
        message["subject"] = f"Fwd: {orig_subject}"

        message.attach(MIMEText(full_body, "plain"))

        def attach_parts(parts):
            for part in parts:
                filename = part.get("filename")
                part_mime = part.get("mimeType", "application/octet-stream")
                body = part.get("body", {})
                attachment_id = body.get("attachmentId")

                if filename and attachment_id:
                    try:
                        att_res = service.users().messages().attachments().get(
                            userId="me", messageId=target_id, id=attachment_id
                        ).execute()
                        att_data = base64.urlsafe_b64decode(att_res.get("data", "").encode("UTF-8"))

                        mime_part = MIMEBase(*part_mime.split("/"))
                        mime_part.set_payload(att_data)
                        encoders.encode_base64(mime_part)
                        mime_part.add_header(
                            "Content-Disposition",
                            f"attachment; filename={filename}"
                        )
                        message.attach(mime_part)
                        logger.info(f"Attached forwarded file: {filename}")
                    except Exception as ex:
                        logger.error(f"Failed to fetch/attach forwarded attachment {filename}: {ex}")

                nested_parts = part.get("parts")
                if nested_parts:
                    attach_parts(nested_parts)

        if "parts" in payload:
            attach_parts(payload["parts"])

        raw_msg = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode("utf-8")

        service.users().messages().send(
            userId="me",
            body={"raw": raw_msg}
        ).execute()

        return True
    except Exception as e:
        logger.error(f"Error forwarding Gmail message: {e}")
        return False


def mark_gmail_email_as_read(phone_number: str, message_id: str = None, email_index: int = None) -> bool:
    """Marks a specific email as read by removing the UNREAD label."""
    service = get_gmail_service(phone_number)
    if not service:
        return False

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
                logger.error(f"Email at index {email_index} not found for marking as read.")
                return False

        if not target_id:
            logger.error("Must provide either message_id or email_index to mark as read.")
            return False

        service.users().messages().modify(
            userId="me", id=target_id,
            body={"removeLabelIds": ["UNREAD"]}
        ).execute()

        return True
    except Exception as e:
        logger.error(f"Error marking Gmail message as read: {e}")
        return False


def mark_gmail_email_as_unread(phone_number: str, message_id: str = None, email_index: int = None) -> bool:
    """Marks a specific email as unread by adding the UNREAD label."""
    service = get_gmail_service(phone_number)
    if not service:
        return False

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
                logger.error(f"Email at index {email_index} not found for marking as unread.")
                return False

        if not target_id:
            logger.error("Must provide either message_id or email_index to mark as unread.")
            return False

        service.users().messages().modify(
            userId="me", id=target_id,
            body={"addLabelIds": ["UNREAD"]}
        ).execute()

        return True
    except Exception as e:
        logger.error(f"Error marking Gmail message as unread: {e}")
        return False


def star_gmail_email(phone_number: str, message_id: str = None, email_index: int = None, star: bool = True) -> bool:
    """Stars or unstars a specific email by adding or removing the STARRED label."""
    service = get_gmail_service(phone_number)
    if not service:
        return False

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
                logger.error(f"Email at index {email_index} not found for starring.")
                return False

        if not target_id:
            logger.error("Must provide either message_id or email_index to star/unstar.")
            return False

        body = {}
        if star:
            body["addLabelIds"] = ["STARRED"]
        else:
            body["removeLabelIds"] = ["STARRED"]

        service.users().messages().modify(
            userId="me", id=target_id,
            body=body
        ).execute()

        return True
    except Exception as e:
        logger.error(f"Error starring/unstarring Gmail message: {e}")
        return False


def delete_gmail_email(phone_number: str, message_id: str = None, email_index: int = None) -> bool:
    """Moves a specific email to the trash (deletes it)."""
    service = get_gmail_service(phone_number)
    if not service:
        return False

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
                logger.error(f"Email at index {email_index} not found for deletion.")
                return False

        if not target_id:
            logger.error("Must provide either message_id or email_index to delete.")
            return False

        service.users().messages().trash(
            userId="me", id=target_id
        ).execute()

        return True
    except Exception as e:
        logger.error(f"Error trashing/deleting Gmail message: {e}")
        return False


def get_gmail_attachments(phone_number: str, message_id: str = None, email_index: int = None) -> list:
    """Downloads attachments of a specific email, saves them to a static directory, and returns their details."""
    service = get_gmail_service(phone_number)
    if not service:
        return []

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
                logger.error(f"Email at index {email_index} not found for attachments.")
                return []

        if not target_id:
            logger.error("Must provide either message_id or email_index to get attachments.")
            return []

        msg = service.users().messages().get(userId="me", id=target_id, format="full").execute()
        payload = msg.get("payload", {})

        attachments = []
        static_dir = os.path.join(os.getcwd(), "static", "attachments")
        os.makedirs(static_dir, exist_ok=True)

        from config import Config
        base_url = Config.GOOGLE_REDIRECT_URI.replace("/auth/callback", "")

        def download_parts(parts):
            for part in parts:
                filename = part.get("filename")
                body = part.get("body", {})
                attachment_id = body.get("attachmentId")

                if filename and attachment_id:
                    try:
                        att_res = service.users().messages().attachments().get(
                            userId="me", messageId=target_id, id=attachment_id
                        ).execute()
                        att_data = base64.urlsafe_b64decode(att_res.get("data", "").encode("UTF-8"))

                        # Generate a safe file name or prefix to avoid collision
                        safe_filename = f"{target_id}_{filename}"
                        safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in "._-")

                        file_path = os.path.join(static_dir, safe_filename)
                        with open(file_path, "wb") as f:
                            f.write(att_data)

                        attachments.append({
                            "filename": filename,
                            "size_bytes": len(att_data),
                            "media_url": f"{base_url}/static/attachments/{safe_filename}"
                        })
                        logger.info(f"Downloaded attachment: {filename} to {file_path}")
                    except Exception as ex:
                        logger.error(f"Error downloading attachment {filename}: {ex}")

                nested_parts = part.get("parts")
                if nested_parts:
                    download_parts(nested_parts)

        if "parts" in payload:
            download_parts(payload["parts"])

        return attachments
    except Exception as e:
        logger.error(f"Error getting attachments: {e}")
        return []


def get_unread_emails_digest_data(phone_number: str, max_results: int = 5) -> list:
    """Fetches full content of all unread emails for generating a digest."""
    service = get_gmail_service(phone_number)
    if not service:
        return []

    try:
        results = service.users().messages().list(
            userId="me", q="is:unread label:INBOX", maxResults=max_results
        ).execute()

        messages = results.get("messages", [])
        digest_data = []

        for msg in messages:
            msg_id = msg["id"]
            msg_details = service.users().messages().get(
                userId="me", id=msg_id, format="full"
            ).execute()

            payload = msg_details.get("payload", {})
            headers = payload.get("headers", [])

            subject = "No Subject"
            sender = "Unknown Sender"
            date = ""

            for header in headers:
                name = header["name"].lower()
                if name == "subject":
                    subject = header["value"]
                elif name == "from":
                    sender = header["value"]
                elif name == "date":
                    date = header["value"]

            # Try to get the body
            body = parse_message_payload(payload)
            if not body:
                body_data = payload.get("body", {}).get("data", "")
                if body_data:
                    body = base64.urlsafe_b64decode(body_data.encode("UTF-8")).decode("utf-8", errors="replace")

            if body:
                body = clean_html(body)
            else:
                body = msg_details.get("snippet", "")

            digest_data.append({
                "sender": sender,
                "subject": subject,
                "date": date,
                "body": body[:500]  # First 500 characters of clean body is plenty for a digest summary
            })

        return digest_data
    except Exception as e:
        logger.error(f"Error fetching email digest data: {e}")
        return []


class GmailOperation:
    """Base interface for all Gmail operations to follow Open-Closed Principle."""
    def execute(self, service, phone_number: str, **kwargs):
        raise NotImplementedError

GMAIL_OPERATIONS_REGISTRY = {}

def register_gmail_operation(name: str, op_class):
    GMAIL_OPERATIONS_REGISTRY[name] = op_class

def execute_gmail_operation(phone_number: str, operation_name: str, **kwargs) -> bool:
    """Executes a registered Gmail operation by name."""
    service = get_gmail_service(phone_number)
    if not service:
        logger.error(f"Gmail service not found for {phone_number}")
        return False
    op_class = GMAIL_OPERATIONS_REGISTRY.get(operation_name)
    if not op_class:
        logger.error(f"Gmail operation '{operation_name}' is not registered.")
        return False
    try:
        return op_class().execute(service, phone_number, **kwargs)
    except Exception as e:
        logger.error(f"Error executing Gmail operation '{operation_name}': {e}")
        return False


# --- Extensible Operations Implementations ---

class ArchiveGmailEmail(GmailOperation):
    def execute(self, service, phone_number: str, **kwargs):
        message_id = kwargs.get("message_id")
        if not message_id:
            return False
        # Archiving in Gmail means removing the INBOX label
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["INBOX"]}
        ).execute()
        return True

class LabelGmailEmail(GmailOperation):
    def execute(self, service, phone_number: str, **kwargs):
        message_id = kwargs.get("message_id")
        label_id = kwargs.get("label_id")
        if not message_id or not label_id:
            return False
        # Add label
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": [label_id]}
        ).execute()
        return True

# Register the operations
register_gmail_operation("archive", ArchiveGmailEmail)
register_gmail_operation("label", LabelGmailEmail)


def generate_daily_email_digest_data(phone_number: str) -> dict:
    """Fetches categorized email counts and details to construct a daily email digest."""
    service = get_gmail_service(phone_number)
    if not service:
        return {}

    def count_query(q):
        try:
            res = service.users().messages().list(userId="me", q=q, maxResults=50).execute()
            return len(res.get("messages", []))
        except Exception:
            return 0

    def get_emails_query(q, max_r=3):
        try:
            res = service.users().messages().list(userId="me", q=q, maxResults=max_r).execute()
            messages = res.get("messages", [])
            items = []
            for msg in messages:
                details = service.users().messages().get(userId="me", id=msg["id"], format="metadata").execute()
                headers = details.get("payload", {}).get("headers", [])
                subject = "No Subject"
                sender = "Unknown"
                for h in headers:
                    if h["name"].lower() == "subject":
                        subject = h["value"]
                    elif h["name"].lower() == "from":
                        sender = h["value"]
                items.append({"sender": sender, "subject": subject})
            return items
        except Exception:
            return []

    try:
        unread_count = count_query("is:unread label:INBOX")
        important_emails = get_emails_query("is:unread label:IMPORTANT")
        meeting_invites = get_emails_query("invite OR invitation OR calendar")
        promotions_count = count_query("category:promotions")
        spam_count = count_query("label:spam")
        priority_emails = get_emails_query("is:starred")

        return {
            "unread_count": unread_count,
            "important": important_emails,
            "meetings": meeting_invites,
            "promotions_count": promotions_count,
            "spam_count": spam_count,
            "priority": priority_emails
        }
    except Exception as e:
        logger.error(f"Error fetching daily digest data: {e}")
        return {}
