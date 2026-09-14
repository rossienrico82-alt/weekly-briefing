"""
Configurazione centrale dell'app.
Tutti i valori sensibili arrivano da variabili d'ambiente (.env in locale,
GitHub Secrets in produzione). Nessun segreto è mai scritto qui dentro.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Fuso orario di riferimento per tutta l'app ---
TIMEZONE = "Europe/Rome"

# --- Coordinate fisse di Gradara (PU), Marche, Italia ---
GRADARA_LAT = 43.9339
GRADARA_LON = 12.6733
GRADARA_LABEL = "Gradara (PU)"

# --- Google Calendar ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN", "")
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# --- Email ---
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)
EMAIL_TO = os.getenv("EMAIL_TO", "")

# NB: nessuna AI a pagamento e' usata: la sintesi notizie e la frase finale
# sono generate con semplice logica testuale (vedi app/summary.py), cosi'
# il progetto resta a costo zero.

# --- Dashboard ---
DASHBOARD_SECRET = os.getenv("DASHBOARD_SECRET", "")

# --- Database ---
DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/briefing.db")
Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)

# --- News RSS (fonti ufficiali, pubblicamente accessibili) ---
# NB: gli URL dei feed RSS possono cambiare nel tempo. Verificare periodicamente
# che restino validi (es. aprendo il link nel browser: deve restituire XML valido).
NEWS_FEEDS = {
    "ANSA": "https://www.ansa.it/sito/ansait_rss.xml",
    "Il Sole 24 Ore": "https://www.ilsole24ore.com/rss/italia.xml",
}
MAX_NEWS_PER_SOURCE = 5
