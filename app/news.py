"""
Notizie da feed RSS ufficiali (ANSA, Il Sole 24 Ore).
Nessuno scraping aggressivo: leggiamo solo i feed RSS pubblici pensati
per la sindacazione dei contenuti, con un semplice GET.
"""
import feedparser
import httpx

from app.config import NEWS_FEEDS, MAX_NEWS_PER_SOURCE


class NewsSourceError(Exception):
    pass


def fetch_news():
    """
    Ritorna dict {nome_fonte: {"ok": bool, "items": [...], "error": str|None}}
    Una fonte che fallisce non blocca le altre (gestito dal chiamante).
    """
    results = {}
    for source, url in NEWS_FEEDS.items():
        try:
            resp = httpx.get(url, timeout=15, headers={"User-Agent": "WeeklyBriefing/1.0"})
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
            if parsed.bozo and not parsed.entries:
                raise NewsSourceError(str(parsed.bozo_exception))

            items = []
            for entry in parsed.entries[:MAX_NEWS_PER_SOURCE]:
                items.append({
                    "title": entry.get("title", "").strip(),
                    "link": entry.get("link", ""),
                    "summary": _clean_summary(entry.get("summary", "")),
                    "published": entry.get("published", ""),
                })
            results[source] = {"ok": True, "items": items, "error": None}
        except Exception as e:
            results[source] = {"ok": False, "items": [], "error": str(e)}
    return results


def _clean_summary(html_summary: str) -> str:
    import re
    text = re.sub(r"<[^>]+>", "", html_summary or "")
    return text.strip()[:400]
