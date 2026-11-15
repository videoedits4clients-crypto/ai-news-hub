#!/usr/bin/env python3
"""
Sends a structured weekly AI digest email to all subscribers.

Data comes from data/news.json (trending clusters + top stories).
Subscribers come from the Google Apps Script endpoint (see apps-script/Code.gs).
Email is sent via Gmail SMTP — you need a Google account with an App Password:
  https://myaccount.google.com/apppasswords  (enable 2-Step Verification first)

Required environment variables:
  SMTP_USER         your Gmail address
  SMTP_APP_PASSWORD the 16-character app password
  NEWSLETTER_ENDPOINT  the Apps Script web-app URL (must allow GET ?action=emails)
Optional:
  SITE_URL          public URL of the site, linked in the header
Optional:
  SMTP_HOST         SMTP server (default smtp.gmail.com)
  SMTP_PORT         465 = SSL (default), 587 = STARTTLS
Usage:
  python scripts/newsletter.py --dry-run     # write preview.html, send nothing
  python scripts/newsletter.py               # send for real
"""
import json
import os
import smtplib
import sys
import urllib.request
from collections import Counter
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEWS_FILE = ROOT / "data" / "news.json"

SMTP_HOST = os.environ.get("SMTP_HOST") or "smtp.gmail.com"
SMTP_PORT = int(os.environ.get("SMTP_PORT") or "465")

TOPIC_EMOJI = {"Models": "🤖", "Research": "🔬", "Funding": "💰",
               "Policy": "⚖️", "Chips": "🔌", "Business": "💼"}

# ---------------------------------------------------------------- data


def pick_stories(data, days=7):
    """Trending clusters + top stories from the past week, grouped by topic."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent = [it for it in data["items"]
              if it["date"] and datetime.fromisoformat(it["date"]) >= cutoff]
    if not recent:
        recent = data["items"]

    trending = data.get("trending", [])[:3]

    topic_rules = [
        ("Models & Releases", ["gpt", "claude", "gemini", "llama", "llm", "model",
                               "openai", "anthropic", "mistral", "deepseek", "agent"]),
        ("Research & Science", ["research", "paper", "study", "benchmark", "arxiv",
                                "breakthrough", "scientist", "university"]),
        ("Money & Business", ["funding", "ipo", "raise", "billion", "million",
                              "valuation", "invest", "acquisition", "stock",
                              "earnings", "startup", "ceo", "market"]),
        ("Policy & Law", ["regulat", "policy", "law", "lawsuit", "sue", "court",
                          "copyright", "privacy", "ban", "petition"]),
        ("Chips & Hardware", ["nvidia", "chip", "gpu", "tpu", "semiconductor",
                              "intel", "amd", "tsmc", "silicon"]),
    ]
    grouped, used = {}, set()
    for name, kws in topic_rules:
        bucket = [it for it in recent
                  if any(k in (it["title"] + " " + it["summary"]).lower() for k in kws)
                  and it["link"] not in used][:5]
        if bucket:
            grouped[name] = bucket
            used.update(it["link"] for it in bucket)

    # leftovers as a catch-all "More headlines"
    rest = [it for it in recent if it["link"] not in used][:8]
    if rest:
        grouped["More from the week"] = rest
    return trending, grouped


def stats(data, days=7):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent = [it for it in data["items"]
              if it["date"] and datetime.fromisoformat(it["date"]) >= cutoff]
    if not recent:
        recent = data["items"][:100]
    by_source = Counter(it["source"] for it in recent)
    top_sources = by_source.most_common(5)
    return len(recent), top_sources


# ---------------------------------------------------------------- html

def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_html(trending, grouped, n_articles, top_sources, site_url):
    updated = datetime.now(timezone.utc).strftime("%B %d, %Y")
    site_url = site_url or "http://localhost:8000/"

    parts = [f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#f6f8fa;font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#1f2328;">
<div style="max-width:640px;margin:0 auto;padding:24px 16px;">
  <div style="background:#0e1116;border-radius:16px 16px 0 0;padding:28px;text-align:center;">
    <div style="font-size:28px;font-weight:800;color:#6ee7b7;">⚡ AI Pulse</div>
    <div style="color:#8b949e;font-size:13px;margin-top:4px;">Your weekly AI digest — {updated}</div>
  </div>
  <div style="background:#ffffff;border:1px solid #e1e4e8;border-top:none;padding:24px;border-radius:0 0 16px 16px;">
    <div style="font-size:12px;color:#57606a;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">
      {n_articles} articles · {', '.join(f'{s} ({c})' for s, c in top_sources[:3])}
    </div>"""]

    if trending:
        parts.append("""    <div style="background:#fff8e6;border:1px solid #f5d76e;border-radius:12px;padding:18px;margin-bottom:20px;">
      <div style="font-weight:800;font-size:14px;color:#9a6700;margin-bottom:10px;">🔥 TRENDING THIS WEEK</div>""")
        for t in trending:
            links = "".join(
                f'<a href="{esc(l["link"])}" style="color:#0969da;font-size:12.5px;text-decoration:none;margin-right:10px;">{esc(l["source"])} ↗</a>'
                for l in t["links"][:4])
            parts.append(f"""      <div style="margin-bottom:12px;">
        <div style="font-weight:700;font-size:15px;line-height:1.4;">
          <a href="{esc(t["links"][0]["link"])}" style="color:#1f2328;text-decoration:none;">{esc(t["title"])}</a>
        </div>
        <div style="margin-top:4px;">{links}</div>
      </div>""")
        parts.append("    </div>")

    for section, items in grouped.items():
        emoji = next((TOPIC_EMOJI[k] for k, rules in [
            ("Models", ["model", "openai", "anthropic"]), ("Research", ["research"]),
            ("Business", ["money"]), ("Policy", ["policy"]), ("Chips", ["chip"])
        ] if k.lower() in section.lower() or section == k), "📰")
        parts.append(f"""    <div style="font-weight:800;font-size:14px;color:#1f2328;margin:22px 0 10px;">
      {emoji} {esc(section).upper()}</div>""")
        for it in items:
            parts.append(f"""    <div style="padding:10px 0;border-bottom:1px solid #eef1f4;">
      <div style="font-size:11.5px;color:#0a9d68;font-weight:700;">{esc(it["source"])} · {esc((it["date"] or "")[:10])}</div>
      <div style="font-size:14.5px;font-weight:600;line-height:1.45;margin-top:2px;">
        <a href="{esc(it["link"])}" style="color:#1f2328;text-decoration:none;">{esc(it["title"])}</a>
      </div>
    </div>""")

    parts.append(f"""    <div style="text-align:center;padding:24px 0 8px;">
      <a href="{esc(site_url)}" style="background:#0a9d68;color:#ffffff;font-weight:700;font-size:14px;
        padding:12px 26px;border-radius:10px;text-decoration:none;display:inline-block;">⚡ Read the live feed</a>
    </div>
    <div style="color:#8b949e;font-size:12px;text-align:center;padding-top:16px;line-height:1.6;">
      You're receiving this because you subscribed at AI Pulse.<br>
      Headlines belong to their publishers. Click any title to read the original.
    </div>
  </div>
</div>
</body></html>""")
    return "".join(parts)


