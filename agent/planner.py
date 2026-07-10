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

    def fetch_unread_emails(self, limit: int = 5) -> str:
        """Retrieves unread emails from the user's Gmail inbox.

        Args:
            limit (int): Maximum number of emails to retrieve. Defaults to 5.

        Returns:
            str: JSON list of emails containing sender, subject, date, and snippet.
        """
        logger.info(f"Tool Executed: fetch_unread_emails for {self.phone_number}")
        emails = gmail_tool.fetch_unread_emails(self.phone_number, limit)
        if not emails:
            return json.dumps({"error": "No unread emails found or user not authenticated. Tell the user to run /login."})
        return json.dumps(emails)

    def read_email(self, message_id: str = None, email_index: int = None) -> str:
        """Retrieves and reads the full text of a specific Gmail email.

        Args:
            message_id (str): The unique ID of the email. Optional if email_index is given.
            email_index (int): The 1-based index of the email in the inbox list. Optional if message_id is given.

        Returns:
            str: JSON string containing details of the email or error.
        """
        logger.info(f"Tool Executed: read_email for {self.phone_number} (id: {message_id}, index: {email_index})")
        email_data = gmail_tool.read_gmail_email(self.phone_number, message_id, email_index)
        return json.dumps(email_data)

    def search_emails(self, query: str, limit: int = 5) -> str:
        """Searches the user's Gmail emails using standard Gmail search syntax (e.g. from:Microsoft, subject:internship, is:unread).

        Args:
            query (str): The search query parameter.
            limit (int): Maximum number of search results to return. Defaults to 5.

        Returns:
            str: JSON string containing a list of matching emails or error.
        """
        logger.info(f"Tool Executed: search_emails for {self.phone_number} (query: {query}, limit: {limit})")
        emails = gmail_tool.search_gmail_emails(self.phone_number, query, limit)
        return json.dumps(emails)

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
        success = gmail_tool.reply_gmail_email(self.phone_number, reply_body, message_id, email_index)
        if success:
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
        success = gmail_tool.forward_gmail_email(self.phone_number, to_email, message_id, email_index)
        if success:
            return json.dumps({"status": "success", "message": f"Email forwarded successfully to {to_email}."})
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
        success = gmail_tool.mark_gmail_email_as_read(self.phone_number, message_id, email_index)
        if success:
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
        success = gmail_tool.mark_gmail_email_as_unread(self.phone_number, message_id, email_index)
        if success:
            return json.dumps({"status": "success", "message": "Email marked as unread."})
        return json.dumps({"status": "error", "message": "Failed to mark email as unread."})

    def send_email(self, to_email: str, subject: str, body: str) -> str:
        logger.info(f"Tool Executed: send_email to {to_email}")

        success = gmail_tool.send_gmail_email(
            self.phone_number,
            to_email,
            subject,
            body
        )

        if success:
            return json.dumps({
                "status": "success",
                "message": f"Email sent successfully to {to_email}."
            })

        return json.dumps({
            "status": "error",
            "message": "Failed to send email."
        })

    def draft_email(self, to_email: str, subject: str, body: str) -> str:
        """Creates an email draft."""

        logger.info(f"Tool Executed: draft_email to {to_email}")

        success = gmail_tool.create_gmail_draft(
            self.phone_number,
            to_email,
            subject,
            body
        )

        if success:
            return json.dumps({
                "status": "success",
                "message": f"Draft created successfully for {to_email}."
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

        system_instruction = (
            "You are SyncCopilot AI, a workplace assistant that helps employees manage tasks.\n"
            "You run inside WhatsApp. Help the user complete real-world tasks using your tools.\n"
            "Your available tools represent operations on Slack, Jira, Gmail, and Google Calendar.\n\n"
            "Rules:\n"
            "1. Before scheduling anything, checking schedule, or doing date comparisons, ALWAYS invoke `get_current_time` to check today's date and time.\n"
            "2. Never fabricate emails, tickets, or schedules. If a tool returns no data, explain that clearly.\n"
            "3. If a tool fails because Google credentials are missing, ask the user to type `/login` to authorize their account.\n"
            "4. Keep your replies concise, friendly, and structured using WhatsApp markdown compatibility (bold, lists)."
            "5. If the user asks to send an email, ALWAYS use send_email.\n"
            "6. Only use draft_email if the user explicitly asks to create a draft."
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
            self.send_email,
            self.draft_email,
            self.post_slack_message,
            self.fetch_slack_mentions,
            self.fetch_assigned_jira_tickets,
            self.log_work_hours,
            self.create_jira_issue_ticket
        ]

        try:
            router = AIRouter()

            return self.ai_router.generate(
                provider=Config.AI_PROVIDER,
                user_message=user_message,
                tools=tool_list,
                system_instruction=system_instruction,
            )

        except Exception as e:
            logger.exception(f"Error in SyncCopilotAgent run loop: {e}")
            return f"❌ Sorry, I encountered an internal error trying to process that: {str(e)}"
