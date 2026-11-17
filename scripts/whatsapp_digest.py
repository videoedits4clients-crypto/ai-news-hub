#!/usr/bin/env python3
"""
Sends the top AI headlines as a WhatsApp digest.

Two providers are supported (set WHATSAPP_PROVIDER):

1. "callmebot"  — FREE, for sending to YOUR OWN number (personal use).
   One-time setup:
     a. Save +34 621 331 709 in your contacts
     b. Send it:  "I allow callmebot to send me messages"
        (check the exact activation number at https://www.callmebot.com/)
     c. It replies with your apikey
   Then set env vars:
     CALLMEBOT_PHONE   = your number with country code, e.g. 919876543210
     CALLMEBOT_APIKEY  = the key CallMeBot gave you

2. "meta"  — official WhatsApp Cloud API (for subscribers / business use).
   Create a Meta developer app (developers.facebook.com) → WhatsApp product.
   Set env vars:
     META_TOKEN          = permanent system-user access token
     META_PHONE_NUMBER_ID= your WhatsApp Business phone number ID
     META_TO             = recipient number(s), comma-separated
   NOTE: business-initiated template messages have per-message pricing;
   you must send an approved template (edit TEMPLATE below).

Usage:
    python scripts/whatsapp_digest.py             # send top stories
    python scripts/whatsapp_digest.py --top 8     # more stories
"""
import json
import os
import re
import smtplib
import sys
import urllib.parse
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEWS_FILE = ROOT / "data" / "news.json"

TEMPLATE = """🤖 *AI Pulse — Today's Top AI News*

{stories}

_Until tomorrow ⚡_"""


def load_news():
    if not NEWS_FILE.exists():
        sys.exit("data/news.json not found — run scripts/fetch_news.py first")
    return json.loads(NEWS_FILE.read_text(encoding="utf-8"))


AI_RE = re.compile(
    r"\b(ai|a\.i\.|artificial intelligence|llms?|gpt-?[0-9]*|chatgpt|claude|gemini|"
    r"openai|anthropic|nvidia|machine learning|neural|chatbots?|agentic|agents?|"
    r"models?|inference|transformer|deepmind|mistral|copilot|diffusion|robots?|"
    r"gpus?|datacent(?:er|re)|foundation model|generative)\b",
    re.IGNORECASE,
)


def is_ai_story(item):
    """General tech feeds (BBC Technology, CNBC, Verge...) carry plenty of
    non-AI news. A digest called AI Pulse must not lead with a GTA 6 story."""
    text = " ".join(str(item.get(k, "")) for k in ("title", "summary", "description"))
    return bool(AI_RE.search(text))


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


def format_digest(items):
    lines = []
    for i, it in enumerate(items, 1):
        lines.append(f"{i}. *[{it['source']}]* {it['title']}")
        lines.append(f"   {it['link']}")
    return TEMPLATE.format(stories="\n".join(lines))


def send_callmebot(text, phone, apikey):
    url = ("https://api.callmebot.com/whatsapp.php?"
           + urllib.parse.urlencode({"phone": phone, "text": text, "apikey": apikey}))
    with urllib.request.urlopen(url, timeout=30) as resp:
        body = resp.read().decode("utf-8", "replace")
    if "message queued" not in body.lower():
        raise RuntimeError(f"CallMeBot unexpected response: {body[:200]}")


