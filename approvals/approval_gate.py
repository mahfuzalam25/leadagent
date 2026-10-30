import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_connection, update_lead_status

# ── CONFIG ──────────────────────────────────────────────
GATE_NAME = "Human Approval Gate #1 — Shortlist Review"
# ────────────────────────────────────────────────────────


def get_shortlisted_leads():
    """Get all shortlisted leads from the database."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, category, address, phone, website, rating, reviews, ai_score, ai_reason
        FROM leads WHERE status = 'shortlisted'
    """)
    rows = cursor.fetchall()
    conn.close()

    leads = []
    for row in rows:
        leads.append({
            "id":        row[0],
            "name":      row[1],
            "category":  row[2],
            "address":   row[3],
            "phone":     row[4],
            "website":   row[5],
            "rating":    row[6],
            "reviews":   row[7],
            "ai_score":  row[8],
            "ai_reason": row[9],
        })
    return leads


def display_lead(index: int, total: int, lead: dict):
    """Display a single lead clearly for human review."""
    print("\n" + "="*60)
    print(f"  LEAD {index} of {total}")
    print("="*60)
    print(f"  Name      : {lead['name']}")
    print(f"  Category  : {lead['category']}")
    print(f"  Address   : {lead['address']}")
    print(f"  Phone     : {lead['phone']}")
    print(f"  Website   : {lead['website']}")
    print(f"  Rating    : {lead['rating']} ⭐ ({lead['reviews']} reviews)")
    print(f"  AI Score  : {lead['ai_score']}/10")
    print(f"  AI Reason : {lead['ai_reason']}")
    print("="*60)


def run_approval_gate():
    """Interactive CLI for human review of shortlisted leads."""
    leads = get_shortlisted_leads()

    if not leads:
        print("[!] No shortlisted leads to review.")
        return

    print(f"\n{'='*60}")
    print(f"  {GATE_NAME}")
    print(f"  {len(leads)} leads to review")
    print(f"{'='*60}")
    print("\n  Commands:")
    print("  [y] Approve — send to website audit")
    print("  [n] Reject  — remove from pipeline")
    print("  [s] Skip    — review later")
    print("  [q] Quit    — stop reviewing\n")

    approved = 0
    rejected = 0
    skipped  = 0

    for i, lead in enumerate(leads, 1):
        display_lead(i, len(leads), lead)

        while True:
            choice = input("\n  Your decision [y/n/s/q]: ").strip().lower()

            if choice == "y":
                update_lead_status(lead["phone"], "approved")
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

            elif choice == "q":
                print("\n  [!] Quitting review session.")
                print(f"\n  Session summary:")
                print(f"  Approved : {approved}")
                print(f"  Rejected : {rejected}")
                print(f"  Skipped  : {skipped}")
                return

            else:
                print("  [!] Invalid input. Enter y, n, s, or q.")

    print(f"\n{'='*60}")
    print(f"  Review complete!")
    print(f"  Approved : {approved}")
    print(f"  Rejected : {rejected}")
    print(f"  Skipped  : {skipped}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run_approval_gate()