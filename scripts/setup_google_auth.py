"""
Script da eseguire UNA SOLA VOLTA, sul proprio computer, per autorizzare
l'app ad accedere in sola lettura al proprio Google Calendar.

Apre il browser, l'utente fa login con il PROPRIO account Google (nessuna
password viene mai vista o salvata da questa app: e' tutto gestito da Google),
e alla fine stampa il "refresh token" da copiare in .env (o come GitHub Secret).

Uso:
    python scripts/setup_google_auth.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google_auth_oauthlib.flow import InstalledAppFlow
from app.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_SCOPES

CLIENT_CONFIG = {
    "installed": {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}


def main():
    if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET):
        print("ERRORE: imposta prima GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET nel file .env")
        print("(li trovi nel progetto Google Cloud creato seguendo il README, sezione Configurazione)")
        return

    flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, scopes=GOOGLE_SCOPES)
    # access_type=offline + prompt=consent garantiscono il rilascio di un refresh_token
    creds = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",
    )

    print("\n✅ Autorizzazione completata!\n")
    print("Copia questa riga nel tuo file .env (e come GitHub Secret, se usi l'automazione):\n")
    print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}\n")


if __name__ == "__main__":
    main()
