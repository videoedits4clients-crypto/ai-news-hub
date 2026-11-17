"""Builds the ready-to-forward digest text from data/news.json.

Deliberately separate from the sender. The text is regenerated on the fast
15-minute feed pipeline (fetch_news.py) and only *sent* once a day, so an
assistant fetching it at 8:10am always sees text from the last 15 minutes
instead of racing the daily job that used to produce it.
"""

from datetime import datetime, timedelta, timezone

from ai_filter import is_ai_story

IST = timezone(timedelta(hours=5, minutes=30))

TEMPLATE = """🤖 *AI Pulse — Today's Top AI News — {date}*

{stories}

_Until tomorrow ⚡_"""


def pick_stories(data, top, scan_limit=120):
    """Fresh stories, most recent first, in three tiers:
    real news outlets first, then vendor blogs/newsrooms, and community posts
    (Reddit r/*, Hacker News) only as filler — so the digest reads like
    headlines from a publication, not a forum crawl or a press-release pile.

    Only AI-related stories are eligible; if that leaves too few, the filter is
    relaxed rather than shipping a short digest."""
    def is_community(src):
        s = src.lower()
        return s.startswith("r/") or "hacker news" in s

    def is_vendor(src):
        s = src.lower()
        return "blog" in s or "newsroom" in s

    def collect(ai_only):
        max_per_src = max(1, top // 3)          # spread across sources
        seen_src, news, vendor, chatter = {}, [], [], []
        for item in data["items"][:scan_limit]:  # bounded window = stays fresh
            if ai_only and not is_ai_story(item):
                continue
            src = item["source"]
            if seen_src.get(src, 0) >= max_per_src:
                continue
            seen_src[src] = seen_src.get(src, 0) + 1
            if is_community(src):
                chatter.append(item)
            elif is_vendor(src):
                vendor.append(item)
            else:
                news.append(item)
        return news, vendor, chatter

    news, vendor, chatter = collect(ai_only=True)
    if len(news) + len(vendor) + len(chatter) < top:
        news, vendor, chatter = collect(ai_only=False)
    return (news[:top] + vendor + chatter)[:top]


def format_digest(items, when=None):
    """The date in the header is deliberate: if the file ever goes stale, the
    staleness is visible in the message itself instead of being invisible."""
    when = when or datetime.now(IST)
    lines = []
    for i, it in enumerate(items, 1):
        lines.append(f"{i}. *[{it['source']}]* {it['title']}")
        lines.append(f"   {it['link']}")
    return TEMPLATE.format(date=when.strftime("%d %b %Y"),
                           stories="\n".join(lines))
