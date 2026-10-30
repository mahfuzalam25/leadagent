import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_connection, update_lead_status

# ── CONFIG ──────────────────────────────────────────────
GATE_NAME  = "Human Approval Gate #2 — Email Draft Review"
DRAFTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "drafts"
)
REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "reports"
)
# ────────────────────────────────────────────────────────


def get_drafted_leads():
    """Get all leads with email_drafted status."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, category, address, phone, website,
               rating, reviews, email_subject, email_body, audit_data
        FROM leads WHERE status = 'email_drafted'
    """)
    rows = cursor.fetchall()
    conn.close()

    leads = []
    for row in rows:
        leads.append({
            "id":            row[0],
            "name":          row[1],
            "category":      row[2],
            "address":       row[3],
            "phone":         row[4],
            "website":       row[5],
            "rating":        row[6],
            "reviews":       row[7],
            "email_subject": row[8],
            "email_body":    row[9],
            "audit_data":    row[10],
        })
    return leads


def display_draft(index: int, total: int, lead: dict):
    """Display email draft for human review."""
    safe_name   = lead["name"].replace(" ", "_").replace("/", "_").replace("|", "").strip("_")[:30]
    draft_file  = os.path.join(DRAFTS_DIR,  f"{safe_name}_draft.txt")
    report_file = os.path.join(REPORTS_DIR, f"{safe_name}_report.pdf")

    print("\n" + "="*60)
    print(f"  EMAIL DRAFT {index} of {total}")
    print("="*60)
    print(f"  Business : {lead['name']}")
    print(f"  Website  : {lead['website']}")
    print(f"  Phone    : {lead['phone']}")
    print(f"  Rating   : {lead['rating']} ⭐ ({lead['reviews']} reviews)")
    print(f"  Subject  : {lead['email_subject']}")
    print("-"*60)
    print(f"\n{lead['email_body']}\n")
    print("-"*60)

    # Show file paths
    if os.path.exists(draft_file):
        print(f"  📄 Draft  : {draft_file}")
    if os.path.exists(report_file):
        print(f"  📊 Report : {report_file}")
    print("="*60)


def run_approval_gate2():
    """Interactive CLI for human review of email drafts."""
    leads = get_drafted_leads()

    if not leads:
        print("[!] No email drafts to review.")
        return

    print(f"\n{'='*60}")
    print(f"  {GATE_NAME}")
    print(f"  {len(leads)} drafts to review")
    print(f"{'='*60}")
    print("\n  Commands:")
    print("  [y] Approve — mark ready to send")
    print("  [n] Reject  — remove from pipeline")
    print("  [s] Skip    — review later")
    print("  [o] Open    — open PDF report in viewer")
    print("  [q] Quit    — stop reviewing\n")

    approved = 0
    rejected = 0
    skipped  = 0

    for i, lead in enumerate(leads, 1):
        display_draft(i, len(leads), lead)

        while True:
            choice = input("\n  Your decision [y/n/s/o/q]: ").strip().lower()

            if choice == "y":
                update_lead_status(lead["phone"], "approved_to_send")
                print(f"  ✅ Approved — {lead['name']}")
                approved += 1
                break

            elif choice == "n":
                update_lead_status(lead["phone"], "rejected")
                print(f"  ❌ Rejected — {lead['name']}")
                rejected += 1
                break

            elif choice == "s":
                print(f"  ⏭️  Skipped — {lead['name']}")
                skipped += 1
                break

            elif choice == "o":
                safe_name   = lead["name"].replace(" ", "_").replace("/", "_").replace("|", "").strip("_")[:30]
                report_file = os.path.join(REPORTS_DIR, f"{safe_name}_report.pdf")
                if os.path.exists(report_file):
                    os.startfile(report_file)
                    print(f"  📊 Opening report...")
                else:
                    print(f"  [!] Report not found: {report_file}")

            elif choice == "q":
                print("\n  [!] Quitting review session.")
                print(f"\n  Session summary:")
                print(f"  Approved : {approved}")
                print(f"  Rejected : {rejected}")
                print(f"  Skipped  : {skipped}")
                return

            else:
                print("  [!] Invalid input. Enter y, n, s, o, or q.")

    print(f"\n{'='*60}")
    print(f"  Review complete!")
    print(f"  Approved to send : {approved}")
    print(f"  Rejected         : {rejected}")
    print(f"  Skipped          : {skipped}")
    print(f"{'='*60}\n")
    print(f"  [+] Run emailer/send.py to send all approved emails.")


if __name__ == "__main__":
    run_approval_gate2()