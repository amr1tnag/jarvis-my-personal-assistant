"""
Google Calendar integration.
Setup (one-time):
  1. Go to console.cloud.google.com → create a project
  2. Enable the Google Calendar API
  3. Create OAuth 2.0 credentials (Desktop app) → download as
     jarvis-my-personal-assistant/credentials.json
  4. Run Jarvis once — a browser tab opens asking you to log in.
     After that, token.json is saved and no browser is needed again.
"""

import os
import datetime

_CREDS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "credentials.json")
_TOKEN_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "token.json")
_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def _get_service():
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = None
        if os.path.exists(_TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(_TOKEN_FILE, _SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(_CREDS_FILE):
                    return None, "credentials.json not found. See setup instructions in jarvis/skills/calendar.py."
                flow = InstalledAppFlow.from_client_secrets_file(_CREDS_FILE, _SCOPES)
                creds = flow.run_local_server(port=0)
            with open(_TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        return build("calendar", "v3", credentials=creds), None
    except ImportError:
        return None, "Google Calendar packages not installed. Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
    except Exception as e:
        return None, str(e)


def get_todays_events() -> str:
    service, err = _get_service()
    if err:
        return f"Calendar unavailable: {err}"

    now = datetime.datetime.utcnow()
    start = now.replace(hour=0, minute=0, second=0).isoformat() + "Z"
    end   = now.replace(hour=23, minute=59, second=59).isoformat() + "Z"

    try:
        result = service.events().list(
            calendarId="primary",
            timeMin=start,
            timeMax=end,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = result.get("items", [])
        if not events:
            return "You have no events scheduled for today."
        lines = []
        for e in events:
            start_val = e["start"].get("dateTime", e["start"].get("date", ""))
            if "T" in start_val:
                t = datetime.datetime.fromisoformat(start_val.replace("Z", "+00:00"))
                t_local = t.astimezone()
                time_str = t_local.strftime("%-I:%M %p")
            else:
                time_str = "all day"
            lines.append(f"{e['summary']} at {time_str}")
        return "Today's schedule: " + "; ".join(lines)
    except Exception as e:
        return f"Couldn't fetch calendar: {e}"


def get_upcoming_events(days: int = 7) -> str:
    service, err = _get_service()
    if err:
        return f"Calendar unavailable: {err}"

    now = datetime.datetime.utcnow()
    end = (now + datetime.timedelta(days=days)).isoformat() + "Z"

    try:
        result = service.events().list(
            calendarId="primary",
            timeMin=now.isoformat() + "Z",
            timeMax=end,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = result.get("items", [])
        if not events:
            return f"Nothing scheduled in the next {days} days."
        lines = []
        for e in events:
            start_val = e["start"].get("dateTime", e["start"].get("date", ""))
            if "T" in start_val:
                t = datetime.datetime.fromisoformat(start_val.replace("Z", "+00:00"))
                t_local = t.astimezone()
                date_str = t_local.strftime("%A %-I:%M %p")
            else:
                date_str = start_val
            lines.append(f"{e['summary']} on {date_str}")
        return "Upcoming: " + "; ".join(lines)
    except Exception as e:
        return f"Couldn't fetch calendar: {e}"
