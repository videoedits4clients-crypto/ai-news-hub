#!/usr/bin/env python3
"""
Fetches AI news from RSS/Atom feeds (feeds.json) and writes data/news.json.
Uses only the Python standard library — no dependencies to install.

Run:  python scripts/fetch_news.py
"""
import email.utils
import gzip
import html
import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEEDS_FILE = ROOT / "feeds.json"
OUTPUT_FILE = ROOT / "data" / "news.json"

MAX_PER_FEED = 25
MAX_TOTAL = 400
TIMEOUT = 20
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        body = resp.read()
    # Some feeds (e.g. DeepMind) serve gzip even without asking
    if body[:2] == b"\x1f\x8b":
        body = gzip.decompress(body)
    return body


def strip_html(text: str) -> str:
    """Remove tags/entities and collapse whitespace from a summary string."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_date(raw: str) -> str:
    """Normalize various feed date formats to ISO 8601 UTC."""
    if not raw:
        return ""
    raw = raw.strip()
    dt = None
    try:
        dt = email.utils.parsedate_to_datetime(raw)          # RSS: RFC 822
    except (TypeError, ValueError):
        pass
    if dt is None:
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(raw, fmt)
                break
            except ValueError:
                continue
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def find_image(entry: ET.Element, ns: dict) -> str:
    """Best-effort image extraction: media:thumbnail > media:content > enclosure."""
    thumb = entry.find("media:thumbnail", ns)
    if thumb is not None and thumb.get("url"):
        return thumb.get("url")
    content = entry.find("media:content", ns)
    if content is not None and content.get("url") and (content.get("medium") == "image" or (content.get("type") or "").startswith("image")):
        return content.get("url")
    for enc in entry.findall("enclosure"):
        if (enc.get("type") or "").startswith("image") and enc.get("url"):
            return enc.get("url")
    return ""


def parse_feed(body: bytes) -> dict:
    """Parse an RSS 2.0 or Atom document into a normalized dict."""
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        # Some feeds embed stray HTML; retry after removing invalid control chars
        cleaned = re.sub(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]", b"", body)
        root = ET.fromstring(cleaned)

    ns = {
        "media": "http://search.yahoo.com/mrss/",
        "atom": "http://www.w3.org/2005/Atom",
        "dc": "http://purl.org/dc/elements/1.1/",
    }
    tag = root.tag.split("}")[-1].lower()
    items = []

    if tag == "rss":                                        # RSS 2.0
        for item in root.iter("item"):
            title = strip_html(item.findtext("title") or "")
            link = (item.findtext("link") or "").strip()
            items.append({
                "title": title,
                "link": link,
                "summary": strip_html(item.findtext("description") or "")[:280],
                "date": parse_date(item.findtext("pubDate") or ""),
                "image": find_image(item, ns),
            })
    elif tag in ("feed",):                                  # Atom
        for entry in root.findall("atom:entry", ns):
            link_el = entry.find("atom:link", ns)
            link = link_el.get("href") if link_el is not None else ""
            items.append({
                "title": strip_html(entry.findtext("atom:title", "", ns)),
                "link": (link or "").strip(),
                "summary": strip_html(entry.findtext("atom:summary", "", ns))[:280],
                "date": parse_date(entry.findtext("atom:updated", "", ns) or ""),
                "image": find_image(entry, ns),
            })
    return {"kind": tag, "items": items}


def fetch_feed(source: str, url: str, keywords=None):
    """Fetch one feed. If keywords is set, keep only items whose
    title/summary contains at least one keyword (AI-only sections)."""
    body = None
    for attempt, wait in enumerate((6, 20, 40), start=1):
        try:
            body = http_get(url)
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 3:         # rate limited: back off, retry
                time.sleep(wait)
                continue
            return [], f"{source}: {type(exc).__name__}: {exc}"
        except Exception as exc:
            return [], f"{source}: {type(exc).__name__}: {exc}"
    if body is None:
        return [], f"{source}: no response"

    try:
        parsed = parse_feed(body)
    except ET.ParseError as exc:
        return [], f"{source}: ParseError: {exc}"

    items = []
    for it in parsed["items"][:MAX_PER_FEED]:
        if not it["title"] or not it["link"]:
            continue
        if keywords:
            hay = (it["title"] + " " + it["summary"]).lower()
            if not any(k.lower() in hay for k in keywords):
                continue
        it["source"] = source
        items.append(it)
    return items, None


STOPWORDS = {
    "the", "and", "for", "that", "with", "from", "this", "are", "was", "were",
    "has", "have", "had", "not", "but", "you", "your", "its", "their", "they",
    "than", "then", "will", "can", "how", "why", "what", "who", "when", "after",
    "before", "over", "into", "out", "new", "says", "said", "amid", "about",
    "more", "most", "could", "would", "should", "been", "being", "which",
    "while", "also", "her", "his", "she", "him", "them", "our", "all", "any",
    "may", "might", "must", "now", "here", "there", "just", "get", "got", "one",
    "two", "still", "ever", "only", "own", "same", "very", "much", "many",
    "such", "because", "since", "during", "these", "those", "does", "did",
    "make", "made", "like", "off", "per", "via", "ltd", "inc", "against",
}


def title_tokens(title: str) -> set:
    words = re.findall(r"[a-z0-9]+", title.lower())
    return {w for w in words if len(w) >= 3 or w == "ai"} - STOPWORDS


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def trending_clusters(items):
    """Greedily group near-duplicate titles from different sources.
    A cluster of >=2 means the story is being covered widely = trending."""
    clusters = []
    for it in items:                                    # newest first
        toks = title_tokens(it["title"])
        if len(toks) < 3:
            continue
        target = None
        for cl in clusters:
            if any(jaccard(toks, t) >= 0.45 for t in cl["toks"]):
                target = cl
                break
        if target:
            target["items"].append(it)
            target["toks"].append(toks)
        else:
            clusters.append({"items": [it], "toks": [toks]})

    out = []
    for cl in clusters:
        if len(cl["items"]) < 2:
            continue
        newest = max(cl["items"], key=lambda x: x["date"])
        out.append({
            "count": len(cl["items"]),
            "title": newest["title"],
            "date": newest["date"],
            "sources": sorted({i["source"] for i in cl["items"]}),
            "links": [{"source": i["source"], "title": i["title"],
                       "link": i["link"]} for i in cl["items"]],
        })
    out.sort(key=lambda c: (c["count"], c["date"]), reverse=True)
    return out[:15]


def main() -> int:
    raw = json.loads(FEEDS_FILE.read_text(encoding="utf-8"))
    # feeds.json is either a flat list or grouped into named sections
    if isinstance(raw, list):
        feeds = raw
    else:
        feeds = [f for section in raw.values() for f in section]
    all_items, errors = [], []
    for i, feed in enumerate(feeds):
        if i > 0:
            time.sleep(3)                                   # be polite, avoid 429s
        items, err = fetch_feed(feed["name"], feed["url"], feed.get("filter"))
        all_items.extend(items)
        if err:
            errors.append(err)
        print(f"  {feed['name']:<24} {len(items):>3} items")

    # Deduplicate: prefer keeping the item whose title (lowercased, stripped
    # of punctuation) we haven't seen, and identical URLs.
    seen_titles, seen_links, unique = set(), set(), []
    for it in sorted(all_items, key=lambda x: x["date"], reverse=True):
        key = re.sub(r"[^a-z0-9 ]", "", it["title"].lower())[:90]
        if key in seen_titles or it["link"] in seen_links:
            continue
        seen_titles.add(key)
        seen_links.add(it["link"])
        unique.append(it)
    unique = unique[:MAX_TOTAL]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "count": len(unique),
        "sources": [f["name"] for f in feeds],
        "trending": trending_clusters(unique),
        "items": unique,
    }
    OUTPUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    print(f"\nWrote {len(unique)} articles -> {OUTPUT_FILE.relative_to(ROOT)}")
    if errors:
        print("Feed errors (non-fatal):")
        for e in errors:
            print("  -", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
