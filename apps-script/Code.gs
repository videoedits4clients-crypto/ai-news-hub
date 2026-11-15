// Google Apps Script — the free "mini backend" for the newsletter signup.
//
// SETUP (one-time, ~5 minutes):
// 1. Go to https://sheets.google.com and create a spreadsheet named "AI Pulse subscribers".
//    Sheet1 columns: A = timestamp, B = email  (the script creates headers if missing)
// 2. In the spreadsheet: Extensions → Apps Script. Delete the sample code,
//    paste this entire file, and Save.
// 3. Click Deploy → New deployment → type: Web app
//      - Execute as: Me
//      - Who has access: Anyone
//    → Deploy → authorize → COPY the Web app URL (ends in /exec).
// 4. Paste that URL into config.js in this repo as `newsletterEndpoint`.
//
// The same URL doubles as the subscriber feed: GET <url>?action=emails
// returns all emails as JSON — the weekly newsletter script uses that.

var SHEET_NAME = "Sheet1";

function getSheet_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(["timestamp", "email"]);
  }
  return sheet;
}

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var email = String(data.email || "").trim().toLowerCase();

    // basic validation
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
