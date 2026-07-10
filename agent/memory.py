import logging
import re
import os

logger = logging.getLogger(__name__)

class UserSessionMemory:
    def __init__(self, phone_number: str):
        self.phone_number = phone_number
        self.last_email_list = []          # List of emails retrieved/searched last time
        self.last_selected_email = None     # Dict of the currently/last selected email
        self.last_sender = None             # Name/From of the last sender
        self.last_sender_email = None       # Email address of the last sender
        self.last_thread_id = None          # Thread ID of the last email
        self.last_message_id = None         # Message ID of the last email
        self.last_subject = None            # Subject of the last email
        self.last_calendar_event = None     # Dict of last calendar event
        self.last_attachment = []           # List of dicts: {"filename": str, "path": str, "mime_type": str}
        self.last_action = None             # Name of last action executed
        self.last_search_query = None       # Last search query string
        self.last_contact = None            # Last contact details (email or name)

    def to_dict(self):
        return {
            "last_email_list": self.last_email_list,
            "last_selected_email": self.last_selected_email,
            "last_sender": self.last_sender,
            "last_sender_email": self.last_sender_email,
            "last_thread_id": self.last_thread_id,
            "last_message_id": self.last_message_id,
            "last_subject": self.last_subject,
            "last_calendar_event": self.last_calendar_event,
            "last_attachment": self.last_attachment,
            "last_action": self.last_action,
            "last_search_query": self.last_search_query,
            "last_contact": self.last_contact,
        }

    def update_email_context(self, email_dict: dict):
        """Helper to update all email-related session fields from a single email."""
        if not email_dict:
            return
        self.last_selected_email = email_dict
        self.last_message_id = email_dict.get("id")
        self.last_thread_id = email_dict.get("threadId") or email_dict.get("thread_id") or email_dict.get("id")
        self.last_subject = email_dict.get("subject")
        
        sender = email_dict.get("sender") or email_dict.get("from")
        if sender:
            self.last_sender = sender
            # Extract email from format "Name <email@address.com>"
            match = re.search(r'<([^>]+)>', sender)
            if match:
                self.last_sender_email = match.group(1)
            else:
                self.last_sender_email = email_dict.get("sender_email") or email_dict.get("from_email") or sender
            self.last_contact = self.last_sender_email

    def clear_attachments(self):
        """Deletes all temporary files in last_attachment and clears the list."""
        for att in self.last_attachment:
            path = att.get("path")
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    logger.info(f"Deleted temporary attachment file: {path}")
                except Exception as e:
                    logger.error(f"Error deleting temporary file {path}: {e}")
        self.last_attachment = []

# Global in-memory registry mapping phone_number to UserSessionMemory
_memories = {}

def get_session_memory(phone_number: str) -> UserSessionMemory:
    if phone_number not in _memories:
        _memories[phone_number] = UserSessionMemory(phone_number)
    return _memories[phone_number]
