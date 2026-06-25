#!/usr/bin/env python3
"""
Remote Job Hunter - Email notification sender.
Sends daily job report as HTML email.
"""
import json, os, sys, time
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

CONFIG_PATH = Path(os.environ.get("JOB_HUNTER_CONFIG", "config.json"))
REPORTS_DIR = Path(os.environ.get("JOB_HUNTER_REPORTS_DIR", "reports"))
COVER_LETTERS_DIR = Path(os.environ.get("JOB_HUNTER_COVER_LETTERS_DIR", "cover-letters"))

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_cover_letters(date_str):
    cl_dir = COVER_LETTERS_DIR / date_str
    letters = {}
    if not cl_dir.exists(): return letters
    for f in sorted(cl_dir.glob("*.md")):
        key = f.stem.replace("-cover-letter", "")
        with open(f, "r", encoding="utf-8") as fh:
            letters[key] = fh.read()
    return letters

def generate_email_html(matches_data, date_str):
    matches = matches_data.get("matches", [])
    cover_letters = load_cover_letters(date_str)
    total_searched = matches_data.get("total_jobs", 0)
    excluded = matches_data.get("excluded", 0)

    jobs_html = ""
    for i, m in enumerate(matches, 1):
        score = m.get("score", 0)
        details = m.get("details", {})
        cl_key = "job-%02d" % i
        cl_content = cover_letters.get(cl_key, "")
        skill_hits = ", ".join(details.get("skill_hits", [])[:5]) or "—"
        remote_type = details.get("remote_type", "unknown")
        exp_level = details.get("exp_level", "unspecified")
        score_color = "#5a6b5a" if score >= 50 else "#8a7540" if score >= 30 else "#8a5a5a"

        cl_section = ""
        if cl_content:
            cl_escaped = cl_content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
            cl_section = '<div style="margin-top:12px;padding:12px;background:#f5f5f0;border-radius:6px;font-size:13px;line-height:1.6;"><strong>Cover Letter:</strong><br>' + cl_escaped + '</div>'

        url = m.get("url", "#")
        title = m.get("title", "Untitled")
        company = m.get("company", "")
        platform = m.get("platform", "")
        snippet = m.get("snippet", "")[:200]

        job_card = '''
        <div style="background:#fff;border:1px solid rgba(0,0,0,0.06);border-radius:12px;padding:20px;margin-bottom:16px;">
            <div style="display:flex;align-items:flex-start;gap:12px;">
                <div style="font-size:14px;font-weight:700;color:#5a6b5a;flex-shrink:0;width:28px;">#%d</div>
                <div style="flex:1;">
                    <h3 style="font-size:16px;font-weight:600;margin-bottom:4px;">
                        <a href="%s" target="_blank" style="color:#2c2a26;text-decoration:none;">%s</a>
                    </h3>
                    <div style="font-size:13px;color:#7a7568;">
                        <span>%s</span> · <span>%s</span> · <span style="padding:2px 8px;background:rgba(90,107,90,0.08);border-radius:4px;font-size:12px;">%s</span>
                    </div>
                </div>
                <div style="font-size:20px;font-weight:700;color:%s;">%d</div>
            </div>
            <div style="font-size:13px;color:#7a7568;margin-top:12px;line-height:1.6;">%s</div>
            <div style="font-size:12px;color:#5a6b5a;margin-top:8px;">Skills: %s</div>
            %s
        </div>
        ''' % (i, url, title, company, platform, remote_type, score_color, score, snippet, skill_hits, cl_section)
        jobs_html += job_card

    if not jobs_html:
        jobs_html = '<div style="text-align:center;padding:48px 24px;color:#7a7568;font-size:15px;">No matching jobs found today.</div>'

    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width,initial-scale=1.0">
        <title>Daily Job Report - %s</title>
    </head>
    <body style="font-family:-apple-system,'PingFang SC',sans-serif;background:#faf9f7;color:#2c2a26;line-height:1.7;padding:24px;">
        <div style="max-width:720px;margin:0 auto;">
            <div style="text-align:center;padding:32px 0 24px;border-bottom:1px solid rgba(0,0,0,0.06);margin-bottom:24px;">
                <h1 style="font-size:22px;font-weight:600;margin-bottom:8px;">Daily Job Report</h1>
                <div>%s</div>
                <div style="display:flex;justify-content:center;gap:24px;margin-top:12px;">
                    <div><div style="font-size:24px;font-weight:600;color:#5a6b5a;">%d</div><div style="font-size:12px;color:#7a7568;">Results</div></div>
                    <div><div style="font-size:24px;font-weight:600;color:#5a6b5a;">%d</div><div style="font-size:12px;color:#7a7568;">Matched</div></div>
                    <div><div style="font-size:24px;font-weight:600;color:#5a6b5a;">%d</div><div style="font-size:12px;color:#7a7568;">Excluded</div></div>
                </div>
            </div>
            %s
            <div style="text-align:center;padding:24px;font-size:12px;color:#7a7568;border-top:1px solid rgba(0,0,0,0.06);margin-top:24px;">
                Remote Job Hunter
            </div>
        </div>
    </body>
    </html>
    ''' % (date_str, date_str, total_searched, len(matches), excluded, jobs_html)

    return html

def send_email(to_addr, subject, html_content, config):
    smtp_config = config.get("email", {})
    smtp_host = smtp_config.get("smtp_host", "smtp.gmail.com")
    smtp_port = smtp_config.get("smtp_port", 587)
    smtp_user = smtp_config.get("smtp_user", "")
    smtp_pass = smtp_config.get("smtp_pass", "")

    if not smtp_user or not smtp_pass:
        print("[ERROR] SMTP credentials not configured in config.json", file=sys.stderr)
        print("Please add email section to config.json:", file=sys.stderr)
        print('{"email": {"smtp_host": "smtp.gmail.com", "smtp_port": 587, "smtp_user": "your@gmail.com", "smtp_pass": "your-app-password"}}', file=sys.stderr)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_addr

    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print("Email sent to %s" % to_addr, file=sys.stderr)
        return True
    except Exception as e:
        print("[ERROR] Failed to send email: %s" % e, file=sys.stderr)
        return False

def main():
    config = load_config()
    date_str = time.strftime("%Y-%m-%d")

    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            matches_data = json.load(f)
    else:
        matches_data = json.load(sys.stdin)

    matches_data["date"] = matches_data.get("date") or date_str
    html = generate_email_html(matches_data, date_str)

    to_addr = config.get("profile", {}).get("contact_email", "")
    if not to_addr:
        print("[ERROR] No contact_email in profile config", file=sys.stderr)
        return

    subject = "Daily Job Report - %s (%d matches)" % (date_str, len(matches_data.get("matches", [])))

    send_email(to_addr, subject, html, config)

    # Also save report
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / ("%s.html" % date_str)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("Report saved to: %s" % report_path, file=sys.stderr)

if __name__ == "__main__":
    main()
