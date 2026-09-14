"""
Orchestratore: mette insieme calendario + meteo + news e genera/invia
il briefing settimanale. Punto d'ingresso usato sia dallo script CLI
(GitHub Actions) sia dai pulsanti della dashboard.
"""
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app import database as db
from app.config import EMAIL_TO, TIMEZONE
from app.dates import now_rome, next_week_range, briefing_id_for
from app.calendar_service import fetch_events, group_events_by_day, CalendarError
from app.weather import fetch_weather, WeatherError
from app.news import fetch_news
from app.summary import summarize_news, generate_week_summary
from app.emailer import send_email, EmailError

GIORNI_IT = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

TEMPLATE_DIR = Path(__file__).parent / "templates"
_env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))


def run_briefing(send: bool = True, force: bool = False) -> dict:
    """
    Esegue l'intero processo. Se send=False, genera solo l'HTML senza inviare
    (usato per l'anteprima/test). Se force=True, invia anche se un briefing
    per la stessa settimana risulta già inviato (utile per test manuali).
    Ritorna un dict con esito, log e (se generato) l'HTML.
    """
    db.init_db()
    week_start, week_end = next_week_range()
    briefing_id = briefing_id_for(week_start, week_end)
    db.start_run(briefing_id, week_start.isoformat(), week_end.isoformat())

    if send and not force and db.already_sent(briefing_id):
        db.log(briefing_id, "INFO", "Briefing già inviato per questa settimana: nessuna azione.")
        return {"status": "skipped", "briefing_id": briefing_id}

    errors = []

    # 1. Google Calendar
    try:
        db.log(briefing_id, "INFO", "Avvio Weekly Briefing")
        events = fetch_events(week_start, week_end)
        db.log(briefing_id, "INFO", f"Google Calendar OK – trovati {len(events)} eventi")
        calendar_ok = True
    except CalendarError as e:
        events = []
        calendar_ok = False
        errors.append(str(e))
        db.log(briefing_id, "ERROR", f"Google Calendar KO – {e}")

    days_map = group_events_by_day(events, week_start, week_end)
    days = []
    for i, (d, evs) in enumerate(sorted(days_map.items())):
        days.append({
            "label": f"{GIORNI_IT[i]} {d.strftime('%d/%m')}",
            "events": [_format_event(ev) for ev in evs],
        })

    # 2. Meteo
    try:
        weather_raw = fetch_weather(week_start, week_end)
        db.log(briefing_id, "INFO", "Meteo OK")
    except WeatherError as e:
        weather_raw = {}
        errors.append(str(e))
        db.log(briefing_id, "ERROR", f"Meteo KO – {e}")

    weather = _format_weather(week_start, week_end, weather_raw)

    # 3. News (ANSA + Sole 24 Ore), ognuna indipendente
    news_raw = fetch_news()
    for source, data in news_raw.items():
        if data["ok"]:
            db.log(briefing_id, "INFO", f"{source} OK – {len(data['items'])} notizie")
        else:
            errors.append(f"{source}: {data['error']}")
            db.log(briefing_id, "ERROR", f"{source} KO – {data['error']}")

    news_summarized = summarize_news(news_raw)
    db.log(briefing_id, "INFO", "Selezione/sintesi notizie OK")

    # 4. Sintesi finale della settimana (generata con logica testuale, non AI)
    events_count = len(events)
    days_with_events = sum(1 for d in days if d["events"])
    week_summary = generate_week_summary(events_count, days_with_events, weather_raw)
    db.log(briefing_id, "INFO", "Generazione sintesi settimana OK")

    # 5. Render HTML
    template = _env.get_template("email_template.html")
    html = template.render(
        week_start_label=week_start.strftime("%d/%m"),
        week_end_label=week_end.strftime("%d/%m"),
        days=days,
        weather=weather,
        ansa_news=news_summarized.get("ANSA", []),
        ansa_error=not news_raw.get("ANSA", {}).get("ok", True),
        sole_news=news_summarized.get("Il Sole 24 Ore", []),
        sole_error=not news_raw.get("Il Sole 24 Ore", {}).get("ok", True),
        week_summary=week_summary,
        generated_at=now_rome().strftime("%d/%m/%Y %H:%M"),
    )
    db.log(briefing_id, "INFO", "Generazione briefing OK")

    result = {
        "status": "generated",
        "briefing_id": briefing_id,
        "html": html,
        "errors": errors,
        "calendar_ok": calendar_ok,
    }

    if not send:
        db.finish_run(briefing_id, "generated", email_sent=False,
                       error_message="; ".join(errors) if errors else None)
        return result

    if not calendar_ok:
        # Senza calendario il briefing non è completo: lo segnaliamo ma
        # inviamo comunque meteo + news, come richiesto (gestione errori §16).
        db.log(briefing_id, "ERROR", "Calendario mancante: email inviata comunque, incompleta")

    subject = f"📅 Weekly Briefing – settimana dal {week_start.strftime('%d/%m')} al {week_end.strftime('%d/%m')}"
    try:
        send_email(EMAIL_TO, subject, html)
        db.log(briefing_id, "INFO", "Email inviata OK")
        db.finish_run(briefing_id, "sent", email_sent=True,
                       error_message="; ".join(errors) if errors else None)
        result["status"] = "sent"
    except EmailError as e:
        db.log(briefing_id, "ERROR", f"Invio email KO – {e}")
        db.finish_run(briefing_id, "error", email_sent=False, error_message=str(e))
        result["status"] = "error"
        result["errors"].append(str(e))

    return result


def _format_event(ev) -> dict:
    return {
        "title": ev["title"],
        "all_day": ev["all_day"],
        "start_time": ev["start"].strftime("%H:%M"),
        "end_time": ev["end"].strftime("%H:%M"),
        "location": ev["location"],
        "meet_link": ev["meet_link"],
    }


def _format_weather(week_start, week_end, weather_raw) -> list:
    from datetime import timedelta
    result = []
    d = week_start
    i = 0
    while d <= week_end:
        w = weather_raw.get(d.isoformat())
        entry = {"label": f"{GIORNI_IT[i]} {d.strftime('%d/%m')}", "available": w is not None}
        if w:
            highlight = None
            if w["max"] >= 30:
                highlight = "🔥 Molto caldo"
            elif w["min"] <= 2:
                highlight = "❄️ Freddo"
            elif w["rain_prob"] is not None and w["rain_prob"] >= 60:
                highlight = "☔ Alta probabilità di pioggia"
            entry.update({
                "min": round(w["min"]), "max": round(w["max"]),
                "emoji": w["emoji"], "text": w["label"],
                "rain_prob": w["rain_prob"], "highlight": highlight,
            })
        result.append(entry)
        d += timedelta(days=1)
        i += 1
    return result
