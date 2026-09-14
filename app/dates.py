"""
Calcolo deterministico della "settimana successiva".
Regola: se oggi (in Europe/Rome) e' domenica, la settimana successiva va
dal lunedi' immediatamente successivo alla domenica immediatamente successiva
compresa. Se lo script viene lanciato con qualche minuto di scarto rispetto
alle 18:00, il risultato e' identico: dipende solo dalla DATA del giorno di
esecuzione, non dall'orario esatto.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import TIMEZONE


def now_rome() -> datetime:
    return datetime.now(ZoneInfo(TIMEZONE))


def next_week_range(reference: datetime = None):
    """
    Ritorna (lunedi_successivo, domenica_successiva) come date.
    reference: datetime consapevole del fuso, di default 'adesso' a Roma.
    Funziona indipendentemente dal giorno della settimana in cui viene
    chiamata (utile per test manuali durante la settimana).
    """
    ref = (reference or now_rome()).date()
    days_until_next_monday = (7 - ref.weekday()) % 7
    days_until_next_monday = days_until_next_monday or 7  # se oggi e' lunedi', prendi il prossimo
    # Caso normale d'uso: lo script gira la domenica -> weekday() == 6
    # (7 - 6) % 7 = 1 -> lunedi' e' domani. Corretto.
    next_monday = ref + timedelta(days=days_until_next_monday)
    next_sunday = next_monday + timedelta(days=6)
    return next_monday, next_sunday


def briefing_id_for(week_start, week_end) -> str:
    return f"{week_start.isoformat()}_{week_end.isoformat()}"


def is_sunday_evening_window(reference: datetime = None, target_hour: int = 18, window_minutes: int = 45) -> bool:
    """
    Usata dallo script di automazione (GitHub Actions) per capire se siamo
    realmente vicini alla finestra di domenica 18:00 Europe/Rome. Il workflow
    schedula DUE trigger orari (uno per l'ora solare, uno per l'ora legale):
    solo quello coerente con il fuso corrente cade entro questa finestra
    (45 minuti, < 60 minuti di scarto tra le due schedulazioni), cosi'
    da evitare invii duplicati senza dover mantenere uno stato condiviso
    tra le due esecuzioni.
    """
    ref = reference or now_rome()
    if ref.weekday() != 6:  # 6 = domenica
        return False
    target = ref.replace(hour=target_hour, minute=0, second=0, microsecond=0)
    delta = abs((ref - target).total_seconds()) / 60
    return delta <= window_minutes
