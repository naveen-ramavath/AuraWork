import json
import logging
import datetime
import google.generativeai as genai
from ai.router import AIRouter
from google.generativeai.types import GenerateContentResponse
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from ai.router import AIRouter
from config import Config
import tools.slack as slack_tool
import tools.jira as jira_tool
import tools.gmail as gmail_tool
import tools.calendar as calendar_tool
from agent.memory import get_session_memory

logger = logging.getLogger(__name__)

class SyncCopilotAgent:
    def __init__(self, phone_number: str, db: Session):
        self.phone_number = phone_number
        self.db = db
        # Configure Gemini API
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.ai_router = AIRouter()

    # --- Tool Definitions ---

    def get_current_time(self) -> str:
        """Retrieves the current date and time. Use this before scheduling any calendar events or checking emails.

        Returns:
            str: The current timestamp in ISO format.
        """
        now = datetime.datetime.now().isoformat()
        logger.info(f"Tool Executed: get_current_time -> {now}")
        return json.dumps({"current_time": now, "timezone": "Asia/Kolkata"})

    def fetch_calendar_schedule(self, limit: int = 5) -> str:
        """Fetches upcoming events from the user's Google Calendar.

        Args:
            limit (int): Maximum number of events to fetch. Defaults to 5.

        Returns:
            str: JSON string containing list of calendar events.
        """
        logger.info(f"Tool Executed: fetch_calendar_schedule for {self.phone_number}")
        events = calendar_tool.fetch_calendar_events(self.phone_number, limit)
        if not events:
            return json.dumps({"error": "No calendar events found or user not authenticated. Tell the user to run /login."})
        return json.dumps(events)

    def create_meeting(self, summary: str, start_iso: str, end_iso: str, description: str = "", location: str = "") -> str:
        """Creates a new calendar event (meeting) in the user's primary calendar and returns details.

        Args:
            summary (str): The title of the meeting.
            start_iso (str): Start time in ISO format (e.g., '2026-06-28T09:00:00+05:30').
            end_iso (str): End time in ISO format.
            description (str): Optional meeting description/agenda.
            location (str): Optional meeting location.

        Returns:
            str: JSON string containing created event details and Google Meet link.
        """
        logger.info(f"Tool Executed: create_meeting '{summary}' from {start_iso} to {end_iso}")
        event = calendar_tool.create_calendar_event(
            self.phone_number, summary, start_iso, end_iso, description, location
        )
        if not event:
            return json.dumps({"error": "Failed to create meeting. Ensure Google account is authenticated."})
        return json.dumps(event)

    def _resolve_context(self, message_id: str = None, email_index: int = None) -> dict:
        """Resolves target email context using the session memory or direct input."""
        memory = get_session_memory(self.phone_number)
        
        # 1. Resolve by index if provided
        if email_index is not None:
            try:
                idx = int(email_index) - 1
                if 0 <= idx < len(memory.last_email_list):
                    selected = memory.last_email_list[idx]
                    memory.update_email_context(selected)
                    return selected
            except (ValueError, TypeError):
                pass
                
        # 2. Resolve by message_id if provided
        if message_id:
            for item in memory.last_email_list:
                if item.get("id") == message_id:
                    memory.update_email_context(item)
                    return item
            return {"id": message_id}
            
        # 3. Fallback to last selected / active email
        if memory.last_selected_email:
            return memory.last_selected_email
            
        if memory.last_message_id:
            return {
                "id": memory.last_message_id,
                "threadId": memory.last_thread_id,
                "subject": memory.last_subject,
                "sender": memory.last_sender,
                "sender_email": memory.last_sender_email
            }
            
        return None

    def _resolve_contact_email(self, name_or_email: str) -> str:
        """Resolves recipient name to email using session memory context if possible."""
        if not name_or_email:
            return ""
        if "@" in name_or_email:
            return name_or_email
            
        memory = get_session_memory(self.phone_number)
        
        # Check if the name matches the last sender
        if memory.last_sender and name_or_email.lower() in memory.last_sender.lower():
            if memory.last_sender_email:
                return memory.last_sender_email
                
        # Check if it matches last contact
        if memory.last_contact and name_or_email.lower() in memory.last_contact.lower():
            if "@" in memory.last_contact:
                return memory.last_contact
                
        # Return name as is if we can't resolve
        return name_or_email

    def fetch_unread_emails(self, limit: int = 5) -> str:
        """Retrieves unread emails from the user's Gmail inbox.

        Args:
            limit (int): Maximum number of emails to retrieve. Defaults to 5.

        Returns:
            str: Conversational formatted text with numbered emails.
        """
        logger.info(f"Tool Executed: fetch_unread_emails for {self.phone_number}")
        emails = gmail_tool.fetch_unread_emails(self.phone_number, limit)
        if not emails:
            return "No unread emails found or user not authenticated. Tell the user to run /login."
            
        # Save to memory
        memory = get_session_memory(self.phone_number)
        memory.last_email_list = emails
        memory.last_action = "fetch_unread_emails"
        
        # Format for output (Numbered list)
        lines = []
        for idx, em in enumerate(emails, 1):
            lines.append(f"{idx}.\nSender: {em.get('sender')}\nSubject: {em.get('subject')}\nDate: {em.get('date')}\nSnippet: {em.get('snippet')}\n")
        return "\n".join(lines)

    def read_email(self, message_id: str = None, email_index: int = None) -> str:
        """Retrieves and reads the full text of a specific Gmail email.

        Args:
            message_id (str): The unique ID of the email. Optional if email_index is given.
            email_index (int): The 1-based index of the email in the inbox list. Optional if message_id is given.

        Returns:
            str: JSON string containing details of the email or error.
        """
        logger.info(f"Tool Executed: read_email for {self.phone_number} (id: {message_id}, index: {email_index})")
        ctx = self._resolve_context(message_id, email_index)
        if not ctx or not ctx.get("id"):
            return "Error: Could not resolve which email to read from session memory. Please specify which email you want to read."
            
        email_data = gmail_tool.read_gmail_email(self.phone_number, ctx["id"])
        if not email_data:
            return "Failed to read email."
            
        # Update memory context with full parsed details
        memory = get_session_memory(self.phone_number)
        full_detail = {**ctx, **email_data}
        memory.update_email_context(full_detail)
        memory.last_action = "read_email"
        
        return json.dumps(full_detail)

    def search_emails(self, query: str, limit: int = 5) -> str:
        """Searches the user's Gmail emails using standard Gmail search syntax (e.g. from:Microsoft, subject:internship, is:unread).

        Args:
            query (str): The search query parameter.
            limit (int): Maximum number of search results to return. Defaults to 5.

        Returns:
            str: Conversational formatted text with numbered search results.
        """
        logger.info(f"Tool Executed: search_emails for {self.phone_number} (query: {query}, limit: {limit})")
        emails = gmail_tool.search_gmail_emails(self.phone_number, query, limit)
        if not emails:
            return f"No emails found matching query '{query}'."
            
        # Save to memory
        memory = get_session_memory(self.phone_number)
        memory.last_email_list = emails
        memory.last_search_query = query
        memory.last_action = "search_emails"
        
        # Format for output (Numbered list)
        lines = []
        for idx, em in enumerate(emails, 1):
            lines.append(f"{idx}.\nSender: {em.get('sender')}\nSubject: {em.get('subject')}\nDate: {em.get('date')}\nSnippet: {em.get('snippet')}\n")
        return "\n".join(lines)

    def reply_to_email(self, reply_body: str, message_id: str = None, email_index: int = None) -> str:
        """Replies to a specific email inside the same email thread using threadId and messageId references.

        Args:
            reply_body (str): The body text of the reply.
            message_id (str): The unique ID of the email being replied to. Optional if email_index is given.
            email_index (int): The 1-based index of the email in the inbox list. Optional if message_id is given.

        Returns:
            str: JSON string indicating success or error.
        """
        logger.info(f"Tool Executed: reply_to_email for {self.phone_number} (id: {message_id}, index: {email_index})")
        ctx = self._resolve_context(message_id, email_index)
        if not ctx or not ctx.get("id"):
            return "Error: Could not resolve email context to reply. Please specify which email to reply to."
            
        memory = get_session_memory(self.phone_number)
        attachments = memory.last_attachment
        
        success = gmail_tool.reply_gmail_email(self.phone_number, reply_body, ctx["id"], attachments=attachments)
        if success:
            memory.clear_attachments() # Auto delete temporary files
            memory.last_action = "reply_to_email"
            return json.dumps({"status": "success", "message": "Reply sent successfully."})
        return json.dumps({"status": "error", "message": "Failed to send reply."})

    def forward_email(self, to_email: str, message_id: str = None, email_index: int = None) -> str:
        """Forwards an email to a specified recipient address, preserving headers and forwarding attachments.

        Args:
            to_email (str): The email address to forward the email to.
            message_id (str): The unique ID of the email being forwarded. Optional if email_index is given.
            email_index (int): The 1-based index of the email in the inbox list. Optional if message_id is given.

        Returns:
            str: JSON string indicating success or error.
        """
        logger.info(f"Tool Executed: forward_email for {self.phone_number} to {to_email} (id: {message_id}, index: {email_index})")
        ctx = self._resolve_context(message_id, email_index)
        if not ctx or not ctx.get("id"):
            return "Error: Could not resolve email context to forward. Please specify which email to forward."
            
        resolved_to = self._resolve_contact_email(to_email)
        
        success = gmail_tool.forward_gmail_email(self.phone_number, resolved_to, ctx["id"])
        if success:
            memory = get_session_memory(self.phone_number)
            memory.last_action = "forward_email"
            return json.dumps({"status": "success", "message": f"Email forwarded successfully to {resolved_to}."})
        return json.dumps({"status": "error", "message": "Failed to forward email."})

    def mark_as_read(self, message_id: str = None, email_index: int = None) -> str:
        """Marks a specific email as read by removing the unread label.

        Args:
            message_id (str): The unique ID of the email. Optional if email_index is given.
            email_index (int): The 1-based index of the email in the inbox list. Optional if message_id is given.

        Returns:
            str: JSON string indicating success or error.
        """
        logger.info(f"Tool Executed: mark_as_read for {self.phone_number} (id: {message_id}, index: {email_index})")
        ctx = self._resolve_context(message_id, email_index)
        if not ctx or not ctx.get("id"):
            return "Error: Could not resolve email context to mark as read."
            
        success = gmail_tool.mark_gmail_email_as_read(self.phone_number, ctx["id"])
        if success:
            memory = get_session_memory(self.phone_number)
            memory.last_action = "mark_as_read"
            return json.dumps({"status": "success", "message": "Email marked as read."})
        return json.dumps({"status": "error", "message": "Failed to mark email as read."})

    def mark_as_unread(self, message_id: str = None, email_index: int = None) -> str:
        """Marks a specific email as unread by adding the unread label.

        Args:
            message_id (str): The unique ID of the email. Optional if email_index is given.
            email_index (int): The 1-based index of the email in the inbox list. Optional if message_id is given.

        Returns:
            str: JSON string indicating success or error.
        """
        logger.info(f"Tool Executed: mark_as_unread for {self.phone_number} (id: {message_id}, index: {email_index})")
        ctx = self._resolve_context(message_id, email_index)
        if not ctx or not ctx.get("id"):
            return "Error: Could not resolve email context to mark as unread."
            
        success = gmail_tool.mark_gmail_email_as_unread(self.phone_number, ctx["id"])
        if success:
            memory = get_session_memory(self.phone_number)
            memory.last_action = "mark_as_unread"
            return json.dumps({"status": "success", "message": "Email marked as unread."})
        return json.dumps({"status": "error", "message": "Failed to mark email as unread."})

    def star_email(self, message_id: str = None, email_index: int = None, star: bool = True) -> str:
        """Stars or unstars a specific email.

        Args:
            message_id (str): The unique ID of the email. Optional if email_index is given.
            email_index (int): The 1-based index of the email in the inbox list. Optional if message_id is given.
            star (bool): True to star, False to unstar. Defaults to True.

        Returns:
            str: JSON string indicating success or error.
        """
        action = "starred" if star else "unstarred"
        logger.info(f"Tool Executed: star_email for {self.phone_number} (id: {message_id}, index: {email_index}, action: {action})")
        ctx = self._resolve_context(message_id, email_index)
        if not ctx or not ctx.get("id"):
            return f"Error: Could not resolve email context to {action[:-2]}."
            
        success = gmail_tool.star_gmail_email(self.phone_number, ctx["id"], None, star)
        if success:
            memory = get_session_memory(self.phone_number)
            memory.last_action = f"star_email_{action}"
            return json.dumps({"status": "success", "message": f"Email {action} successfully."})
        return json.dumps({"status": "error", "message": f"Failed to {action[:-2]} email."})

    def delete_email(self, message_id: str = None, email_index: int = None) -> str:
        """Moves a specific email to the trash (deletes it).

        Args:
            message_id (str): The unique ID of the email. Optional if email_index is given.
            email_index (int): The 1-based index of the email in the inbox list. Optional if message_id is given.

        Returns:
            str: JSON string indicating success or error.
        """
        logger.info(f"Tool Executed: delete_email for {self.phone_number} (id: {message_id}, index: {email_index})")
        ctx = self._resolve_context(message_id, email_index)
        if not ctx or not ctx.get("id"):
            return "Error: Could not resolve email context to delete."
            
        success = gmail_tool.delete_gmail_email(self.phone_number, ctx["id"])
        if success:
            memory = get_session_memory(self.phone_number)
            memory.last_action = "delete_email"
            return json.dumps({"status": "success", "message": "Email moved to trash successfully."})
        return json.dumps({"status": "error", "message": "Failed to delete email."})

    def get_attachments(self, message_id: str = None, email_index: int = None) -> str:
        """Downloads file attachments of a specific email to a temporary directory and returns metadata.

        Args:
            message_id (str): The unique ID of the email. Optional if email_index is given.
            email_index (int): The 1-based index of the email in the inbox list. Optional if message_id is given.

        Returns:
            str: JSON string containing a list of attachments details (filename, size_bytes, media_url).
        """
        logger.info(f"Tool Executed: get_attachments for {self.phone_number} (id: {message_id}, index: {email_index})")
        ctx = self._resolve_context(message_id, email_index)
        if not ctx or not ctx.get("id"):
            return "Error: Could not resolve email context to fetch attachments."
            
        attachments = gmail_tool.get_gmail_attachments(self.phone_number, ctx["id"])
        return json.dumps(attachments)

    def generate_inbox_digest(self, max_results: int = 5) -> str:
        """Fetches all unread emails, reads their contents, and generates a structured digest of unread emails.

        Args:
            max_results (int): The maximum number of unread emails to summarize. Defaults to 5.

        Returns:
            str: JSON string containing list of unread email details (sender, subject, date, body snippet) for digest generation.
        """
        logger.info(f"Tool Executed: generate_inbox_digest for {self.phone_number} (limit: {max_results})")
        digest_data = gmail_tool.get_unread_emails_digest_data(self.phone_number, max_results)
        return json.dumps(digest_data)

    def get_daily_email_digest(self) -> str:
        """Fetches and generates a beautiful daily email digest with categories like Today's Inbox, Meeting Invites, Promotions, and Spam."""
        logger.info(f"Tool Executed: get_daily_email_digest for {self.phone_number}")
        data = gmail_tool.generate_daily_email_digest_data(self.phone_number)
        if not data:
            return "Failed to fetch email digest."

        # Format beautiful WhatsApp output
        lines = [
            "*Good Morning!* ☀️",
            "",
            "Here is your *Today's Inbox* email digest:",
            f"📨 *Unread Count*: {data.get('unread_count', 0)} unread emails",
            ""
        ]

        priority = data.get("priority", [])
        if priority:
            lines.append("⭐ *Priority / Starred Emails*:")
            for item in priority:
                lines.append(f"- From: {item['sender']} | Subject: {item['subject']}")
            lines.append("")

        important = data.get("important", [])
        if important:
            lines.append("🔥 *Important Emails*:")
            for item in important:
                lines.append(f"- From: {item['sender']} | Subject: {item['subject']}")
            lines.append("")

        meetings = data.get("meetings", [])
        if meetings:
            lines.append("📅 *Meeting Invites*:")
            for item in meetings:
                lines.append(f"- From: {item['sender']} | Subject: {item['subject']}")
            lines.append("")

        lines.append(f"🏷️ *Promotions*: {data.get('promotions_count', 0)} unread promotions")
        lines.append(f"🛡️ *Spam*: {data.get('spam_count', 0)} spam messages")

        return "\n".join(lines)

    def send_email(self, to_email: str, subject: str, body: str) -> str:
        """Sends an email immediately, optionally including local file attachments."""
        logger.info(f"Tool Executed: send_email to {to_email}")
        resolved_to = self._resolve_contact_email(to_email)

        memory = get_session_memory(self.phone_number)
        attachments = memory.last_attachment

        success = gmail_tool.send_gmail_email(
            self.phone_number,
            resolved_to,
            subject,
            body,
            attachments=attachments
        )

        if success:
            memory.clear_attachments()  # Auto delete temporary files
            return json.dumps({
                "status": "success",
                "message": f"Email sent successfully to {resolved_to}."
            })

        return json.dumps({
            "status": "error",
            "message": "Failed to send email."
        })

    def draft_email(self, to_email: str, subject: str, body: str) -> str:
        """Creates an email draft.

        Args:
            to_email (str): Recipient email address.
            subject (str): Email subject.
            body (str): Email body text.

        Returns:
            str: JSON string indicating success or error.
        """
        logger.info(f"Tool Executed: draft_email to {to_email}")
        resolved_to = self._resolve_contact_email(to_email)

        success = gmail_tool.create_gmail_draft(
            self.phone_number,
            resolved_to,
            subject,
            body
        )

        if success:
            return json.dumps({
                "status": "success",
                "message": f"Draft created successfully for {resolved_to}."
            })

        return json.dumps({
            "status": "error",
            "message": "Failed to create draft."
        })

    def post_slack_message(self, channel: str, text: str) -> str:
        """Posts a message to a specific Slack channel or team DM.

        Args:
            channel (str): The name or ID of the channel (e.g. 'general' or 'dev-updates').
            text (str): The content of the message.

        Returns:
            str: Status message indicating success or failure.
        """
        logger.info(f"Tool Executed: post_slack_message to #{channel}")
        # Clean channel symbol if provided
        channel_cleaned = channel.lstrip('#')
        success = slack_tool.post_message_to_slack(channel_cleaned, text)
        if success:
            return json.dumps({"status": "success", "message": f"Message posted to Slack #{channel_cleaned}."})
        return json.dumps({"status": "error", "message": "Failed to post message to Slack. Ensure Slack token is configured."})

    def fetch_slack_mentions(self) -> str:
        """Retrieves recent unread notifications and mentions for the user on Slack.

        Returns:
            str: JSON list of recent Slack mentions.
        """
        logger.info(f"Tool Executed: fetch_slack_mentions")
        mentions = slack_tool.get_slack_unread_mentions()
        if not mentions:
            return json.dumps({"message": "No unread Slack mentions found."})
        return json.dumps(mentions)

    def fetch_assigned_jira_tickets(self, limit: int = 5) -> str:
        """Fetches active, open Jira issues assigned to the user.

        Args:
            limit (int): Max number of tickets to retrieve. Defaults to 5.

        Returns:
            str: JSON list of issues containing key, summary, status, and priority.
        """
        logger.info(f"Tool Executed: fetch_assigned_jira_tickets")
        issues = jira_tool.get_assigned_jira_issues(limit)
        if not issues:
            return json.dumps({"message": "No open assigned Jira tickets found or Jira details are not configured."})
        return json.dumps(issues)

    def log_work_hours(self, issue_key: str, time_spent: str, comment: str = "") -> str:
        """Logs time spent working on a specific Jira ticket.

        Args:
            issue_key (str): The Jira issue identifier (e.g., 'PROJ-101').
            time_spent (str): The duration to log (e.g., '1h 30m', '45m').
            comment (str): Optional description of the work done.

        Returns:
            str: Status message indicating success or failure.
        """
        logger.info(f"Tool Executed: log_work_hours on {issue_key} for {time_spent}")
        success = jira_tool.log_jira_work(issue_key, time_spent, comment)
        if success:
            return json.dumps({"status": "success", "message": f"Successfully logged {time_spent} on {issue_key}."})
        return json.dumps({"status": "error", "message": f"Failed to log work hours on {issue_key}."})

    def create_jira_issue_ticket(self, project_key: str, summary: str, description: str, issue_type: str = "Task") -> str:
        """Creates a new Jira issue ticket for tracking work.

        Args:
            project_key (str): Project identifier (e.g. 'PROJ').
            summary (str): Short summary of the task.
            description (str): Detailed description of the work.
            issue_type (str): Type of ticket (e.g., 'Task', 'Bug', 'Story'). Defaults to 'Task'.

        Returns:
            str: JSON string containing the created ticket key or error.
        """
        logger.info(f"Tool Executed: create_jira_issue_ticket '{summary}'")
        key = jira_tool.create_jira_ticket(project_key, summary, description, issue_type)
        if key:
            return json.dumps({"status": "success", "issue_key": key})
        return json.dumps({"status": "error", "message": "Failed to create Jira issue."})

    # --- Agent Execution Logic ---

    def run(self, user_message: str) -> str:
        """Main execution flow using a manual function-calling loop with Gemini."""
        if not Config.GEMINI_API_KEY:
            return "⚠️ Gemini API key is missing. Please check your config."

        memory = get_session_memory(self.phone_number)
        
        # Build contextual instructions based on session memory
        state_context = (
            f"Active Session Memory Context:\n"
            f"- Last Selected Email ID: {memory.last_message_id or 'None'}\n"
            f"- Last Thread ID: {memory.last_thread_id or 'None'}\n"
            f"- Last Subject: {memory.last_subject or 'None'}\n"
            f"- Last Sender Name: {memory.last_sender or 'None'}\n"
            f"- Last Sender Email: {memory.last_sender_email or 'None'}\n"
            f"- Last Search Query: {memory.last_search_query or 'None'}\n"
            f"- Last Action: {memory.last_action or 'None'}\n"
            f"- Pending Attachments Uploaded by WhatsApp: {[att.get('filename') for att in memory.last_attachment]}\n"
            f"- Number of listed emails in last view: {len(memory.last_email_list)}\n"
        )

        system_instruction = (
            "You are SyncCopilot AI, a workplace assistant that helps employees manage tasks.\n"
            "You run inside WhatsApp. Help the user complete real-world tasks using your tools.\n"
            "Your available tools represent operations on Slack, Jira, Gmail, and Google Calendar.\n\n"
            "Rules:\n"
            "1. Before scheduling anything, checking schedule, or doing date comparisons, ALWAYS invoke `get_current_time` to check today's date and time.\n"
            "2. Never fabricate emails, tickets, or schedules. If a tool returns no data, explain that clearly.\n"
            "3. If a tool fails because Google credentials are missing, ask the user to type `/login` to authorize their account.\n"
            "4. Keep your replies concise, friendly, and structured using WhatsApp markdown compatibility (bold, lists).\n"
            "5. If the user asks to send an email, ALWAYS use send_email.\n"
            "6. Only use draft_email if the user explicitly asks to create a draft.\n"
            "7. Use the Active Session Memory Context to resolve terms like 'him', 'her', 'first', 'second', 'reply to it', 'forward this', 'delete it' or 'that email'. For example, if the user says 'reply to it', and the Last Selected Email ID is set, use it.\n\n"
            f"{state_context}"
        )

        # Register tools
        tool_list = [
            self.get_current_time,
            self.fetch_calendar_schedule,
            self.create_meeting,
            self.fetch_unread_emails,
            self.read_email,
            self.search_emails,
            self.reply_to_email,
            self.forward_email,
            self.mark_as_read,
            self.mark_as_unread,
            self.star_email,
            self.delete_email,
            self.get_attachments,
            self.generate_inbox_digest,
            self.get_daily_email_digest,
            self.send_email,
            self.draft_email,
            self.post_slack_message,
            self.fetch_slack_mentions,
            self.fetch_assigned_jira_tickets,
            self.log_work_hours,
            self.create_jira_issue_ticket
        ]

        try:
            return self.ai_router.generate(
                provider=Config.AI_PROVIDER,
                user_message=user_message,
                tools=tool_list,
                system_instruction=system_instruction,
            )

        except Exception as e:
            logger.exception(f"Error in SyncCopilotAgent run loop: {e}")
            return f"❌ Sorry, I encountered an internal error trying to process that: {str(e)}"
