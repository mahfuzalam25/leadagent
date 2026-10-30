import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "leads.db")


def get_connection():
    """Get a database connection."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    """Create the leads table if it doesn't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT,
            category         TEXT,
            address          TEXT,
            phone            TEXT UNIQUE,
            website          TEXT,
            rating           TEXT,
            reviews          TEXT,
            location         TEXT,
            status           TEXT DEFAULT 'new',
            email            TEXT,
            scraped_at       TEXT,
            audited_at       TEXT,
            emailed_at       TEXT,
            screenshot_path  TEXT,
            audit_data       TEXT,
            site_status      TEXT,
            email_subject    TEXT,
            email_body       TEXT,
            email_drafted_at TEXT,
            ai_score         INTEGER,
            ai_reason        TEXT
        )
    ''')

    conn.commit()
    conn.close()
    print(f"[✓] Database initialized at: {DB_PATH}")


def insert_lead(business: dict):
    """
    Insert a business into the database.
    Skips if phone already exists (duplicate prevention).
    """
    conn   = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO leads (name, category, address, phone, website, rating, reviews, location, scraped_at)
            VALUES (:name, :category, :address, :phone, :website, :rating, :reviews, :location, :scraped_at)
        ''', business)
        conn.commit()
        return True    # inserted successfully

    except sqlite3.IntegrityError:
        return False   # duplicate — phone already exists

    finally:
        conn.close()


def get_all_leads():
    """Return all leads from the database."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads")
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_leads_by_status(status: str):
    """Return leads filtered by status."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads WHERE status = ?", (status,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def update_lead_status(phone: str, status: str):
    """Update the status of a lead by phone number."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE leads SET status = ? WHERE phone = ?", (status, phone))
    conn.commit()
    conn.close()


def get_stats():
    """Print a quick summary of the database."""
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM leads")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT status, COUNT(*) FROM leads GROUP BY status")
    by_status = cursor.fetchall()

    conn.close()

    print(f"\n[DB STATS]")
    print(f"  Total leads : {total}")
    for status, count in by_status:
        print(f"  {status:12} : {count}")


if __name__ == "__main__":
    init_db()
    get_stats()