import re
import urllib.request

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS


def web_search(query: str, max_results: int = 5) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
        lines = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            body = r.get("body", "")
            href = r.get("href", "")
            lines.append(f"{i}. {title}\n   {body}\n   {href}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"Search failed: {e}"


def summarize_url(url: str) -> str:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; JarvisBot/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read().decode("utf-8", errors="ignore")
        # Strip script/style blocks
        raw = re.sub(r"<(script|style)[^>]*>.*?</(script|style)>", "", raw, flags=re.DOTALL | re.IGNORECASE)
        # Strip all remaining HTML tags
        text = re.sub(r"<[^>]+>", " ", raw)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text[:3000] if len(text) > 3000 else text
    except Exception as e:
        return f"Failed to fetch URL: {e}"


def search_news(query: str, max_results: int = 5) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=max_results))
        if not results:
            return "No news found."
        lines = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            date = r.get("date", "")
            source = r.get("source", "")
            body = r.get("body", "")
            url = r.get("url", "")
            lines.append(f"{i}. {title}\n   Date: {date} | Source: {source}\n   {body}\n   {url}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"News search failed: {e}"


def compare_products(product1: str, product2: str) -> str:
    query = f"{product1} vs {product2} comparison review"
    result = web_search(query, max_results=5)
    return f"Comparison: {product1} vs {product2}\n\n{result}"


def find_flights(origin: str, destination: str, date: str = None) -> str:
    query = f"flights from {origin} to {destination}"
    if date:
        query += f" {date}"
    query += " price book"
    result = web_search(query, max_results=5)
    return f"Flight search: {origin} → {destination}{' on ' + date if date else ''}\n\n{result}"


def find_hotels(location: str, checkin: str = None, checkout: str = None) -> str:
    query = f"hotels in {location}"
    if checkin:
        query += f" checkin {checkin}"
    if checkout:
        query += f" checkout {checkout}"
    result = web_search(query, max_results=5)
    return f"Hotel search: {location}{' (' + checkin + ' to ' + checkout + ')' if checkin and checkout else ''}\n\n{result}"


def get_weather(location: str) -> str:
    query = f"current weather {location} today temperature"
    result = web_search(query, max_results=3)
    return f"Weather for {location}:\n\n{result}"