def send_meta(text, token, phone_number_id, to_numbers):
    payload = json.dumps({
        "messaging_product": "whatsapp",
        "to": to_numbers[0],                       # one number per request
        "type": "text",
        "text": {"preview_url": True, "body": text},
    }).encode("utf-8")
    url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
    req = urllib.request.Request(url, data=payload, method="POST",
                                 headers={"Authorization": f"Bearer {token}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode())
    if result.get("messages"):
        return result["messages"][0].get("id", "sent")
    return result


def send_email_digest(text, to_email, sender, app_password):
    """Optionally email the same digest text (handy for copy-pasting into
    a WhatsApp Channel post). Enabled by setting DIGEST_EMAIL_TO."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "⚡ AI Pulse — today's WhatsApp digest (ready to forward)"
    msg["From"] = f"AI Pulse <{sender}>"     # show "AI Pulse", not the raw Gmail address
    msg["To"] = to_email
    msg.attach(MIMEText(text, "plain", "utf-8"))

    host = os.environ.get("SMTP_HOST") or "smtp.gmail.com"
    port = int(os.environ.get("SMTP_PORT") or "465")
    smtp_cls = smtplib.SMTP_SSL if port == 465 else smtplib.SMTP
    with smtp_cls(host, port) as smtp:
        if port != 465:
            smtp.starttls()
        smtp.login(sender, app_password)
        smtp.send_message(msg)


def main():
    top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 6
    provider = os.environ.get("WHATSAPP_PROVIDER", "callmebot")

    data = load_news()
    items = pick_stories(data, top)
    if not items:
        sys.exit("No stories found in data/news.json")
    text = format_digest(items)

    # Publish the ready-to-forward text as one small file, so anything that can
    # fetch a URL (a phone shortcut, an assistant like Instinct, a bookmark)
    # gets today's digest verbatim instead of parsing 200KB of JSON.
    digest_file = ROOT / "data" / "digest.txt"
    digest_file.parent.mkdir(parents=True, exist_ok=True)
    digest_file.write_text(text + "\n", encoding="utf-8")
    print("[OK] wrote data/digest.txt")

    # Trending clusters with their source counts, as a few hundred bytes —
    # enough for an assistant to watch ("tell me if something hits 3 sources").
    trend_file = ROOT / "data" / "trending.txt"
    clusters = [
        t for t in data.get("trending", [])
        if is_ai_story({"title": t.get("title", "")})
    ][:8]
    lines = [f"AI Pulse - trending now (feed updated {data.get('updated', '')})", ""]
    for i, t in enumerate(clusters, 1):
        srcs = t.get("sources", [])
        lines.append(f"{i}. [{t.get('count', len(srcs))} sources] {t.get('title', '')}")
        if srcs:
            lines.append("   " + " · ".join(srcs))
    trend_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("[OK] wrote data/trending.txt")

    sent_whatsapp = False
    if provider == "callmebot":
        phone = os.environ.get("CALLMEBOT_PHONE") or ""
        apikey = os.environ.get("CALLMEBOT_APIKEY") or ""
        if not apikey:
            print("[SKIP] CallMeBot API key not set yet - skipping WhatsApp send "
                  "(waiting on the key; the email copy still goes out)")
        else:
            send_callmebot(text, phone, apikey)
            sent_whatsapp = True
    elif provider == "meta":
        token = os.environ.get("META_TOKEN") or ""
        recipients = [x.strip() for x in (os.environ.get("META_TO") or "").split(",") if x.strip()]
        if not token or not recipients:
            print("[SKIP] Meta Cloud API not configured yet - skipping WhatsApp send")
        else:
            phone_number_id = os.environ["META_PHONE_NUMBER_ID"]
            for r in recipients:
                send_meta(text, token, phone_number_id, r)
            sent_whatsapp = True
    else:
        sys.exit(f"Unknown provider: {provider}")

    # Daily email copy for the WhatsApp Channel workflow (optional)
    email_to = os.environ.get("DIGEST_EMAIL_TO")
    email_from = os.environ.get("SMTP_USER")
    email_pass = os.environ.get("SMTP_APP_PASSWORD")
    email_sent = False
    if email_to and email_from and email_pass:
        try:
            send_email_digest(text, email_to, email_from, email_pass)
            email_sent = True
            print("[OK] Also emailed a copy for your Channel")
        except Exception as exc:
            print(f"[WARN] Digest email failed (non-fatal): {exc}")

    status = []
    if sent_whatsapp:
        status.append(f"sent {len(items)} stories via {provider}")
    else:
        status.append("WhatsApp send skipped (not configured yet)")
    status.append("email copy sent" if email_sent else
                  "no email copy (DIGEST_EMAIL_TO/SMTP not set)")
    print("[OK] " + "; ".join(status))


if __name__ == "__main__":
    main()
