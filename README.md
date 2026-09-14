# Weekly Briefing

Web app leggera, per un solo utente, che ogni **domenica alle 18:00 (Europe/Rome)**
invia un'email di riepilogo della settimana successiva con:
- impegni presi da **Google Calendar**
- meteo di **Gradara (PU)** (via [Open-Meteo](https://open-meteo.com), gratuita)
- notizie principali da **ANSA** e **Il Sole 24 Ore** (via feed RSS ufficiali)
- una breve sintesi finale della settimana, generata con semplice logica testuale sui dati reali raccolti (nessuna AI a pagamento)

Costi ricorrenti: **0€**, in modo verificabile (vedi sezione Costi).

---

## 1. Architettura

```
Google Calendar API (OAuth, sola lettura) ─┐
Open-Meteo API (gratuita, no key)          ├─► app/briefing.py ─► email_template.html ─► SMTP ─► la tua casella
Feed RSS ANSA + Sole 24 Ore                ┘
```
Nessun servizio a pagamento nella catena: la selezione/sintesi delle notizie e la frase
finale di riepilogo sono generate da `app/summary.py` con logica testuale (troncamento
per frasi, confronto min/max meteo), senza chiamare alcuna API AI.

- **Backend**: Python (FastAPI per la dashboard, script separato per l'invio)
- **Database**: SQLite (solo storico esecuzioni e log, NON credenziali)
- **Automazione**: GitHub Actions (cron settimanale, gratuito) — non serve un server sempre acceso
- **Dashboard**: pagina singola, opzionale, per test manuali (puoi tenerla solo in locale se non ti serve online)

**Perché queste scelte e non altre:**
- *GitHub Actions invece di un servizio "sempre acceso"*: i piani gratuiti di hosting (Render, Railway...)
  spengono l'app dopo inattività, quindi un cron interno rischierebbe di non scattare mai la domenica.
  GitHub Actions ha un cron scheduler gratuito e affidabile, per questo lo usiamo per l'**invio automatico**.
  La dashboard FastAPI resta comunque disponibile per test manuali (locale o, se vuoi, su un hosting gratuito).
- *Refresh token Google salvato come variabile d'ambiente / GitHub Secret, non nel database*: più semplice
  e più sicuro — un file di database potrebbe finire per sbaglio in un backup o essere committato.
- *SMTP (es. Gmail con App Password) invece di un servizio email a pagamento*: gratuito per un solo invio
  a settimana, e la funzione `send_email()` è isolata in `app/emailer.py` così puoi cambiare provider in futuro
  modificando un solo file.
- *Nessuna AI a pagamento*: la sintesi notizie e la frase finale sono generate con semplice logica testuale
  (`app/summary.py`), non con una chiamata a un modello AI — così il progetto è a costo zero verificabile,
  non solo "quasi zero". Il compromesso è che la sintesi è meno "discorsiva" di un testo scritto da un AI:
  se in futuro vorrai renderla più naturale, questo è l'unico punto del progetto dove aggiungere una chiamata
  a un servizio AI (anche gratuito, se ne trovi uno affidabile) senza toccare il resto dell'app.
- *Due orari di cron (17:00 e 16:00 UTC)*: GitHub Actions usa sempre UTC, ma l'Italia cambia ora legale/solare.
  Lo script stesso verifica di essere in una finestra di ±45 minuti dalle 18:00 reali a Roma, così solo il
  trigger corretto per la stagione invia davvero l'email (vedi `app/dates.py`).

### Costi previsti
| Servizio | Costo |
|---|---|
| Google Calendar API | Gratuita |
| Open-Meteo | Gratuita |
| Feed RSS ANSA / Sole 24 Ore | Gratuiti |
| GitHub Actions (cron) | Gratuito (uso minimo, ben sotto i limiti free) |
| SQLite | Gratuita |
| SMTP Gmail | Gratuito |
| Sintesi testuale (no AI) | Gratuita |

---

## 2. Struttura del progetto

```
weekly-briefing/
├── app/
│   ├── main.py              # dashboard FastAPI
│   ├── briefing.py          # orchestratore: mette insieme tutto e invia
│   ├── calendar_service.py  # Google Calendar (OAuth, sola lettura)
│   ├── weather.py           # Open-Meteo
│   ├── news.py              # RSS ANSA + Sole 24 Ore
│   ├── summary.py            # selezione/sintesi notizie + frase finale (no AI, logica testuale)
│   ├── emailer.py           # invio email (SMTP), astratto
│   ├── database.py          # SQLite: storico esecuzioni, log, dedupe
│   ├── dates.py             # calcolo "settimana successiva", finestra oraria
│   ├── config.py            # configurazione da variabili d'ambiente
│   └── templates/email_template.html
├── scripts/
│   ├── setup_google_auth.py # da lanciare UNA VOLTA per collegare Google
│   └── run_briefing.py      # eseguito da GitHub Actions ogni domenica
├── tests/test_dates.py
├── .github/workflows/weekly_briefing.yml
├── .env.example
├── .gitignore
└── requirements.txt
```

---

## 3. Configurazione — passo passo

### 3.1 Progetto Google Cloud + Calendar API
1. Vai su [console.cloud.google.com](https://console.cloud.google.com/) e crea un nuovo progetto (es. "weekly-briefing").
2. Menu ☰ → **API e servizi** → **Libreria** → cerca "Google Calendar API" → **Abilita**.
3. **API e servizi** → **Schermata consenso OAuth**:
   - Tipo utente: **Esterno** (va bene anche se sei l'unico utente — resterà in modalità "Test").
   - Compila nome app ed email, salva.
   - In "Utenti di test" aggiungi il tuo indirizzo Gmail.
4. **API e servizi** → **Credenziali** → **Crea credenziali** → **ID client OAuth**:
   - Tipo applicazione: **App desktop**.
   - Copia **Client ID** e **Client secret**.

### 3.2 File .env locale
```bash
cp .env.example .env
```
Apri `.env` e inserisci `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET` appena ottenuti.

### 3.3 Autorizzazione Google (una tantum)
```bash
pip install -r requirements.txt
python scripts/setup_google_auth.py
```
Si apre il browser: fai login col tuo account Google, accetta i permessi di **sola lettura** del calendario.
Al termine, lo script stampa una riga tipo:
```
GOOGLE_REFRESH_TOKEN=1//0g...
```
Copiala nel tuo `.env`.

### 3.4 Email (Gmail con App Password — gratuito)
1. Attiva la verifica in due passaggi sul tuo account Google, se non già attiva.
2. Vai su [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords), crea una password per l'app "Mail".
3. Nel `.env`:
   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=tuoindirizzo@gmail.com
   SMTP_PASSWORD=<la app password, 16 caratteri>
   EMAIL_FROM=tuoindirizzo@gmail.com
   EMAIL_TO=tuoindirizzo@gmail.com
   ```
   (Puoi usare un provider diverso da Gmail: basta compilare gli stessi campi SMTP_*.)

### 3.5 Meteo
Nessuna configurazione richiesta: Open-Meteo è gratuita e senza API key. Le coordinate di Gradara
sono già impostate in `app/config.py`.

### 3.6 Dashboard (opzionale)
Imposta `DASHBOARD_SECRET` in `.env` con una stringa a caso: sarà richiesta come `?token=...`
per usare la dashboard, così non è accessibile a chiunque trovi l'URL.

---

## 4. Avvio in locale

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```
Apri `http://localhost:8000/?token=IL_TUO_DASHBOARD_SECRET`.

Per generare un'anteprima HTML senza inviare nulla:
```bash
python scripts/run_briefing.py --preview
```
(crea `preview.html`, apribile nel browser)

Per un invio di test reale, immediato:
```bash
python scripts/run_briefing.py --force
```

---

## 5. Automazione (GitHub Actions — gratuita)

1. Crea un repository GitHub (privato, consigliato) e caricaci questo progetto:
   ```bash
   git init
   git add .
   git commit -m "Weekly Briefing"
   git branch -M main
   git remote add origin https://github.com/<tuo-utente>/weekly-briefing.git
   git push -u origin main
   ```
   Grazie al `.gitignore`, il file `.env` e il database **non** verranno mai caricati.

2. Nel repository su GitHub: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**,
   e aggiungi uno per uno tutti questi (stessi valori del tuo `.env`):
   `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, `SMTP_HOST`, `SMTP_PORT`,
   `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM`, `EMAIL_TO`.

3. Il workflow in `.github/workflows/weekly_briefing.yml` è già pronto: ogni domenica (finestra 18:00
   Europe/Rome) invierà automaticamente il briefing. Nessun server da mantenere acceso.

4. Per un test manuale dall'automazione stessa: nel repository, tab **Actions** → **Weekly Briefing** →
   **Run workflow** → spunta "Forza l'invio" → **Run workflow**.

---

## 6. Deploy della dashboard (opzionale)

L'invio automatico funziona già solo con GitHub Actions (punto 5), senza bisogno di alcun hosting.
Se vuoi comunque una dashboard web raggiungibile da browser (non solo in locale):

1. Vai su [render.com](https://render.com), crea un account gratuito.
2. **New** → **Web Service** → collega il repository GitHub.
3. Build command: `pip install -r requirements.txt`
   Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. In **Environment**, aggiungi le stesse variabili del tuo `.env`.
5. Deploy. Il piano gratuito "va in stop" dopo inattività e si riattiva alla prima richiesta:
   va benissimo per una dashboard usata occasionalmente, l'invio automatico resta comunque
   gestito da GitHub Actions e non dipende da questo servizio.

---

## 7. Modalità TEST

- `python scripts/run_briefing.py --preview` → genera solo l'HTML (verifica calendario, meteo, news)
- `python scripts/run_briefing.py --force` → genera E invia subito, ignorando l'orario
- Dashboard → pulsante **"Genera briefing adesso"** (genera e invia) o **"Invia email di test"**
- `GET /preview?token=...` sulla dashboard → mostra l'HTML nel browser senza inviare nulla

---

## 8. Sicurezza — checklist

- [x] Nessuna password o API key nel codice sorgente: tutto arriva da variabili d'ambiente.
- [x] `.env` è in `.gitignore`: non verrà mai committato.
- [x] Il refresh token Google non è mai salvato nel database né mostrato in dashboard.
- [x] Scope Google Calendar è di **sola lettura** (`calendar.readonly`): l'app non può modificare/cancellare eventi.
- [x] Gli endpoint della dashboard che eseguono azioni (`/run`, `/test-email`) richiedono `DASHBOARD_SECRET`.
- [x] I feed RSS vengono letti con normali richieste GET, nel rispetto dei termini di sindacazione dei siti (nessuno scraping aggressivo).

Prima di pubblicare il repository, verifica comunque con `git log` e `git diff` che nessun file `.env`
o log con dati personali sia mai stato aggiunto per errore.

---

## 9. Modifica dell'orario di invio

Cambia i due valori cron in `.github/workflows/weekly_briefing.yml` (sono in UTC). Ad esempio, per
inviare alle 20:00 Europe/Rome: `0 19 * * 0` e `0 18 * * 0`. Aggiorna anche `target_hour` in
`app/dates.py` (funzione `is_sunday_evening_window`) se cambi anche l'ora, non solo il giorno.

---

## 10. Troubleshooting

| Problema | Causa probabile | Soluzione |
|---|---|---|
| "Credenziali Google mancanti" | `.env` incompleto o refresh token scaduto | Rilancia `scripts/setup_google_auth.py` |
| Nessun evento trovato ma il calendario ne ha | L'evento è su un calendario secondario non selezionato | L'app legge già tutti i calendari visibili nell'account; verifica che siano "mostrati" nel tuo Google Calendar |
| Email non arriva | Password errata o SMTP bloccato | Verifica di usare una **App Password**, non la password normale di Gmail |
| ANSA o Sole 24 Ore mancanti nell'email | Feed RSS momentaneamente irraggiungibile o URL cambiato | L'app continua comunque con le altre sezioni; verifica l'URL in `app/config.py` aprendolo nel browser |
| GitHub Actions non invia nulla | Nessun trigger cade nella finestra ±45 min delle 18:00 Rome | Usa "Run workflow" con "Forza l'invio" per un invio manuale; controlla i log dell'Action |
| Email duplicata la stessa settimana | Non dovrebbe succedere: l'invio è protetto da `briefing_id` univoco nel database | Se capita, controlla che `data/` non venga ripulita tra le esecuzioni |

---

**Flusso finale d'uso:** colleghi Google Calendar una volta (`setup_google_auth.py`) → configuri
l'email in `.env`/Secrets → fai un test (`--force` o pulsante dashboard) → carichi su GitHub →
da quel momento, ogni domenica alle 18:00, ricevi il briefing automaticamente.
