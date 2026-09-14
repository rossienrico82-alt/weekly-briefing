"""
Integrazione Google Calendar (sola lettura).
Usa un refresh token OAuth generato UNA VOLTA con scripts/setup_google_auth.py
e salvato come variabile d'ambiente GOOGLE_REFRESH_TOKEN. Ad ogni esecuzione
viene scambiato per un access token temporaneo: nessuna password viene mai
letta o salvata.
"""
from datetime import datetime, time
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REFRESH_TOKEN,
    GOOGLE_SCOPES,
    TIMEZONE,
)


class CalendarError(Exception):
    pass


def _get_service():
    if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REFRESH_TOKEN):
        raise CalendarError(
            "Credenziali Google mancanti. Esegui scripts/setup_google_auth.py "
            "e imposta GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / GOOGLE_REFRESH_TOKEN."
        )
    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=GOOGLE_SCOPES,
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def fetch_events(week_start, week_end):
    """
    Recupera gli eventi da tutti i calendari visibili all'utente per
    l'intervallo [week_start 00:00, week_end 23:59:59] in Europe/Rome.
    Ritorna una lista di dict gia' normalizzati, ordinata cronologicamente.
    """
    tz = ZoneInfo(TIMEZONE)
    time_min = datetime.combine(week_start, time.min, tzinfo=tz).isoformat()
    time_max = datetime.combine(week_end, time(23, 59, 59), tzinfo=tz).isoformat()

    try:
        service = _get_service()
        cal_list = service.calendarList().list().execute().get("items", [])
    except Exception as e:
        raise CalendarError(f"Impossibile accedere a Google Calendar: {e}")

    events = []
    for cal in cal_list:
        cal_id = cal["id"]
        cal_name = cal.get("summaryOverride") or cal.get("summary") or cal_id
        try:
            page_token = None
            while True:
                result = service.events().list(
                    calendarId=cal_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,   # espande gli eventi ricorrenti
                    orderBy="startTime",
                    pageToken=page_token,
                ).execute()
                for ev in result.get("items", []):
                    events.append(_normalize_event(ev, cal_name, tz))
                page_token = result.get("nextPageToken")
                if not page_token:
                    break
        except Exception as e:
            # Un singolo calendario che fallisce non deve bloccare gli altri
            continue

    events.sort(key=lambda e: e["start"])
    return events


def _normalize_event(ev, calendar_name, tz):
    start_raw = ev["start"]
    end_raw = ev["end"]
    all_day = "date" in start_raw  # eventi "tutto il giorno" non hanno "dateTime"

    if all_day:
        start = datetime.fromisoformat(start_raw["date"]).replace(tzinfo=tz)
        end = datetime.fromisoformat(end_raw["date"]).replace(tzinfo=tz)
    else:
        start = datetime.fromisoformat(start_raw["dateTime"]).astimezone(tz)
        end = datetime.fromisoformat(end_raw["dateTime"]).astimezone(tz)

    meet_link = ev.get("hangoutLink", "")

    return {
        "title": ev.get("summary", "(senza titolo)"),
        "start": start,
        "end": end,
        "all_day": all_day,
        "location": ev.get("location", ""),
        "description": (ev.get("description") or "")[:280],  # tronca descrizioni lunghe
        "meet_link": meet_link,
        "calendar": calendar_name,
        "multi_day": (end.date() - start.date()).days >= 1 and not all_day,
    }


def group_events_by_day(events, week_start, week_end):
    """Ritorna un dict {data: [eventi]} con tutti i 7 giorni presenti anche se vuoti."""
    from datetime import timedelta
    days = {}
    d = week_start
    while d <= week_end:
        days[d] = []
        d += timedelta(days=1)

    for ev in events:
        d = ev["start"].date()
        if d in days:
            days[d].append(ev)
        elif ev["all_day"] and ev["end"].date() in days:
            # eventi tutto il giorno multi-giorno: mostralo anche sui giorni successivi
            days[ev["end"].date()].append(ev)
    return days
