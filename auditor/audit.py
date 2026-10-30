import os
import sys
import re
import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_connection, update_lead_status

# ── CONFIG ──────────────────────────────────────────────
SCREENSHOTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "screenshots"
)
REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "reports"
)
# ────────────────────────────────────────────────────────


def get_approved_leads():
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, category, address, phone, website, rating, reviews
        FROM leads WHERE status = 'approved'
    """)
    rows = cursor.fetchall()
    conn.close()

    leads = []
    for row in rows:
        leads.append({
            "id": row[0], "name": row[1], "category": row[2],
            "address": row[3], "phone": row[4], "website": row[5],
            "rating": row[6], "reviews": row[7],
        })
    return leads


def save_audit_result(lead_id: int, audit: dict):
    conn   = get_connection()
    cursor = conn.cursor()

    for col in ["screenshot_path", "audit_data", "site_status", "audited_at", "email"]:
        try:
            cursor.execute(f"ALTER TABLE leads ADD COLUMN {col} TEXT")
            conn.commit()
        except:
            pass

    cursor.execute("""
        UPDATE leads SET
            screenshot_path = ?,
            audit_data      = ?,
            site_status     = ?,
            audited_at      = ?,
            email           = ?
        WHERE id = ?
    """, (
        audit.get("screenshot_path"),
        json.dumps(audit),
        audit.get("site_status"),
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        audit.get("email", ""),
        lead_id
    ))
    conn.commit()
    conn.close()


async def extract_email(page, url: str) -> str:
    """Try to extract email from website."""
    import urllib.parse

    def clean_email(raw: str) -> str:
        return urllib.parse.unquote(raw).strip().lower()

    try:
        # Check current page for mailto links
        emails = await page.eval_on_selector_all(
            'a[href^="mailto:"]',
            "els => els.map(e => e.href.replace('mailto:', '').split('?')[0].trim())"
        )
        if emails:
            return clean_email(emails[0])

        # Try contact pages
        contact_urls = [
            url.rstrip("/") + "/contact",
            url.rstrip("/") + "/contact-us",
            url.rstrip("/") + "/about",
        ]
        for contact_url in contact_urls:
            try:
                await page.goto(contact_url, wait_until="domcontentloaded", timeout=10000)
                await page.wait_for_timeout(1000)
                emails = await page.eval_on_selector_all(
                    'a[href^="mailto:"]',
                    "els => els.map(e => e.href.replace('mailto:', '').split('?')[0].trim())"
                )
                if emails:
                    return clean_email(emails[0])
            except:
                continue

        # Scan body text for email pattern
        try:
            body_text = await page.locator("body").inner_text(timeout=3000)
            matches   = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', body_text)
            if matches:
                valid = [m for m in matches if not any(
                    x in m.lower() for x in ["@2x", ".png", ".jpg", "example", "sentry", "wix"]
                )]
                if valid:
                    return clean_email(valid[0])
        except:
            pass

    except:
        pass

    return ""


async def audit_website(page, lead: dict) -> dict:
    url   = lead["website"]
    name  = lead["name"]
    audit = {
        "url": url, "site_status": "unknown",
        "screenshot_path": None, "email": "",
        "seo": {}, "issues": [], "score": 0,
    }

    # ── Step 1: Visit the site ──
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)

        if response and response.status >= 400:
            audit["site_status"] = f"error_{response.status}"
            audit["issues"].append(f"Site returned HTTP {response.status}")
            return audit

        audit["site_status"] = "online"

    except Exception as e:
        audit["site_status"] = "offline"
        audit["issues"].append(f"Site unreachable: {str(e)[:100]}")
        return audit

    # ── Step 2: Take screenshot ──
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    safe_name       = name.replace(" ", "_").replace("/", "_")[:30]
    screenshot_path = os.path.join(SCREENSHOTS_DIR, f"{safe_name}.png")

    try:
        await page.screenshot(path=screenshot_path, full_page=False)
        audit["screenshot_path"] = screenshot_path
        print(f"    [📸] Screenshot saved")
    except Exception as e:
        audit["issues"].append(f"Screenshot failed: {str(e)[:100]}")

    # ── Step 3: Extract email ──
    email = await extract_email(page, url)
    audit["email"] = email
    if email:
        print(f"    [📧] Email found: {email}")
    else:
        print(f"    [!] No email found")

    # ── Step 4: Go back to main URL for SEO checks ──
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(1000)
    except:
        pass

    # ── Step 5: SEO checks ──
    seo    = {}
    issues = []
    score  = 100

    try:
        title = await page.title()
        seo["title"] = title
        if not title:
            issues.append("Missing page title")
            score -= 15
        elif len(title) > 60:
            issues.append(f"Title too long ({len(title)} chars, ideal < 60)")
            score -= 5
    except:
        issues.append("Could not read page title")
        score -= 10

    try:
        meta_desc = await page.get_attribute('meta[name="description"]', "content")
        seo["meta_description"] = meta_desc
        if not meta_desc:
            issues.append("Missing meta description")
            score -= 15
        elif len(meta_desc) > 160:
            issues.append(f"Meta description too long ({len(meta_desc)} chars)")
            score -= 5
    except:
        issues.append("Missing meta description")
        score -= 15

    try:
        h1 = await page.locator("h1").first.inner_text(timeout=3000)
        seo["h1"] = h1
        if not h1:
            issues.append("Missing H1 tag")
            score -= 10
    except:
        issues.append("Missing H1 tag")
        score -= 10

    try:
        imgs_without_alt = await page.eval_on_selector_all(
            "img:not([alt])", "els => els.length"
        )
        seo["images_missing_alt"] = imgs_without_alt
        if imgs_without_alt > 0:
            issues.append(f"{imgs_without_alt} images missing alt text")
            score -= min(imgs_without_alt * 3, 15)
    except:
        pass

    if not url.startswith("https://"):
        issues.append("Site not using HTTPS")
        score -= 20
    else:
        seo["https"] = True

    try:
        viewport_meta = await page.get_attribute('meta[name="viewport"]', "content")
        seo["mobile_viewport"] = viewport_meta
        if not viewport_meta:
            issues.append("Missing mobile viewport meta tag")
            score -= 15
    except:
        issues.append("Missing mobile viewport meta tag")
        score -= 15

    try:
        body_text = await page.locator("body").inner_text(timeout=3000)
        if "phone" not in body_text.lower() and "contact" not in body_text.lower():
            issues.append("No visible contact information found")
            score -= 10
    except:
        pass

    audit["seo"]    = seo
    audit["issues"] = issues
    audit["score"]  = max(score, 0)

    return audit


async def run_auditor():
    leads = get_approved_leads()

    if not leads:
        print("[!] No approved leads to audit.")
        return

    print(f"[+] Auditing {len(leads)} approved websites...\n")
    os.makedirs(REPORTS_DIR, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page    = await browser.new_page(viewport={"width": 1280, "height": 800})

        for i, lead in enumerate(leads, 1):
            print(f"  [{i}/{len(leads)}] Auditing: {lead['name']}")
            print(f"    URL: {lead['website']}")

            audit = await audit_website(page, lead)
            save_audit_result(lead["id"], audit)

            if audit["site_status"] == "online":
                update_lead_status(lead["phone"], "audited")
                print(f"    [✓] Score: {audit['score']}/100")
                print(f"    [!] Issues found: {len(audit['issues'])}")
                for issue in audit["issues"]:
                    print(f"        • {issue}")
            else:
                update_lead_status(lead["phone"], "site_error")
                print(f"    [✗] Site status: {audit['site_status']}")
            print()

        await browser.close()

    print("[DONE] All websites audited.")
    print(f"[+] Screenshots saved to: {SCREENSHOTS_DIR}")


if __name__ == "__main__":
    asyncio.run(run_auditor())