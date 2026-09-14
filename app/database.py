"""
Livello dati: SQLite.
Non salviamo token OAuth qui dentro: il refresh token Google vive solo come
variabile d'ambiente / GitHub Secret (piu' semplice e piu' sicuro di tenerlo
in un file di database che potrebbe finire per errore in un backup o in Git).
Il database serve solo per: storico esecuzioni e log, e per evitare invii doppi.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from app.config import DATABASE_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    briefing_id TEXT UNIQUE NOT NULL,   -- es. "2026-09-21_2026-09-27"
    week_start TEXT NOT NULL,
    week_end TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',  -- running | sent | error
    email_sent INTEGER NOT NULL DEFAULT 0,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS run_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    briefing_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    level TEXT NOT NULL,   -- INFO | ERROR
    message TEXT NOT NULL
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def start_run(briefing_id: str, week_start: str, week_end: str):
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO runs
               (briefing_id, week_start, week_end, started_at, status)
               VALUES (?, ?, ?, ?, 'running')""",
            (briefing_id, week_start, week_end, now),
        )


def already_sent(briefing_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT email_sent FROM runs WHERE briefing_id = ?", (briefing_id,)
        ).fetchone()
        return bool(row and row["email_sent"])


def finish_run(briefing_id: str, status: str, email_sent: bool, error_message: str = None):
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            """UPDATE runs SET finished_at = ?, status = ?, email_sent = ?, error_message = ?
               WHERE briefing_id = ?""",
            (now, status, int(email_sent), error_message, briefing_id),
        )


def log(briefing_id: str, level: str, message: str):
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO run_logs (briefing_id, ts, level, message) VALUES (?, ?, ?, ?)",
            (briefing_id, now, level, message),
        )
    print(f"[{now}] {level} - {message}")


def get_last_run():
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None


def get_run_logs(briefing_id: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM run_logs WHERE briefing_id = ? ORDER BY id ASC",
            (briefing_id,),
        ).fetchall()
        return [dict(r) for r in rows]
