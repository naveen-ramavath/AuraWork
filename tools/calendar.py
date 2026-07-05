import datetime
import logging
from googleapiclient.discovery import build
from services.google_oauth import get_user_credentials

logger = logging.getLogger(__name__)

def get_calendar_service(phone_number: str):
    """Initializes the Google Calendar API service."""
    creds = get_user_credentials(phone_number)
    if not creds:
        logger.warning(f"No Google credentials found for user {phone_number}.")
        return None
    return build("calendar", "v3", credentials=creds)

def fetch_calendar_events(phone_number: str, limit: int = 5) -> list:
    service = get_calendar_service(phone_number)

    print("=" * 50)
    print("PHONE:", phone_number)
    print("SERVICE:", service)

    if not service:
        return []

    try:
        now = datetime.datetime.utcnow().isoformat() + "Z"
        print("NOW:", now)

        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            maxResults=limit,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        print("EVENT RESULT:")
        print(events_result)

        events = events_result.get("items", [])
        print("TOTAL EVENTS:", len(events))

        event_list = []
        
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))
            summary = event.get("summary", "Untitled Event")
            
            event_list.append({
                "id": event.get("id"),
                "summary": summary,
                "start": start,
                "end": end,
                "location": event.get("location", ""),
                "htmlLink": event.get("htmlLink")
            })
            
        return event_list
    except Exception as e:
        logger.error(f"Error fetching calendar events for user {phone_number}: {e}")
        return []

def create_calendar_event(phone_number: str, summary: str, start_iso: str, end_iso: str, description: str = "", location: str = "") -> dict or None:
    """Creates a new calendar event in the user's primary calendar."""
    service = get_calendar_service(phone_number)
    if not service:
        return None

    try:
        # Example iso format: '2026-06-28T09:00:00+05:30'
        event_body = {
            "summary": summary,
            "location": location,
            "description": description,
            "start": {
                "dateTime": start_iso,
                "timeZone": "Asia/Kolkata", # Default timezone
            },
            "end": {
                "dateTime": end_iso,
                "timeZone": "Asia/Kolkata",
            },
            "conferenceData": {
                "createRequest": {
                    "requestId": f"sync_copilot_{int(datetime.datetime.utcnow().timestamp())}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"}
                }
            }
        }

        # Send request with support for creating Google Meet links automatically
        event = service.events().insert(
            calendarId="primary", 
            body=event_body, 
            conferenceDataVersion=1
        ).execute()
        
        return {
            "id": event.get("id"),
            "summary": event.get("summary"),
            "htmlLink": event.get("htmlLink"),
            "meetLink": event.get("conferenceData", {}).get("entryPoints", [{}])[0].get("uri", "")
        }
    except Exception as e:
        logger.error(f"Error creating calendar event for user {phone_number}: {e}")
        return None
