import os
import sys
import ssl
import imaplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_connection, update_lead_status

# ── CONFIG ──────────────────────────────────────────────
SMTP_HOST   = os.getenv("SMTP_HOST",   "mail.privateemail.com")
SMTP_PORT   = int(os.getenv("SMTP_PORT", 465))
SMTP_USER   = os.getenv("SMTP_USER")
SMTP_PASS   = os.getenv("SMTP_PASS")
SENDER_NAME = os.getenv("SENDER_NAME", "Anindya")
REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "reports"
)
# ────────────────────────────────────────────────────────


def get_approved_to_send():
    """Get all leads approved to send."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, phone, website, email, email_subject, email_body
        FROM leads WHERE status = 'approved_to_send'
    """)
    rows = cursor.fetchall()
    conn.close()

    leads = []
    for row in rows:
        leads.append({
            "id":            row[0],
            "name":          row[1],
            "phone":         row[2],
            "website":       row[3],
            "email":         row[4],
            "email_subject": row[5],
            "email_body":    row[6],
        })
    return leads


def get_report_path(name: str) -> str:
    """Get PDF report path for a business."""
    safe_name = name.replace(" ", "_").replace("/", "_").replace("|", "").strip("_")[:30]
    return os.path.join(REPORTS_DIR, f"{safe_name}_report.pdf")


def save_to_sent_folder(msg) -> None:
    """Save a copy of the sent email to the IMAP Sent folder."""
    try:
        print(f"    [📬] Connecting to IMAP: {SMTP_HOST}")
        imap = imaplib.IMAP4_SSL(SMTP_HOST)
        imap.login(SMTP_USER, SMTP_PASS)
        print(f"    [📬] IMAP login successful")

        result = imap.append(
            "Sent",
            "\\Seen",
            imaplib.Time2Internaldate(datetime.now(timezone.utc)),
            msg.as_bytes()
        )
        print(f"    [📬] Append result: {result}")
        imap.logout()

    except Exception as e:
        print(f"    [!] IMAP Sent save failed: {e}")

        imap.logout()

    except Exception as e:
        print(f"    [!] IMAP Sent save failed: {e}")


def send_email(to_email: str, to_name: str, subject: str, body: str, report_path: str = None) -> bool:
    """Send a single email with optional PDF attachment."""
    try:
        msg = MIMEMultipart()
        msg["From"]    = f"{SENDER_NAME} <{SMTP_USER}>"
        msg["To"]      = to_email
        msg["Subject"] = subject

        # Email body
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # Attach PDF report if it exists
        if report_path and os.path.exists(report_path):
            with open(report_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                filename = os.path.basename(report_path)
                part.add_header("Content-Disposition", f"attachment; filename={filename}")
                msg.attach(part)
            print(f"    [📎] Report attached: {filename}")

        # Send via SSL
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)

        # Save copy to Sent folder
        save_to_sent_folder(msg)

        return True

    except Exception as e:
        print(f"    [✗] Send failed: {e}")
        return False


def update_emailed_at(lead_id: int):
    """Update emailed_at timestamp in database."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE leads SET emailed_at = ? WHERE id = ?",
        (datetime.now().strftime("%Y-%m-%d %H:%M"), lead_id)
    )
    conn.commit()
    conn.close()


def run_sender():
    """Main email sending pipeline."""
    leads = get_approved_to_send()

    if not leads:
        print("[!] No approved leads to send emails to.")
        return

    print(f"[+] Sending emails to {len(leads)} leads...\n")

    sent   = 0
    failed = 0

    for i, lead in enumerate(leads, 1):
        name     = lead["name"]
        to_email = lead["email"]

        print(f"  [{i}/{len(leads)}] Sending to: {name}")

        # Check if email address exists
        if not to_email or to_email == "N/A" or to_email == "":
            print(f"    [!] No email address found for {name} — skipping")
            print(f"    [!] Website: {lead['website']} — manually find contact email")
            update_lead_status(lead["phone"], "no_email")
            failed += 1
            continue

        report_path = get_report_path(name)
        success     = send_email(
            to_email    = to_email,
            to_name     = name,
            subject     = lead["email_subject"],
            body        = lead["email_body"],
            report_path = report_path
        )

        if success:
            update_lead_status(lead["phone"], "emailed")
            update_emailed_at(lead["id"])
            print(f"    [✓] Email sent to {to_email}")
            sent += 1
        else:
            update_lead_status(lead["phone"], "email_failed")
            failed += 1

    print(f"\n[DONE] {sent} sent, {failed} failed/skipped")
    print(f"[+] Check database for final status.")


if __name__ == "__main__":
    run_sender()