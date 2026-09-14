"""Test minimale per la logica di calcolo della settimana (il punto più delicato)."""
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.dates import next_week_range, briefing_id_for


def test_domenica_sera():
    # Domenica 20 settembre 2026, ore 18:00 Europe/Rome -> settimana 21-27/09/2026
    ref = datetime(2026, 9, 20, 18, 0, tzinfo=ZoneInfo("Europe/Rome"))
    start, end = next_week_range(ref)
    assert start.isoformat() == "2026-09-21"
    assert end.isoformat() == "2026-09-27"
    assert briefing_id_for(start, end) == "2026-09-21_2026-09-27"


def test_lunedi():
    # Se lanciato di lunedì, deve prendere il lunedì della settimana successiva (non quello odierno)
    ref = datetime(2026, 9, 21, 10, 0, tzinfo=ZoneInfo("Europe/Rome"))
    start, end = next_week_range(ref)
    assert start.isoformat() == "2026-09-28"


if __name__ == "__main__":
    test_domenica_sera()
    test_lunedi()
    print("OK: tutti i test superati")
