"""
Entry point per l'esecuzione automatica (GitHub Actions) o manuale da terminale.

Uso:
    python scripts/run_briefing.py            # invia solo se e' realmente
                                                # domenica sera (finestra 18:00)
    python scripts/run_briefing.py --force     # ignora il controllo orario e
                                                # invia comunque (utile per test)
    python scripts/run_briefing.py --preview   # genera solo l'HTML, non invia
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.dates import is_sunday_evening_window
from app.briefing import run_briefing


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Ignora il controllo sull'orario ed invia comunque")
    parser.add_argument("--preview", action="store_true", help="Genera solo l'HTML senza inviare l'email")
    args = parser.parse_args()

    if args.preview:
        result = run_briefing(send=False)
        out_path = Path("preview.html")
        out_path.write_text(result["html"], encoding="utf-8")
        print(f"Anteprima salvata in {out_path.resolve()}")
        return

    if not args.force and not is_sunday_evening_window():
        print("Non siamo nella finestra di domenica ~18:00 Europe/Rome: nessuna azione. "
              "Usa --force per forzare l'invio.")
        return

    result = run_briefing(send=True, force=args.force)
    print(f"Esito: {result['status']} (briefing_id={result['briefing_id']})")
    if result.get("errors"):
        print("Avvisi/errori:", "; ".join(result["errors"]))


if __name__ == "__main__":
    main()
