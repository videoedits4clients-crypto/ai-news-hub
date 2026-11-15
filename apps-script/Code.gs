// Google Apps Script — the free "mini backend" for the newsletter signup.
//
// Handles: signup POST → store email → send styled welcome email.
// Also exposes: GET ?action=emails (subscriber list) and ?action=count.
//
// After editing this file: Deploy → Manage deployments → ✏ Edit →
// New version → Deploy, then re-authorize if a new permission is asked.

var SHEET_NAME = "Sheet1";

var SITE_URL = "https://videoedits4clients-crypto.github.io/ai-news-hub/";
var SKILLATLAS_URL = "https://videoedits4clients-crypto.github.io/skillatlas/";
var CHANNEL_URL = "https://whatsapp.com/channel/0029Vb8mlry8F2pN2kfEZT0L";

function getSheet_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(["timestamp", "email"]);
  }
  return sheet;
}

// ------------------------------------------------------ welcome email

function welcomeHtml_() {
  // Dark, brand-matching design (mirrors the site's dark + mint identity).
  // Emoji are HTML entities — never literal — so Gmail never mojibakes them.
  // Logo: hosted email-logo.png from GitHub Pages (works in Gmail, no attachment).
  // Named differently from icon.png so Gmail's image-proxy cache never serves
  // a stale/corrupted copy of the PWA icon.
  var ICON = SITE_URL + "email-logo.png";

  return ""
  + "<div style='margin:0;padding:26px 12px;background:#eef1f4;'>"
  + "<div style='max-width:600px;margin:0 auto;background:#0b0f14;border:1px solid #d0d7de;border-radius:20px;overflow:hidden;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#e6edf3;'>"

  // ===== header: hosted logo + wordmark =====
  + "<div style='text-align:center;padding:40px 24px 26px;'>"
  + "<img src='" + ICON + "' width='76' height='76' alt='AI Pulse' style='border-radius:18px;display:inline-block;'>"
  + "<div style='font-size:34px;font-weight:800;color:#6ee7b7;letter-spacing:0.5px;margin-top:14px;'>AI Pulse</div>"
  + "<div style='color:#8b949e;font-size:13px;margin-top:6px;letter-spacing:1.5px;text-transform:uppercase;'>Artificial intelligence news, decoded weekly</div>"
  + "</div>"

  // ===== hero card =====
  + "<div style='background:#161b22;border:1px solid #21262d;border-radius:16px;padding:30px 28px;margin:0 16px;'>"
  + "<div style='font-size:24px;font-weight:800;color:#ffffff;'>Welcome aboard! &#127881;</div>"
  + "<p style='font-size:15px;line-height:1.65;color:#c9d1d9;margin:12px 0 0;'>"
  + "You just joined readers who get <b style='color:#ffffff;'>one sharp, structured email every Monday</b> "
  + "&#8212; the trending AI stories, the big model releases, the funding moves and the policy shifts. "
  + "Every headline links to the original source. No spam, ever.</p>"
  + "</div>"

  // ===== what you get: 2x2 card grid =====
  + "<div style='padding:26px 16px 0;'>"
  + "<div style='color:#6ee7b7;font-size:12px;font-weight:800;letter-spacing:2px;text-transform:uppercase;margin-bottom:12px;'>&#128073; What lands in your inbox</div>"
  + "<table width='100%' cellpadding='0' cellspacing='0'><tr>"
  + "<td width='50%' style='padding:0 6px 12px 0;'>"
  +   "<div style='background:#161b22;border:1px solid #21262d;border-radius:12px;padding:16px;'>"
  +   "<div style='font-size:22px;'>&#128293;</div>"
  +   "<div style='font-weight:700;color:#ffffff;font-size:14px;margin-top:6px;'>Trending</div>"
  +   "<div style='color:#8b949e;font-size:12.5px;line-height:1.5;margin-top:3px;'>Stories covered by multiple sources, ranked</div></div>"
  + "</td>"
  + "<td width='50%' style='padding:0 0 12px 6px;'>"
  +   "<div style='background:#161b22;border:1px solid #21262d;border-radius:12px;padding:16px;'>"
  +   "<div style='font-size:22px;'>&#129302;</div>"
  +   "<div style='font-weight:700;color:#ffffff;font-size:14px;margin-top:6px;'>Models &amp; releases</div>"
  +   "<div style='color:#8b949e;font-size:12.5px;line-height:1.5;margin-top:3px;'>New launches, straight from the labs</div></div>"
  + "</td>"
  + "</tr><tr>"
  + "<td width='50%' style='padding:0 6px 0 0;'>"
  +   "<div style='background:#161b22;border:1px solid #21262d;border-radius:12px;padding:16px;'>"
  +   "<div style='font-size:22px;'>&#128176;</div>"
  +   "<div style='font-weight:700;color:#ffffff;font-size:14px;margin-top:6px;'>Money &amp; business</div>"
  +   "<div style='color:#8b949e;font-size:12.5px;line-height:1.5;margin-top:3px;'>Who raised, who shipped, who's hiring</div></div>"
  + "</td>"
  + "<td width='50%' style='padding:0 0 0 6px;'>"
  +   "<div style='background:#161b22;border:1px solid #21262d;border-radius:12px;padding:16px;'>"
  +   "<div style='font-size:22px;'>&#9878;&#65039;</div>"
  +   "<div style='font-weight:700;color:#ffffff;font-size:14px;margin-top:6px;'>Policy &amp; law</div>"
  +   "<div style='color:#8b949e;font-size:12.5px;line-height:1.5;margin-top:3px;'>The rules shaping AI, decoded</div></div>"
  + "</td>"
  + "</tr></table>"
  + "</div>"

  // ===== primary CTA =====
  + "<div style='text-align:center;padding:28px 16px 6px;'>"
  + "<a href='" + SITE_URL + "' style='display:block;background:#0a9d68;color:#ffffff;font-weight:800;font-size:15px;padding:15px 10px;border-radius:12px;text-decoration:none;'>&#9889; Open AI Pulse &#8212; it's live now</a>"
  + "<div style='color:#8b949e;font-size:12.5px;margin-top:10px;'>Fresh headlines every 15 minutes &#8212; bookmark it.</div>"
  + "</div>"

  // ===== skillatlas card =====
  + "<div style='background:#161b22;border:1px solid #21262d;border-radius:14px;padding:20px;margin:24px 16px 0;'>"
  + "<table width='100%' cellpadding='0' cellspacing='0'><tr>"
  + "<td style='vertical-align:top;padding-right:14px;font-size:24px;'>&#129517;</td>"
  + "<td style='vertical-align:top;'>"
  + "<div style='font-weight:800;color:#ffffff;font-size:14.5px;'>Also from us: SkillAtlas</div>"
  + "<p style='color:#8b949e;font-size:13px;line-height:1.55;margin:6px 0 10px;'>"
  + "Every Claude &amp; AI-agent skill on GitHub &#8212; sorted into plain-English categories, refreshed twice a day. Search, preview, install in one click.</p>"
  + "<a href='" + SKILLATLAS_URL + "' style='display:inline-block;background:#e6edf3;color:#0b0f14;font-weight:700;font-size:12.5px;padding:9px 16px;border-radius:9px;text-decoration:none;'>Explore SkillAtlas &#8594;</a>"
  + "</td></tr></table>"
  + "</div>"

  // ===== whatsapp card =====
  + "<div style='background:#161b22;border:1px solid #1a7f37;border-radius:14px;padding:20px;margin:12px 16px 0;'>"
  + "<table width='100%' cellpadding='0' cellspacing='0'><tr>"
  + "<td style='vertical-align:top;padding-right:14px;font-size:24px;'>&#128241;</td>"
  + "<td style='vertical-align:top;'>"
  + "<div style='font-weight:800;color:#ffffff;font-size:14.5px;'>Prefer WhatsApp?</div>"
  + "<p style='color:#8b949e;font-size:13px;line-height:1.55;margin:6px 0 10px;'>"
  + "Follow our channel for daily AI headlines between the weekly emails.</p>"
  + "<a href='" + CHANNEL_URL + "' style='display:inline-block;background:#1a7f37;color:#ffffff;font-weight:700;font-size:12.5px;padding:9px 16px;border-radius:9px;text-decoration:none;'>Follow AI Pulse on WhatsApp &#8594;</a>"
  + "</td></tr></table>"
  + "</div>"

  // ===== footer =====
  + "<div style='color:#6e7681;font-size:12px;text-align:center;padding:30px 24px 34px;line-height:1.7;'>"
  + "You're receiving this because you subscribed at AI Pulse.<br>"
  + "Headlines belong to their publishers. Reply any time &#8212; a human reads it."
  + "</div>"

  + "</div></div>";
}

