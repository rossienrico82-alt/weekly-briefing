"""
Meteo via Open-Meteo (gratuita, senza API key).
Nessun dato viene inventato: se un giorno manca nella risposta dell'API,
viene segnalato esplicitamente come non disponibile.
"""
import httpx

from app.config import GRADARA_LAT, GRADARA_LON, TIMEZONE

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Mappatura sintetica dei weather code Open-Meteo (WMO) -> emoji + testo breve
WMO_CODES = {
    0: ("☀️", "Sereno"),
    1: ("🌤", "Prevalentemente sereno"),
    2: ("⛅", "Parzialmente nuvoloso"),
    3: ("☁️", "Nuvoloso"),
    45: ("🌫", "Nebbia"), 48: ("🌫", "Nebbia con brina"),
    51: ("🌦", "Pioviggine debole"), 53: ("🌦", "Pioviggine"), 55: ("🌦", "Pioviggine intensa"),
    61: ("🌧", "Pioggia debole"), 63: ("🌧", "Pioggia"), 65: ("🌧", "Pioggia intensa"),
    71: ("🌨", "Neve debole"), 73: ("🌨", "Neve"), 75: ("🌨", "Neve intensa"),
    80: ("🌦", "Rovesci deboli"), 81: ("🌧", "Rovesci"), 82: ("⛈", "Rovesci violenti"),
    95: ("⛈", "Temporale"), 96: ("⛈", "Temporale con grandine"), 99: ("⛈", "Temporale forte"),
}


class WeatherError(Exception):
    pass


def fetch_weather(week_start, week_end):
    """
    Ritorna un dict {data: {min, max, code, emoji, testo, prob_pioggia} | None}
    None significa "dato non disponibile per questo giorno".
    """
    params = {
        "latitude": GRADARA_LAT,
        "longitude": GRADARA_LON,
        "daily": "temperature_2m_min,temperature_2m_max,weathercode,precipitation_probability_max",
        "timezone": TIMEZONE,
        "start_date": week_start.isoformat(),
        "end_date": week_end.isoformat(),
    }
    try:
        resp = httpx.get(OPEN_METEO_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise WeatherError(f"Impossibile contattare Open-Meteo: {e}")

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    result = {}
    for i, d in enumerate(dates):
        try:
            code = daily["weathercode"][i]
            emoji, label = WMO_CODES.get(code, ("❓", "Condizioni sconosciute"))
            result[d] = {
                "min": daily["temperature_2m_min"][i],
                "max": daily["temperature_2m_max"][i],
                "emoji": emoji,
                "label": label,
                "rain_prob": daily.get("precipitation_probability_max", [None] * len(dates))[i],
            }
        except (KeyError, IndexError, TypeError):
            result[d] = None
    return result
