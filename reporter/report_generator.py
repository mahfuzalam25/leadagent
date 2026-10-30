import os
import sys
import json
import anthropic
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import urlparse
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.graphics.shapes import Drawing, Rect, String, Group
from reportlab.graphics import renderPDF

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_connection, update_lead_status

# ── CONFIG ──────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
REPORTS_DIR       = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "reports"
)
AGENCY_NAME      = "Crack404"
AGENCY_WEBSITE   = "https://crack404.pythonanywhere.com/"
AGENCY_CONTACT   = "https://crack404.pythonanywhere.com/contact"
AGENCY_EMAIL     = "crack404websol@gmail.com"
AGENCY_WHATSAPP  = "https://wa.me/8801310692122"
WHATSAPP_NUMBER  = "+880 1310-692122"
# ────────────────────────────────────────────────────────

# ── COLORS ──────────────────────────────────────────────
C_DARK     = colors.HexColor("#1A1A2E")
C_PRIMARY  = colors.HexColor("#16213E")
C_ACCENT   = colors.HexColor("#0F3460")
C_GREEN    = colors.HexColor("#27AE60")
C_RED      = colors.HexColor("#E74C3C")
C_ORANGE   = colors.HexColor("#E67E22")
C_YELLOW   = colors.HexColor("#F39C12")
C_LIGHT    = colors.HexColor("#F8F9FA")
C_BORDER   = colors.HexColor("#DEE2E6")
C_MUTED    = colors.HexColor("#6C757D")
C_WHITE    = colors.white
# ────────────────────────────────────────────────────────


def get_audited_leads():
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, category, address, phone, website,
               rating, reviews, audit_data, screenshot_path
        FROM leads WHERE status = 'audited'
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
        })
    return leads


def clean_website_url(url: str) -> str:
    """Strip URL to just domain e.g. https://example.com."""
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    except:
        return url


def get_score_grade(score: int) -> tuple:
    if score >= 90:
        return "A", C_GREEN
    elif score >= 75:
        return "B", C_YELLOW
    elif score >= 60:
        return "C", C_ORANGE
    elif score >= 40:
        return "D", C_RED
    else:
        return "F", colors.HexColor("#C0392B")


def generate_ai_summary(lead: dict, client: anthropic.Anthropic) -> str:
    audit  = lead["audit"]
    issues = audit.get("issues", [])
    score  = audit.get("score", 0)

    prompt = f"""
You are writing a professional website audit report for {lead['name']}, a {lead['category']} in {lead['address']}.

Website: {lead['website']}
SEO Score: {score}/100
Issues found: {', '.join(issues) if issues else 'None'}
Rating: {lead['rating']} stars ({lead['reviews']} reviews)

Write a SHORT 3-sentence personalized summary for this business owner explaining:
1. What we found about their website
2. How these issues are costing them customers
3. How Crack404 can help fix it

Be specific, friendly, and professional. Under 100 words.
"""
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()


def generate_revenue_impact(score: int, reviews: str) -> str:
    try:
        review_count = int(reviews)
    except:
        review_count = 50

    if score < 60:
        lost_pct  = "40–60%"
        est_leads = review_count // 3
    elif score < 80:
        lost_pct  = "20–40%"
        est_leads = review_count // 5
    else:
        lost_pct  = "10–20%"
        est_leads = review_count // 10

    return (f"Websites with your current score lose approximately {lost_pct} of potential visitors "
            f"before they make contact. Based on your {reviews} reviews, we estimate you may be "
            f"missing {est_leads}+ potential customers per month.")


