import os
import sys
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_leads_by_status, update_lead_status, get_connection

# ── CONFIG ──────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MIN_RATING        = 3.0
MAX_RATING        = 5.0
MIN_REVIEWS       = 5
MAX_REVIEWS       = 2000
# ────────────────────────────────────────────────────────


def get_new_leads():
    """Get all leads with status 'new' from the database."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, category, address, phone, website, rating, reviews, location
        FROM leads WHERE status = 'new'
    """)
    rows = cursor.fetchall()
    conn.close()

    leads = []
    for row in rows:
        leads.append({
            "id":       row[0],
            "name":     row[1],
            "category": row[2],
            "address":  row[3],
            "phone":    row[4],
            "website":  row[5],
            "rating":   row[6],
            "reviews":  row[7],
            "location": row[8],
        })
    return leads


def pre_filter(lead: dict) -> tuple[bool, str]:
    """
    Quick rule-based filter before sending to AI.
    Returns (keep, reason).
    """
    # Must have a website
    if not lead["website"] or lead["website"] == "N/A":
        return False, "no website"

    # Must have a phone
    if not lead["phone"] or lead["phone"] == "N/A":
        return False, "no phone"

    # Only reject very low ratings
    try:
        rating = float(lead["rating"])
        if rating < MIN_RATING:
            return False, f"rating too low ({rating})"
    except:
        pass  # let AI decide if rating is missing

    return True, "passed pre-filter"


def ai_score_lead(lead: dict, client: anthropic.Anthropic) -> dict:
    """
    Send lead to Claude Haiku for scoring and reasoning.
    Returns score (1-10) and reason.
    """
    prompt = f"""
You are a lead qualification agent for Crack404, a web design and development agency.
We help small businesses improve their websites.

Analyze this business and score it as a potential lead (1-10).
A high score means: small local business, likely has a poor or outdated website, would benefit from our services.
A low score means: large chain, franchise, or business unlikely to need our help.

Business details:
- Name: {lead['name']}
- Category: {lead['category']}
- Address: {lead['address']}
- Website: {lead['website']}
- Rating: {lead['rating']}
- Reviews: {lead['reviews']}
- Location: {lead['location']}

Respond ONLY with a JSON object like this:
{{"score": 7, "reason": "Small local cleaning service with basic website, good candidate", "shortlist": true}}

Rules:
- score 1-4: reject (chain, franchise, or poor fit)
- score 5-6: maybe (borderline)
- score 7-10: shortlist (strong candidate)
- shortlist must be true only if score >= 7
"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()

    try:
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        return result
    except:
        return {"score": 0, "reason": "AI parsing error", "shortlist": False}


def update_lead_score(lead_id: int, score: int, reason: str):
    """Save AI score and reason to the database."""
    conn   = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE leads ADD COLUMN ai_score INTEGER")
        cursor.execute("ALTER TABLE leads ADD COLUMN ai_reason TEXT")
        conn.commit()
    except:
        pass  # columns already exist

    cursor.execute("""
        UPDATE leads SET ai_score = ?, ai_reason = ? WHERE id = ?
    """, (score, reason, lead_id))
    conn.commit()
    conn.close()


def run_shortlister():
    """Main shortlisting pipeline."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    leads  = get_new_leads()

    if not leads:
        print("[!] No new leads to process.")
        return

    print(f"[+] Processing {len(leads)} new leads...\n")

    shortlisted = 0
    rejected    = 0

    for lead in leads:
        name = lead['name']

        # Step 1 — Rule-based pre-filter
        keep, reason = pre_filter(lead)
        if not keep:
            update_lead_status(lead["phone"], "rejected")
            update_lead_score(lead["id"], 0, reason)
            print(f"  [✗] {name} — REJECTED ({reason})")
            rejected += 1
            continue

        # Step 2 — AI scoring
        result = ai_score_lead(lead, client)
        score  = result.get("score", 0)
        reason = result.get("reason", "")
        keep   = result.get("shortlist", False)

        update_lead_score(lead["id"], score, reason)

        if keep:
            update_lead_status(lead["phone"], "approved")
            print(f"  [✓] {name} — SHORTLISTED (score: {score}) — {reason}")
            shortlisted += 1
        else:
            update_lead_status(lead["phone"], "rejected")
            print(f"  [✗] {name} — REJECTED (score: {score}) — {reason}")
            rejected += 1

    print(f"\n[DONE] {shortlisted} shortlisted, {rejected} rejected")


if __name__ == "__main__":
    run_shortlister()