# ---------------------------------------------------------------- send


def get_subscribers(endpoint):
    url = endpoint + ("&" if "?" in endpoint else "?") + "action=emails"
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    emails = sorted({e.strip().lower() for e in data.get("emails", []) if e.strip()})
    return emails


def send(sender, app_password, subject, html, subscribers, sender_name="AI Pulse"):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{sender_name} <{sender}>"
    msg["To"] = sender
    msg["Bcc"] = ", ".join(subscribers)
    msg.attach(MIMEText("Your email client doesn't support HTML. "
                        "Visit the AI Pulse website for the latest AI news.", "plain"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    with (smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) if SMTP_PORT == 465
          else smtplib.SMTP(SMTP_HOST, SMTP_PORT)) as smtp:
        if SMTP_PORT != 465:
            smtp.starttls()
        smtp.login(sender, app_password)
        smtp.send_message(msg)


def main():
    dry = "--dry-run" in sys.argv
    if not NEWS_FILE.exists():
        sys.exit("data/news.json missing — run scripts/fetch_news.py first")
    data = json.loads(NEWS_FILE.read_text(encoding="utf-8"))

    trending, grouped = pick_stories(data)
    n_articles, top_sources = stats(data)
    html = build_html(trending, grouped, n_articles, top_sources,
                      os.environ.get("SITE_URL", ""))

    if dry:
        (ROOT / "preview.html").write_text(html, encoding="utf-8")
        print("Dry run — wrote preview.html (open it in a browser to see the email)")
        return

    sender = os.environ.get("SMTP_USER")
    app_password = os.environ.get("SMTP_APP_PASSWORD")
    endpoint = os.environ.get("NEWSLETTER_ENDPOINT")
    if not (sender and app_password and endpoint):
        sys.exit("Set SMTP_USER, SMTP_APP_PASSWORD and NEWSLETTER_ENDPOINT env vars")

    subscribers = get_subscribers(endpoint)
    if not subscribers:
        print("No subscribers yet — nothing to send.")
        return

    subject = f"⚡ AI Pulse weekly: what happened in AI ({datetime.now(timezone.utc).strftime('%b %d')})"
    send(sender, app_password, subject, html, subscribers)
    print(f"✅ Sent weekly digest to {len(subscribers)} subscribers")


if __name__ == "__main__":
    main()