def build_score_chart(score: int, reviews: str) -> Drawing:
    """Simple horizontal bar showing SEO score vs perfect score."""
    try:
        review_count = int(reviews)
    except:
        review_count = 50

    missed  = review_count // 3 if score < 60 else review_count // 5 if score < 80 else review_count // 10
    reached = review_count - missed

    drawing = Drawing(480, 120)

    # ── SEO Score bar ──
    drawing.add(String(10, 100, "SEO Score", fontSize=9, fillColor=C_DARK))
    drawing.add(String(10, 86,  f"{score}/100", fontSize=8, fillColor=C_MUTED))
    # background
    drawing.add(Rect(120, 90, 320, 16, fillColor=C_BORDER, strokeColor=None))
    # score fill
    bar_w = int((score / 100) * 320)
    bar_color = C_GREEN if score >= 80 else C_ORANGE if score >= 60 else C_RED
    drawing.add(Rect(120, 90, bar_w, 16, fillColor=bar_color, strokeColor=None))
    drawing.add(String(445, 96, f"{score}%", fontSize=9, fillColor=C_DARK))

    # ── Customers Reached bar ──
    drawing.add(String(10, 58, "Customers Reached", fontSize=9, fillColor=C_DARK))
    drawing.add(String(10, 44, f"{reached} of {review_count}", fontSize=8, fillColor=C_MUTED))
    # background
    drawing.add(Rect(120, 48, 320, 16, fillColor=C_BORDER, strokeColor=None))
    # reached fill
    reach_pct = int((reached / max(review_count, 1)) * 320)
    drawing.add(Rect(120, 48, reach_pct, 16, fillColor=C_GREEN, strokeColor=None))
    # missed fill
    drawing.add(Rect(120 + reach_pct, 48, 320 - reach_pct, 16, fillColor=C_RED, strokeColor=None))
    drawing.add(String(445, 54, f"{reached}", fontSize=9, fillColor=C_DARK))

    # ── Legend ──
    drawing.add(Rect(10,  18, 12, 10, fillColor=C_GREEN, strokeColor=None))
    drawing.add(String(26, 20, "Reached / Good", fontSize=8, fillColor=C_DARK))
    drawing.add(Rect(160, 18, 12, 10, fillColor=C_RED,   strokeColor=None))
    drawing.add(String(176, 20, "Missed / Issues", fontSize=8, fillColor=C_DARK))
    drawing.add(Rect(310, 18, 12, 10, fillColor=C_ORANGE, strokeColor=None))
    drawing.add(String(326, 20, "Needs Improvement", fontSize=8, fillColor=C_DARK))

    return drawing


