"""
Dashboard web minimale: stato connessioni + pulsanti "Genera briefing adesso"
e "Invia email di test". Nessuna credenziale viene mai mostrata qui.
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import database as db
from app.config import (
    GOOGLE_CLIENT_ID, GOOGLE_REFRESH_TOKEN, SMTP_HOST, SMTP_USER, EMAIL_TO,
    DASHBOARD_SECRET, GRADARA_LABEL, NEWS_FEEDS,
)
from app.dates import next_week_range
from app.briefing import run_briefing

app = FastAPI(title="Weekly Briefing")
templates = Jinja2Templates(directory=str(__import__("pathlib").Path(__file__).parent / "templates"))

db.init_db()


def _check_auth(request: Request):
    if DASHBOARD_SECRET:
        token = request.query_params.get("token") or request.headers.get("x-dashboard-secret")
        if token != DASHBOARD_SECRET:
            raise HTTPException(status_code=401, detail="Non autorizzato")


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    _check_auth(request)
    week_start, week_end = next_week_range()
    last_run = db.get_last_run()
    status = {
        "google": bool(GOOGLE_CLIENT_ID and GOOGLE_REFRESH_TOKEN),
        "email": bool(SMTP_HOST and SMTP_USER and EMAIL_TO),
    }
    token_qs = f"?token={DASHBOARD_SECRET}" if DASHBOARD_SECRET else ""
    return f"""
    <html><head><meta charset="utf-8"><title>Weekly Briefing</title>
    <style>
      body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:640px;margin:40px auto;color:#1f2328;background:#f7f8fa}}
      .card{{background:#fff;border-radius:12px;padding:20px 24px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
      .row{{display:flex;justify-content:space-between;align-items:center;padding:6px 0}}
      .dot{{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:8px}}
      .ok{{background:#2fb344}} .ko{{background:#e5484d}}
      button{{background:#2b2d42;color:#fff;border:none;padding:10px 18px;border-radius:8px;cursor:pointer;font-size:14px;margin-right:8px}}
      button:hover{{opacity:.9}}
      pre{{background:#0f1115;color:#c9ccd6;padding:12px;border-radius:8px;overflow:auto;font-size:12px;max-height:240px}}
    </style></head>
    <body>
      <h1>📅 Weekly Briefing</h1>
      <div class="card">
        <div class="row"><span><span class="dot {'ok' if status['google'] else 'ko'}"></span>Google Calendar</span>
          <span>{'Collegato' if status['google'] else 'Non collegato — esegui scripts/setup_google_auth.py'}</span></div>
        <div class="row"><span><span class="dot {'ok' if status['email'] else 'ko'}"></span>Email ({EMAIL_TO or '—'})</span></div>
        <div class="row"><span><span class="dot ok"></span>Meteo – {GRADARA_LABEL}</span></div>
        <div class="row"><span><span class="dot ok"></span>News – {', '.join(NEWS_FEEDS.keys())}</span></div>
      </div>
      <div class="card">
        <p><strong>Prossima esecuzione:</strong> Domenica ore 18:00 (settimana {week_start.strftime('%d/%m')} – {week_end.strftime('%d/%m')})</p>
        <form method="post" action="/run{token_qs}"><button type="submit">Genera briefing adesso</button></form>
        <form method="post" action="/test-email{token_qs}"><button type="submit">Invia email di test</button></form>
      </div>
      <div class="card">
        <p><strong>Ultimo briefing:</strong> {last_run['briefing_id'] if last_run else '—'}<br>
        Stato: {last_run['status'] if last_run else '—'} · Email inviata: {'sì' if last_run and last_run['email_sent'] else 'no'}<br>
        {f"Errore: {last_run['error_message']}" if last_run and last_run.get('error_message') else ''}</p>
      </div>
    </body></html>
    """


@app.post("/run")
def trigger_run(request: Request, send: bool = True):
    _check_auth(request)
    result = run_briefing(send=send, force=True)
    return result


@app.post("/test-email")
def test_email(request: Request):
    """Genera il briefing e lo invia forzatamente, come test end-to-end."""
    _check_auth(request)
    result = run_briefing(send=True, force=True)
    return result


@app.get("/preview", response_class=HTMLResponse)
def preview(request: Request):
    """Anteprima HTML del prossimo briefing SENZA inviare email."""
    _check_auth(request)
    result = run_briefing(send=False)
    return result.get("html", "<p>Nessun contenuto generato.</p>")


@app.get("/health")
def health():
    return {"status": "ok"}
