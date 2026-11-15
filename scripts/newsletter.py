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
    return len(recent), top_sources, len(by_source)


def short_date(iso):
    """'2026-11-15T…' → 'Nov 15' (empty-safe)."""
    try:
        return datetime.fromisoformat(iso).strftime("%b %d") if iso else ""
    except ValueError:
        return ""


# ---------------------------------------------------------------- html

def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# Per-section look: (emoji, accent color, header tint).
# Section names are internal constants — print them raw, never esc() them,
# otherwise titles like "Models & Releases" render as "MODELS &AMP; RELEASES".
SECTION_STYLE = {
    "Models & Releases":  ("\U0001F916", "#1f6feb", "#eaf2fd"),
    "Research & Science": ("\U0001F52C", "#8250df", "#f5f0fd"),
    "Money & Business":   ("\U0001F4B0", "#1a7f37", "#eaf6ee"),
    "Policy & Law":       ("\u2696\uFE0F",  "#9a6700", "#fff8e6"),
    "Chips & Hardware":   ("\U0001F50C", "#cf222e", "#fdeef0"),
    "More from the week": ("\U0001F4F0", "#57606a", "#f6f8fa"),
}


def build_html(trending, grouped, n_articles, top_sources, n_sources, site_url):
    updated = datetime.now(timezone.utc).strftime("%B %d, %Y")
    site_url = site_url or "http://localhost:8000/"

    parts = [f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#eef1f4;font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#1f2328;">
<div style="max-width:640px;margin:0 auto;padding:20px 12px;">

  <div style="background:#0e1116;border-radius:18px 18px 0 0;padding:32px 28px 26px;text-align:center;">
    <div style="font-size:36px;font-weight:800;color:#6ee7b7;letter-spacing:1px;">&#9889; AI PULSE</div>
    <div style="color:#e6edf3;font-size:12.5px;margin-top:9px;letter-spacing:2.5px;text-transform:uppercase;">Weekly AI digest &#183; {updated}</div>
    <div style="margin-top:16px;">
      <span style="display:inline-block;background:#1c2129;color:#6ee7b7;font-size:11.5px;font-weight:700;padding:6px 13px;border-radius:20px;margin:2px 3px;">{n_articles} stories scanned</span>
      <span style="display:inline-block;background:#1c2129;color:#8b949e;font-size:11.5px;font-weight:700;padding:6px 13px;border-radius:20px;margin:2px 3px;">{n_sources} sources tracked</span>
    </div>
  </div>

  <div style="background:#ffffff;border:1px solid #e1e4e8;border-top:none;padding:6px 22px 24px;border-radius:0 0 18px 18px;">"""]

    if trending:
        parts.append("""
    <div style="background:#fff8e6;border:1px solid #efd86e;border-radius:14px;padding:20px;margin:24px 0 6px;">
      <div style="font-weight:800;font-size:13px;color:#9a6700;letter-spacing:1.5px;margin-bottom:14px;">&#128293; TRENDING THIS WEEK</div>""")
        for i, t in enumerate(trending, 1):
            links = "".join(
                f'<a href="{esc(l["link"])}" style="display:inline-block;background:#ffffff;border:1px solid #e6c95e;color:#9a6700;font-size:11.5px;font-weight:700;padding:3px 11px;border-radius:14px;text-decoration:none;margin:0 5px 5px 0;">{esc(l["source"])} &#8599;</a>'
                for l in t["links"][:4])
            parts.append(f"""      <div style="background:#ffffff;border-radius:11px;padding:15px 16px;margin-bottom:10px;">
        <table cellpadding="0" cellspacing="0" width="100%"><tr>
          <td style="width:36px;vertical-align:top;padding-right:12px;">
            <div style="background:#f5d76e;color:#7a5200;font-weight:800;font-size:16px;width:30px;height:30px;line-height:30px;text-align:center;border-radius:9px;">{i}</div>
          </td>
          <td style="vertical-align:top;">
            <div style="font-weight:700;font-size:15px;line-height:1.4;">
              <a href="{esc(t["links"][0]["link"])}" style="color:#1f2328;text-decoration:none;">{esc(t["title"])}</a>
            </div>
            <div style="margin-top:7px;">{links}</div>
          </td>
        </tr></table>
      </div>""")
        parts.append("    </div>")

    for section, items in grouped.items():
        emoji, color, tint = SECTION_STYLE.get(section, ("\U0001F4F0", "#57606a", "#f6f8fa"))
        parts.append(f"""
    <div style="margin:28px 0 8px;">
      <div style="background:{tint};border-left:5px solid {color};border-radius:9px;padding:11px 15px;font-weight:800;font-size:14px;color:{color};">
        {emoji}&nbsp; {section.upper()}
      </div>""")
        for j, it in enumerate(items):
            divider = "border-bottom:none;" if j == len(items) - 1 else "border-bottom:1px solid #eef1f4;"
            meta = esc(it["source"])
            if it["date"]:
                meta += f' &#183; {esc(short_date(it["date"]))}'
            parts.append(f"""      <div style="padding:13px 14px;{divider}">
        <div style="font-size:11px;color:#0a9d68;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;">{meta}</div>
        <div style="font-size:15px;font-weight:600;line-height:1.45;margin-top:4px;">
          <a href="{esc(it["link"])}" style="color:#24292f;text-decoration:none;">{esc(it["title"])}</a>
        </div>
      </div>""")
        parts.append("    </div>")

    parts.append(f"""
    <div style="text-align:center;padding:28px 0 8px;">
      <a href="{esc(site_url)}" style="background:#0a9d68;color:#ffffff;font-weight:800;font-size:14.5px;
        padding:14px 30px;border-radius:12px;text-decoration:none;display:inline-block;">&#9889; Read the live feed</a>
      <div style="margin-top:12px;font-size:13px;">
        <a href="https://whatsapp.com/channel/0029Vb8mlry8F2pN2kfEZT0L" style="color:#0a9d68;font-weight:700;text-decoration:none;">&#128241; Get daily headlines on WhatsApp &#8594;</a>
      </div>
    </div>
    <div style="color:#8b949e;font-size:12px;text-align:center;padding-top:14px;line-height:1.7;">
      You're receiving this because you subscribed at AI Pulse.<br>
      Headlines belong to their publishers &#8212; click any title to read the original.
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
    n_articles, top_sources, n_sources = stats(data)
    html = build_html(trending, grouped, n_articles, top_sources, n_sources,
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