def create_pdf_report(lead: dict, summary: str) -> str:
    os.makedirs(REPORTS_DIR, exist_ok=True)

    safe_name = lead["name"].replace(" ", "_").replace("/", "_").replace("|", "").strip("_")[:30]
    filename  = os.path.join(REPORTS_DIR, f"{safe_name}_report.pdf")

    doc   = SimpleDocTemplate(
        filename, pagesize=letter,
        rightMargin=0.75*inch, leftMargin=0.75*inch,
        topMargin=0.6*inch,    bottomMargin=0.6*inch
    )
    story = []

    # ── STYLES ──
    def style(name, **kwargs):
        return ParagraphStyle(name, **kwargs)

    s_title    = style("title",   fontSize=26, fontName="Helvetica-Bold",
                       textColor=C_PRIMARY,  alignment=TA_CENTER, spaceAfter=4)
    s_sub      = style("sub",     fontSize=10, fontName="Helvetica",
                       textColor=C_MUTED,    alignment=TA_CENTER, spaceAfter=2)
    s_section  = style("section", fontSize=13, fontName="Helvetica-Bold",
                       textColor=C_PRIMARY,  spaceBefore=10, spaceAfter=6)
    s_body     = style("body",    fontSize=10, fontName="Helvetica",
                       textColor=C_PRIMARY,  spaceAfter=4, leading=15)
    s_good     = style("good",    fontSize=10, fontName="Helvetica",
                       textColor=C_GREEN,    spaceAfter=3)
    s_bad      = style("bad",     fontSize=10, fontName="Helvetica",
                       textColor=C_RED,      spaceAfter=3)
    s_impact   = style("impact",  fontSize=10, fontName="Helvetica",
                       textColor=colors.HexColor("#856404"),
                       backColor=colors.HexColor("#FFF3CD"),
                       borderPad=10, spaceAfter=6, leading=15)
    s_footer   = style("footer",  fontSize=9,  fontName="Helvetica",
                       textColor=C_MUTED,    alignment=TA_CENTER, spaceAfter=2)
    s_link     = style("link",    fontSize=9,  fontName="Helvetica",
                       textColor=C_ACCENT,   alignment=TA_CENTER, spaceAfter=2)

    # ── HEADER ──
    story.append(Spacer(1, 0.1*inch))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("Website Audit Report", s_title))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(
        f'Prepared by <a href="{AGENCY_CONTACT}" color="#0F3460"><u><b>{AGENCY_NAME}</b></u></a>',
        s_sub
    ))
    story.append(Spacer(1, 0.05 * inch))
    story.append(Paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}", s_sub))
    story.append(Spacer(1, 0.2 * inch))
    story.append(HRFlowable(width="100%", thickness=1.5, color=C_ACCENT))
    story.append(Spacer(1, 0.25 * inch))

    # ── BUSINESS OVERVIEW ──
    story.append(Paragraph("Business Overview", s_section))
    clean_url = clean_website_url(lead["website"])
    info_data = [
        ["Business Name", lead["name"]],
        ["Category",      lead["category"]],
        ["Address",       lead["address"]],
        ["Phone",         lead["phone"]],
        ["Website",       clean_url],
        ["Google Rating", f"{lead['rating']} ⭐  ({lead['reviews']} reviews)"],
    ]
    info_table = Table(info_data, colWidths=[1.6*inch, 5.4*inch])
    info_table.setStyle(TableStyle([
        ("FONTNAME",       (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME",       (0, 0), (0, -1),  "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, -1), 10),
        ("TEXTCOLOR",      (0, 0), (0, -1),  C_MUTED),
        ("TEXTCOLOR",      (1, 0), (1, -1),  C_PRIMARY),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [C_LIGHT, C_WHITE]),
        ("GRID",           (0, 0), (-1, -1), 0.5, C_BORDER),
        ("PADDING",        (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 0), (-1, 0),  [C_ACCENT]),
        ("TEXTCOLOR",      (0, 0), (-1, 0),  C_WHITE),
        ("FONTNAME",       (0, 0), (-1, 0),  "Helvetica-Bold"),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.25*inch))

    # ── SCORE CARD ──
    audit        = lead["audit"]
    score        = audit.get("score", 0)
    grade, gcol  = get_score_grade(score)
    seo          = audit.get("seo", {})

    story.append(Paragraph("Website Score Card", s_section))

    def check(val):
        return ("✓", C_GREEN) if val else ("✗", C_RED)

    https_sym,    https_col    = check(seo.get("https"))
    mobile_sym,   mobile_col   = check(seo.get("mobile_viewport"))
    title_sym,    title_col    = check(seo.get("title"))
    meta_sym,     meta_col     = check(seo.get("meta_description"))

    score_color = C_GREEN if score >= 80 else C_ORANGE if score >= 60 else C_RED

    score_data = [
        ["Metric",        "Status", "Metric",        "Status"],
        ["Overall Score", f"{score}/100", "Grade",  grade],
        ["HTTPS Secure",  https_sym,  "Mobile Ready", mobile_sym],
        ["Title Tag",     title_sym,  "Meta Desc",    meta_sym],
    ]
    score_table = Table(score_data, colWidths=[1.9*inch, 1.6*inch, 1.9*inch, 1.6*inch])
    score_table.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("BACKGROUND",  (0, 0), (-1, 0),  C_PRIMARY),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  C_WHITE),
        ("TEXTCOLOR",   (1, 1), (1, 1),   score_color),
        ("FONTNAME",    (1, 1), (1, 1),   "Helvetica-Bold"),
        ("FONTSIZE",    (1, 1), (1, 1),   13),
        ("TEXTCOLOR",   (3, 1), (3, 1),   gcol),
        ("FONTNAME",    (3, 1), (3, 1),   "Helvetica-Bold"),
        ("FONTSIZE",    (3, 1), (3, 1),   13),
        ("TEXTCOLOR",   (1, 2), (1, 2),   https_col),
        ("TEXTCOLOR",   (3, 2), (3, 2),   mobile_col),
        ("TEXTCOLOR",   (1, 3), (1, 3),   title_col),
        ("TEXTCOLOR",   (3, 3), (3, 3),   meta_col),
        ("FONTNAME",    (1, 2), (1, 3),   "Helvetica-Bold"),
        ("FONTNAME",    (3, 2), (3, 3),   "Helvetica-Bold"),
        ("FONTSIZE",    (1, 2), (3, 3),   12),
        ("GRID",        (0, 0), (-1, -1), 0.5, C_BORDER),
        ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_LIGHT, C_WHITE]),
        ("PADDING",     (0, 0), (-1, -1), 10),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.25*inch))

    # ── CHART ──
    story.append(Paragraph("Performance Overview", s_section))
    chart = build_score_chart(score, lead["reviews"])
    story.append(chart)
    story.append(Spacer(1, 0.2*inch))

    # ── ISSUES FOUND ──
    issues = audit.get("issues", [])
    story.append(Paragraph("Issues Found", s_section))
    if issues:
        for issue in issues:
            story.append(Paragraph(f"✗  {issue}", s_bad))
    else:
        story.append(Paragraph("✓  No major issues found — great job!", s_good))
    story.append(Spacer(1, 0.1*inch))

    # ── WHAT'S WORKING ──
    good_items = []
    if seo.get("https"):
        good_items.append("Site uses HTTPS — secure connection")
    if seo.get("mobile_viewport"):
        good_items.append("Mobile viewport is configured")
    if seo.get("title"):
        good_items.append("Page title is present")
    if seo.get("meta_description"):
        good_items.append("Meta description is present")
    if seo.get("h1"):
        good_items.append("H1 heading tag is present")

    if good_items:
        story.append(Paragraph("What's Working Well", s_section))
        for item in good_items:
            story.append(Paragraph(f"✓  {item}", s_good))
        story.append(Spacer(1, 0.1*inch))

    # ── REVENUE IMPACT ──
    story.append(Paragraph("Revenue Impact Estimate", s_section))
    impact = generate_revenue_impact(score, lead["reviews"])
    story.append(Paragraph(impact, s_impact))
    story.append(Spacer(1, 0.1*inch))

    # ── AI SUMMARY ──
    story.append(Paragraph("Our Analysis", s_section))
    story.append(Paragraph(summary, s_body))
    story.append(Spacer(1, 0.2*inch))

    # ── SCREENSHOT ──
    screenshot = lead.get("screenshot_path")
    if screenshot and os.path.exists(screenshot):
        story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
        story.append(Spacer(1, 0.15*inch))
        story.append(Paragraph("Current Website Screenshot", s_section))
        story.append(Spacer(1, 0.05*inch))
        img = Image(screenshot, width=6.5*inch, height=3.5*inch)
        story.append(img)
        story.append(Spacer(1, 0.2*inch))

    # ── CONTACT / CTA ──
    story.append(HRFlowable(width="100%", thickness=1.5, color=C_ACCENT))
    story.append(Spacer(1, 0.15*inch))

    cta_data = [[
        Paragraph(
            f'<a href="{AGENCY_CONTACT}" color="#0F3460"><u>Visit {AGENCY_NAME}</u></a>',
            style("cta1", fontSize=9, fontName="Helvetica", textColor=C_ACCENT, alignment=TA_CENTER)
        ),
        Paragraph(
            f'<a href="mailto:{AGENCY_EMAIL}" color="#0F3460"><u>{AGENCY_EMAIL}</u></a>',
            style("cta2", fontSize=9, fontName="Helvetica", textColor=C_ACCENT, alignment=TA_CENTER)
        ),
        Paragraph(
            f'<a href="{AGENCY_WHATSAPP}" color="#27AE60"><u>💬 WhatsApp {WHATSAPP_NUMBER}</u></a>',
            style("cta3", fontSize=9, fontName="Helvetica", textColor=C_GREEN, alignment=TA_CENTER)
        ),
    ]]
    cta_table = Table(cta_data, colWidths=[2.3*inch, 2.3*inch, 2.4*inch])
    cta_table.setStyle(TableStyle([
        ("ALIGN",   (0, 0), (-1, -1), "CENTER"),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("GRID",    (0, 0), (-1, -1), 0.5, C_BORDER),
        ("BACKGROUND", (0, 0), (-1, -1), C_LIGHT),
    ]))
    story.append(cta_table)
    story.append(Spacer(1, 0.1*inch))

    story.append(Paragraph(
        f'This report was prepared by <b>{AGENCY_NAME}</b> | '
        f'<a href="mailto:{AGENCY_EMAIL}" color="#0F3460"><u>{AGENCY_EMAIL}</u></a> | '
        f'<a href="{AGENCY_WEBSITE}" color="#0F3460"><u>https://crack404.pythonanywhere.com/</u></a>',
        s_footer
    ))
    story.append(Paragraph(
        "We specialize in helping local businesses improve their online presence.",
        s_footer
    ))

    doc.build(story)
    return filename


def run_report_generator():
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    leads  = get_audited_leads()

    if not leads:
        print("[!] No audited leads to generate reports for.")
        return

    print(f"[+] Generating reports for {len(leads)} audited leads...\n")

    for i, lead in enumerate(leads, 1):
        name = lead["name"]
        print(f"  [{i}/{len(leads)}] Generating report: {name}")

        try:
            summary = generate_ai_summary(lead, client)
            print(f"    [✓] AI summary generated")
        except Exception as e:
            summary = f"Our audit found several areas where {name}'s website could be improved."
            print(f"    [!] AI summary fallback: {e}")

        try:
            pdf_path = create_pdf_report(lead, summary)
            print(f"    [✓] Report saved: {pdf_path}")
            update_lead_status(lead["phone"], "report_ready")
        except Exception as e:
            print(f"    [✗] Report failed: {e}")

    print(f"\n[DONE] Reports saved to: {REPORTS_DIR}")


if __name__ == "__main__":
    run_report_generator()