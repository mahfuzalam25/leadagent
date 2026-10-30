import asyncio
import os
import sys
import time
import schedule
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper.maps_scraper      import scrape_google_maps, save_to_csv
from database.db               import init_db, insert_lead, get_stats
from shortlister.shortlist     import run_shortlister
from auditor.audit             import run_auditor
from reporter.report_generator import run_report_generator
from emailer.compose           import run_email_composer
from emailer.send              import run_sender

# ── CONFIG ──────────────────────────────────────────────
SEARCH_QUERIES = [
    ("restaurants", "London, UK"),
    ("restaurants", "Shoreditch, London"),
    ("restaurants", "Canary Wharf, London"),
    ("restaurants", "Camden, London"),
    ("restaurants", "Brixton, London"),
    ("cafe", "London, UK"),
    ("cafe", "Notting Hill, London"),
    ("restaurant", "Greenwich, London"),
    ("restaurant", "Hackney, London"),
    ("restaurant", "Islington, London"),
]
MAX_RESULTS  = 30
RUN_TIME     = "09:00"  # run daily at 9am
# ────────────────────────────────────────────────────────


async def scrape_phase():
    """Phase 1 — Scrape Google Maps and store in DB."""
    print("\n" + "="*60)
    print("  PHASE 1 — Scraping Google Maps")
    print("="*60)

    init_db()

    for query, location in SEARCH_QUERIES:
        print(f"\n[+] Scraping: {query} in {location}")
        data = scrape_google_maps(query, location, MAX_RESULTS)

        inserted = 0
        skipped  = 0
        for business in data:
            if insert_lead(business):
                inserted += 1
            else:
                skipped += 1

        print(f"[✓] {inserted} new, {skipped} duplicates skipped")

    get_stats()


def run_pipeline():
    """Run the full agent pipeline."""
    print("\n" + "="*60)
    print(f"  EXFORGE AGENT — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*60)

    # ── Phase 1: Scrape ──
    asyncio.run(scrape_phase())

    # ── Phase 2: AI Shortlist ──
    print("\n" + "="*60)
    print("  PHASE 2 — AI Shortlisting")
    print("="*60)
    run_shortlister()

    # ── Phase 3: Website Audit ──
    print("\n" + "="*60)
    print("  PHASE 3 — Website Auditor")
    print("="*60)
    asyncio.run(run_auditor())

    # ── Phase 4: Report Generation ──
    print("\n" + "="*60)
    print("  PHASE 4 — Report Generator")
    print("="*60)
    run_report_generator()

    # ── Phase 5: Email Composition ──
    print("\n" + "="*60)
    print("  PHASE 5 — Email Composer")
    print("="*60)
    run_email_composer()

    # ── Phase 6: Send Emails ──
    print("\n" + "="*60)
    print("  PHASE 6 — Sending Emails")
    print("="*60)
    run_sender()

    print("\n" + "="*60)
    print(f"  CYCLE COMPLETE — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*60)
    get_stats()


def get_emails_sent_today() -> int:
    """Return how many emails were sent today."""
    import sqlite3
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "leads.db")
    
    # Ensure the data directory exists before trying to connect
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn    = sqlite3.connect(db_path)
    cursor  = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM leads
            WHERE status = 'emailed'
            AND date(emailed_at) = date('now')
        """)
        count = cursor.fetchone()[0]
    except sqlite3.OperationalError:
        # If the table doesn't exist yet, 0 emails have been sent
        count = 0
        
    conn.close()
    return count


def run_until_target(target: int = 30):
    """Keep running pipeline cycles until target emails sent today."""
    print(f"\n[+] Target: {target} emails today")

    max_cycles = 10  # safety limit
    cycle      = 0

    while cycle < max_cycles:
        sent_today = get_emails_sent_today()
        print(f"\n[+] Emails sent today: {sent_today}/{target}")

        if sent_today >= target:
            print(f"[✓] Target reached — {sent_today} emails sent today!")
            break

        remaining = target - sent_today
        print(f"[+] Need {remaining} more — starting cycle {cycle + 1}...")

        run_pipeline()
        cycle += 1

        sent_today = get_emails_sent_today()
        if sent_today >= target:
            print(f"\n[✓] Target reached — {sent_today} emails sent today!")
            break

        print(f"\n[+] Cycle {cycle} done. Sent today: {sent_today}/{target}")
        print(f"[+] Waiting 60 seconds before next cycle...")
        time.sleep(60)

    if cycle >= max_cycles:
        print(f"\n[!] Max cycles ({max_cycles}) reached. Sent today: {get_emails_sent_today()}")

    get_stats()


def start_scheduler():
    """Schedule the pipeline to run daily."""
    print(f"[+] Scheduler started — running daily at {RUN_TIME}")
    print(f"[+] Press Ctrl+C to stop\n")

    schedule.every().day.at(RUN_TIME).do(run_pipeline)

    # Also run immediately on start
    print("[+] Running pipeline now...\n")
    run_pipeline()

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ExForge Lead Gen Agent")
    parser.add_argument("--now", action="store_true", help="Run pipeline once immediately")
    parser.add_argument("--target", type=int, default=30, help="Target emails per day (default: 30)")
    parser.add_argument("--schedule", action="store_true", help="Run on daily schedule")
    parser.add_argument("--scrape", action="store_true", help="Run scraper only")
    parser.add_argument("--shortlist", action="store_true", help="Run shortlister only")
    parser.add_argument("--audit", action="store_true", help="Run auditor only")
    parser.add_argument("--report", action="store_true", help="Run report generator only")
    parser.add_argument("--compose", action="store_true", help="Run email composer only")
    parser.add_argument("--send", action="store_true", help="Run email sender only")
    parser.add_argument("--sent", action="store_true", help="Show all sent emails")
    args = parser.parse_args()

    if args.schedule:
        start_scheduler()
    elif args.now:
        run_until_target(args.target)
    elif args.scrape:
        asyncio.run(scrape_phase())
    elif args.shortlist:
        run_shortlister()
    elif args.audit:
        asyncio.run(run_auditor())
    elif args.report:
        run_report_generator()
    elif args.compose:
        run_email_composer()
    elif args.send:
        run_sender()
    elif args.sent:
        import sqlite3
        conn   = sqlite3.connect('data/leads.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name, email, website, emailed_at FROM leads WHERE status='emailed'")
        rows   = cursor.fetchall()
        print(f"\n{'='*60}")
        print(f"  EMAILS SENT — {len(rows)} total")
        print(f"{'='*60}")
        for row in rows:
            print(f"  Date    : {row[3]}")
            print(f"  Name    : {row[0]}")
            print(f"  Email   : {row[1]}")
            print(f"  Website : {row[2]}")
            print()
        conn.close()
    else:
        print("ExForge Lead Gen Agent")
        print("\nUsage:")
        print("  python main.py --now          # run full pipeline once")
        print("  python main.py --schedule     # run daily at 9am")
        print("  python main.py --scrape       # scrape only")
        print("  python main.py --shortlist    # shortlist only")
        print("  python main.py --audit        # audit only")
        print("  python main.py --report       # report only")
        print("  python main.py --compose      # compose only")
        print("  python main.py --send         # send only")
        print("  python main.py --sent         # show all sent emails")