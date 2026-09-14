"""
Selezione e sintesi delle notizie + frase riassuntiva della settimana,
SENZA alcuna chiamata a servizi AI a pagamento: tutto e' generato con
semplice logica testuale sui dati gia' recuperati da calendario/meteo/RSS.
Questo mantiene il progetto a costo zero, come richiesto.
"""
import re


def summarize_news(news_by_source: dict) -> dict:
    """
    Riceve i dati grezzi dei feed (titolo/link/estratto) e ritorna, per ogni
    fonte, la lista di notizie gia' pronte per l'email: usa direttamente
    l'estratto fornito dal feed RSS (nessuna invenzione), leggermente ripulito
    e accorciato a 2-3 frasi.
    """
    output = {}
    for source, data in news_by_source.items():
        if not data["ok"]:
            continue
        items = []
        for it in data["items"]:
            items.append({
                "title": it["title"],
                "link": it["link"],
                "summary": _shorten(it["summary"]),
            })
        output[source] = items
    return output


def _shorten(text: str, max_sentences: int = 3, max_chars: int = 320) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    short = " ".join(sentences[:max_sentences])
    if len(short) > max_chars:
        short = short[:max_chars].rsplit(" ", 1)[0] + "…"
    return short


def generate_week_summary(events_count: int, days_with_events: int, weather_by_day: dict) -> str:
    """
    Frase pratica di sintesi della settimana, costruita con un semplice
    template a partire solo sui dati reali raccolti (nessuna AI).
    """
    if events_count == 0:
        impegni = "Nessun impegno in calendario per la settimana."
    elif events_count == 1:
        impegni = "Un solo impegno in calendario, in 1 giorno."
    else:
        impegni = f"{events_count} impegni in calendario, distribuiti su {days_with_events} giorni."

    meteo = _weather_highlight(weather_by_day)
    return f"{impegni} {meteo}".strip()


def _weather_highlight(weather_by_day: dict) -> str:
    valid = {d: w for d, w in weather_by_day.items() if w}
    if not valid:
        return "Previsioni meteo non disponibili."

    max_temp_day = max(valid.items(), key=lambda kv: kv[1]["max"])
    min_temp_day = min(valid.items(), key=lambda kv: kv[1]["min"])
    rainy_days = [d for d, w in valid.items() if (w.get("rain_prob") or 0) >= 60]

    parts = []
    if max_temp_day[1]["max"] >= 30:
        parts.append(f"Picco di caldo il {_fmt_date(max_temp_day[0])} ({round(max_temp_day[1]['max'])}°C).")
    if min_temp_day[1]["min"] <= 2:
        parts.append(f"Giornata fredda il {_fmt_date(min_temp_day[0])} ({round(min_temp_day[1]['min'])}°C).")
    if rainy_days:
        giorni = ", ".join(_fmt_date(d) for d in rainy_days)
        parts.append(f"Alta probabilità di pioggia: {giorni}.")
    if not parts:
        parts.append("Meteo nella media, senza estremi particolari.")
    return " ".join(parts)


def _fmt_date(iso_date: str) -> str:
    from datetime import date
    d = date.fromisoformat(iso_date)
    return d.strftime("%d/%m")
