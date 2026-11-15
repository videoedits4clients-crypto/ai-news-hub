# ⚡ AI Pulse

A free, self-updating AI news aggregator. Headlines are pulled from **33 sources**
— major tech outlets, official AI lab blogs, AI subreddits, and AI newsletters —
via RSS and published as a fast static site. **$0 hosting.**

## Sources

- **Major outlets:** TechCrunch, The Verge, Ars Technica, Wired, MIT Tech Review,
  BBC, The Guardian, CNBC, IEEE Spectrum, NVIDIA Blog, The Register (AI-filtered), ScienceDaily
- **Official AI labs:** OpenAI, Google DeepMind, Google Research, Meta Engineering,
  Hugging Face, Microsoft Research
- **Reddit communities:** r/artificial, r/MachineLearning, r/singularity,
  r/LocalLLaMA, r/OpenAI, r/ChatGPT, r/StableDiffusion
- **Newsletters & community:** Hacker News (AI search), Simon Willison,
  Import AI, Interconnects, Last Week in AI, Synced, Towards Data Science

Note: Reddit rate-limits aggressively — the fetcher retries with backoff
(6s/20s/40s) and skips failed feeds gracefully, so occasional misses are normal.

## How it works

```
RSS feeds ──▶ scripts/fetch_news.py ──▶ data/news.json ──▶ static site (index.html)
                     ▲                                          │
                     └──── GitHub Actions (hourly) ─────────────┘
```

- **No backend, no database** — the site is plain HTML that reads a JSON file.
- The Python script uses only the standard library (nothing to install).
- GitHub Actions refreshes `data/news.json` every hour and commits it.
- Sources live in `feeds.json` — add or remove feeds by editing that file.

## Weekly email newsletter (free)

Visitor flow: popup on the site → email stored in a Google Sheet →
automated styled digest every Monday via Gmail.

1. **Signup backend:** create a Google Sheet → Extensions → Apps Script →
   paste `apps-script/Code.gs` → Deploy as Web app (Anyone can access) →
   copy the `/exec` URL.
2. **Wire it up:** paste that URL into `config.js` → `newsletterEndpoint`.
   The popup on the site activates automatically. Signups land in the Sheet.
3. **Gmail app password:** enable 2-Step Verification, create an app password
   at https://myaccount.google.com/apppasswords
4. **GitHub secrets** (Settings → Secrets and variables → Actions):
   `SMTP_USER` (your Gmail), `SMTP_APP_PASSWORD`, `NEWSLETTER_ENDPOINT`,
   `SITE_URL` (https://yourusername.github.io/ai-news-hub/)
5. The `weekly-newsletter.yml` workflow sends every Monday 09:00 UTC.
   Preview what the email looks like: `python scripts/newsletter.py --dry-run`
   then open `preview.html`.

## WhatsApp daily digest

The site can push the top headlines to your WhatsApp every morning — free.

### Option A — Send to your own number (free, CallMeBot)

One-time setup:
1. Save **+34 621 331 709** in your contacts (see the current activation number at [callmebot.com](https://www.callmebot.com/blog/free-api-whatsapp-text-messages/)).
2. Send it: `I allow callmebot to send me messages` → it replies with your **apikey**.
3. In your GitHub repo add secrets (**Settings → Secrets and variables → Actions**):
   | Secret | Value |
   |---|---|
   | `WHATSAPP_PROVIDER` | `callmebot` |
   | `CALLMEBOT_PHONE`   | your number with country code, e.g. `919876543210` |
   | `CALLMEBOT_APIKEY`  | the key CallMeBot gave you |

The `whatsapp-digest.yml` workflow then fires every day at 09:00 UTC.
Test it anytime with **Actions → WhatsApp daily digest → Run workflow**,
or locally: `set CALLMEBOT_PHONE=… && set CALLMEBOT_APIKEY=… && python scripts/whatsapp_digest.py`

### Option B — Send to other people (official Meta WhatsApp Cloud API)

For subscribers/friends, use the official WhatsApp Business Cloud API
(Meta developer app → WhatsApp product). Add secrets:
`WHATSAPP_PROVIDER=meta`, `META_TOKEN`, `META_PHONE_NUMBER_ID`, `META_TO`.
Note: business-initiated messages must use approved templates and have
per-message pricing — check Meta's current rates.

## Run locally

```bash
python scripts/fetch_news.py   # refresh data
# then open index.html in a browser, or:
python -m http.server 8000     # → http://localhost:8000
```

## Deploy (free) — GitHub Pages

1. Create a GitHub repo and push this folder to it.
2. Enable **Settings → Pages → Source: Deploy from a branch → main / root**.
3. GitHub Actions will auto-refresh the news hourly; the site is always current.

Deploy (free) — Netlify alternative:
1. Push to GitHub, then "Add new site → Import from Git" on Netlify.
2. No build command, publish directory = `.` (root). Done.

## Customizing

| Want to…                    | Edit                              |
|-----------------------------|-----------------------------------|
| Add/remove news sources     | `feeds.json`                      |
| Change how often it updates | `.github/workflows/update-news.yml` (`cron: "0 * * * *"` = hourly) |
| Rename the site             | `<title>` and `.logo` in `index.html` |
| Colors / fonts              | `:root` CSS variables in `index.html` |
| Change digest time / size   | `whatsapp-digest.yml` cron, or `--top 8` in `whatsapp_digest.py` |
| Trending sensitivity        | `0.45` threshold in `trending_clusters()` (lower = more clusters) |
| Topic categories            | `TOPIC_RULES` in `index.html`     |

## Features

- **Latest feed** — search, source filter, topic filter (Models / Research /
  Funding / Policy / Chips / Business — keyword-classified client-side), and
  time filters (24h / week)
- **🔥 Trending** — stories covered by 2+ sources cluster together
  (computed at fetch time by title similarity, see `trending_clusters()`)
- **🔖 Reading list** — bookmark any story (☆ → ★); saved in the browser via
  localStorage
- **🌗 Light/dark theme** — toggle in the header, persisted per browser
- **📱 PWA** — installable on phones/desktop; works offline showing the last
  fetched news (service worker caches the shell, network-first for data)
