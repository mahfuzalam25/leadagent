import os
import sys
import json
import anthropic
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_connection, update_lead_status

# ── CONFIG ──────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
AGENCY_NAME       = "Crack404"
AGENCY_WEBSITE    = "https://crack404.pythonanywhere.com/"
AGENCY_EMAIL      = "crack404websol@gmail.com"
AGENCY_WHATSAPP   = "+8801310692122"
SENDER_NAME       = "Jyoti Prokash Anidya"
DRAFTS_DIR        = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "drafts"
)
# ────────────────────────────────────────────────────────


def get_report_ready_leads():
    """Get all leads with report_ready status."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, category, address, phone, website,
               rating, reviews, audit_data, screenshot_path, email
        FROM leads WHERE status = 'report_ready'
    """)
    rows = cursor.fetchall()
    conn.close()

    leads = []
    for row in rows:
        audit_data = {}
        try:
            audit_data = json.loads(row[8]) if row[8] else {}
        except:
            pass
        leads.append({
            "id":              row[0],
            "name":            row[1],
            "category":        row[2],
            "address":         row[3],
            "phone":           row[4],
            "website":         row[5],
            "rating":          row[6],
            "reviews":         row[7],
            "audit":           audit_data,
            "screenshot_path": row[9],
            "email":           row[10] or "",
        })
    return leads


def generate_email(lead: dict, client: anthropic.Anthropic) -> dict:
    """Use Claude to generate a personalized cold email."""
    audit  = lead["audit"]
    issues = audit.get("issues", [])
    score  = audit.get("score", 0)
    seo    = audit.get("seo", {})

    # Build issues summary for Claude
    issues_text = "\n".join([f"- {i}" for i in issues]) if issues else "- No major issues found"

    prompt = f"""
You are writing a cold outreach email on behalf of {AGENCY_NAME}, a web design agency.
The email is from {SENDER_NAME} at {AGENCY_NAME}.

We just audited this business's website and found real issues. Write a short, personalized, 
friendly cold email that:
1. Opens with something specific about their business (NOT generic)
2. Mentions 1-2 specific issues we found on their website
3. Hints at the revenue impact without being pushy
4. Offers a free consultation call
5. Ends with a clear single CTA

Business details:
- Name: {lead['name']}
- Category: {lead['category']}
- Location: {lead['address']}
- Website: {lead['website']}
- Google Rating: {lead['rating']} stars ({lead['reviews']} reviews)
- SEO Score: {score}/100

Issues found on their website:
{issues_text}

HTTPS: {'Yes' if seo.get('https') else 'No'}
Mobile Ready: {'Yes' if seo.get('mobile_viewport') else 'No'}

Rules:
- Keep it under 150 words
- Sound human, not robotic or salesy
- Be specific about their business
- Do NOT mention competitors
- Do NOT use the word "spam" or "cold email"
- Sign off as: {SENDER_NAME} | {AGENCY_NAME}
- Include website: {AGENCY_WEBSITE}
- Include WhatsApp: {AGENCY_WHATSAPP}
- Always end with this exact line on a new line: "If you'd prefer not to hear from us, just reply with 'unsubscribe' and we'll remove you immediately."

Return ONLY the email body — no subject line, no extra commentary.
"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )

    email_body = message.content[0].text.strip()

    # Generate subject line separately
    subject_prompt = f"""
Write a short, compelling email subject line for a cold outreach email to {lead['name']},
a {lead['category']}. We audited their website and found {len(issues)} issues.
SEO score: {score}/100.

Rules:
- Max 8 words
- Do not use clickbait or all caps
- Sound genuine and specific
- Do not start with "Re:" or "Fwd:"

Return ONLY the subject line, nothing else.
"""
    subject_msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=50,
        messages=[{"role": "user", "content": subject_prompt}]
    )
    subject = subject_msg.content[0].text.strip().strip('"')

    return {
        "subject":   subject,
        "body":      email_body,
        "to_name":   lead["name"],
        "to_email":  "",  # will be filled when we add email extraction
        "website":   lead["website"],
        "score":     score,
        "issues":    issues,
    }


def save_draft(lead: dict, email: dict) -> str:
    """Save email draft as a text file."""
    os.makedirs(DRAFTS_DIR, exist_ok=True)

    safe_name = lead["name"].replace(" ", "_").replace("/", "_").replace("|", "").strip("_")[:30]
    filename  = os.path.join(DRAFTS_DIR, f"{safe_name}_draft.txt")

    with open(filename, "w", encoding="utf-8", errors="replace") as f:
        f.write(f"TO      : {lead['name']}\n")
        f.write(f"WEBSITE : {lead['website']}\n")
        f.write(f"PHONE   : {lead['phone']}\n")
        f.write(f"SUBJECT : {email['subject']}\n")
        f.write(f"SCORE   : {email['score']}/100\n")
        f.write(f"ISSUES  : {', '.join(email['issues'])}\n")
        f.write(f"DATE    : {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("\n" + "="*60 + "\n\n")
        f.write(email["body"])
        f.write("\n\n" + "="*60 + "\n")

    return filename


def save_email_to_db(lead_id: int, email: dict):
    """Save email draft data to database."""
    conn   = get_connection()
    cursor = conn.cursor()

    for col in ["email_subject", "email_body", "email_drafted_at"]:
        try:
            cursor.execute(f"ALTER TABLE leads ADD COLUMN {col} TEXT")
            conn.commit()
        except:
            pass

    cursor.execute("""
        UPDATE leads SET
            email_subject     = ?,
            email_body        = ?,
            email_drafted_at  = ?
        WHERE id = ?
    """, (
        email["subject"],
        email["body"],
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        lead_id
    ))
    conn.commit()
    conn.close()


def run_email_composer():
    """Main email composition pipeline."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    leads  = get_report_ready_leads()

    if not leads:
        print("[!] No report-ready leads to compose emails for.")
        return

    print(f"[+] Composing emails for {len(leads)} leads...\n")

    for i, lead in enumerate(leads, 1):
        name = lead["name"]
        print(f"  [{i}/{len(leads)}] Composing email: {name}")

        try:
            email = generate_email(lead, client)
            print(f"    [✓] Subject: {email['subject']}")

            # Save draft file
            draft_path = save_draft(lead, email)
            print(f"    [✓] Draft saved: {draft_path}")

            # Save to database
            save_email_to_db(lead["id"], email)

            # Auto approve if email exists, otherwise flag for manual review
            if lead["audit"].get("email"):
                update_lead_status(lead["phone"], "approved_to_send")
            else:
                update_lead_status(lead["phone"], "email_drafted")

        except Exception as e:
            print(f"    [✗] Failed: {e}")

    print(f"\n[DONE] All drafts saved to: {DRAFTS_DIR}")
    print(f"[+] Run approval gate #2 to review before sending.")


if __name__ == "__main__":
    run_email_composer()