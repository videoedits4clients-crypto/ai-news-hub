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
  return ""
  + "<div style='margin:0;padding:0;background:#f6f8fa;'>"
  + "<div style='max-width:600px;margin:0 auto;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#1f2328;'>"

  // header
  + "<div style='background:#0e1116;border-radius:16px 16px 0 0;padding:36px 24px;text-align:center;'>"
  + "<div style='font-size:34px;font-weight:800;color:#6ee7b7;'>&#9889; AI Pulse</div>"
  + "<div style='color:#8b949e;font-size:13px;margin-top:6px;'>Artificial intelligence news, decoded weekly</div>"
  + "</div>"

  // body
  + "<div style='background:#ffffff;border:1px solid #e1e4e8;border-top:none;padding:32px 28px;border-radius:0 0 16px 16px;'>"
  + "<h1 style='font-size:22px;margin:0 0 12px;'>Welcome aboard! &#127881;</h1>"
  + "<p style='font-size:15px;line-height:1.6;margin:0 0 18px;'>"
  + "You've just joined readers who get <b>one beautifully structured email every week</b> "
  + "&#8212; the trending AI stories, the big model releases, the funding moves, and the skills the industry is talking about. No spam. Unsubscribe anytime by replying.</p>"

  // what you get
  + "<div style='background:#f6f8fa;border:1px solid #e1e4e8;border-radius:12px;padding:18px 20px;margin-bottom:24px;'>"
  + "<div style='font-weight:800;font-size:13px;color:#57606a;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;'>Every week you'll get</div>"
  + "<div style='font-size:14.5px;line-height:2;'>"
  + "&#128293; <b>Trending</b> &#8212; stories covered by multiple sources<br>"
  + "&#129302; <b>Models &amp; releases</b> &#8212; straight from the labs<br>"
  + "&#128176; <b>Funding &amp; business</b> &#8212; who raised, who shipped<br>"
  + "&#9878;&#65039; <b>Policy</b> &#8212; the rules shaping AI"
  + "</div></div>"

  // CTAs
  + "<table width='100%' cellpadding='0' cellspacing='0'><tr>"
  + "<td style='padding-right:6px;' width='50%'>"
  + "<a href='" + SITE_URL + "' style='display:block;background:#0a9d68;color:#ffffff;font-weight:700;font-size:14px;padding:13px 10px;border-radius:10px;text-decoration:none;text-align:center;'>&#9889; Open AI Pulse</a>"
  + "</td>"
  + "<td style='padding-left:6px;' width='50%'>"
  + "<a href='" + SKILLATLAS_URL + "' style='display:block;background:#1f2328;color:#ffffff;font-weight:700;font-size:14px;padding:13px 10px;border-radius:10px;text-decoration:none;text-align:center;'>&#129517; Explore SkillAtlas</a>"
  + "</td>"
  + "</tr></table>"

  // skillatlas blurb
  + "<div style='border:1px dashed #d0d7de;border-radius:12px;padding:16px 18px;margin-top:22px;'>"
  + "<div style='font-weight:800;font-size:14px;margin-bottom:6px;'>Also from us: &#129517; SkillAtlas</div>"
  + "<p style='font-size:13.5px;line-height:1.55;color:#57606a;margin:0;'>"
  + "Every Claude &amp; AI-agent skill on GitHub &#8212; sorted into plain-English categories, "
  + "refreshed twice a day. Search, preview, and install in one click."
  + " <a href='" + SKILLATLAS_URL + "' style='color:#0969da;font-weight:700;text-decoration:none;'>Take a look &#8594;</a></p>"
  + "</div>"

  // whatsapp channel
  + "<p style='font-size:14px;line-height:1.6;margin:22px 0 0;'>"
  + "Prefer WhatsApp? Follow our daily news channel:<br>"
  + "<a href='" + CHANNEL_URL + "' style='color:#0969da;font-weight:700;text-decoration:none;'>&#128241; AI Pulse on WhatsApp &#8594;</a></p>"

  // footer
  + "<div style='color:#8b949e;font-size:12px;text-align:center;padding-top:26px;line-height:1.6;'>"
  + "You received this because you subscribed at AI Pulse.<br>"
  + "Headlines belong to their publishers."
  + "</div>"

  + "</div></div></div>";
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