function sendWelcome_(email) {
  MailApp.sendEmail({
    to: email,
    name: "AI Pulse",                     // sender shows as "AI Pulse", not the raw Gmail address
    subject: "Welcome to AI Pulse - your weekly AI digest",
    body: "Welcome to AI Pulse! Your weekly AI digest arrives every Monday.\n\n"
        + "News feed: " + SITE_URL + "\n"
        + "SkillAtlas: " + SKILLATLAS_URL + "\n"
        + "WhatsApp channel: " + CHANNEL_URL + "\n\n"
        + "- AI Pulse",
    htmlBody: welcomeHtml_(),
  });
}

// ------------------------------------------------------ handlers

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var email = String(data.email || "").trim().toLowerCase();

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return json_({ ok: false, error: "invalid email" });
    }

    var sheet = getSheet_();

    // skip duplicates
    var emails = sheet.getRange(2, 2, Math.max(sheet.getLastRow() - 1, 1), 1).getValues();
    for (var i = 0; i < emails.length; i++) {
      if (String(emails[i][0]).toLowerCase() === email) {
        return json_({ ok: true, duplicate: true });
      }
    }

    sheet.appendRow([new Date().toISOString(), email]);

    // welcome email — never blocks the signup itself
    try {
      sendWelcome_(email);
    } catch (mailErr) {
      // e.g. daily mail quota exceeded; the subscription is still saved
    }

    return json_({ ok: true });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  }
}

// GET ?action=emails → { emails: [...] }   (used by the weekly newsletter script)
// GET ?action=count  → { count: n }
function doGet(e) {
  var action = (e && e.parameter && e.parameter.action) || "count";
  var sheet = getSheet_();
  var lastRow = sheet.getLastRow();
  var values = lastRow > 1
    ? sheet.getRange(2, 2, lastRow - 1, 1).getValues().flat()
    : [];
  if (action === "emails") {
    return json_({ emails: values.map(function (v) { return String(v); }) });
  }
  return json_({ count: values.length });
}

function json_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

// TEST HELPER — select this in the Run ▶ dropdown and press Run.
// It sends the welcome email to your own account and triggers any
// missing authorization prompt. Delete it later if you want.
function testWelcomeEmail() {
  var me = Session.getActiveUser().getEmail();
  sendWelcome_(me);
  Logger.log("Welcome email sent to: " + me);
}
