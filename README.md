
<div align="center">

<pre align="center">
███████╗██╗  ██╗███████╗ ██████╗ ██████╗  ██████╗ ███████╗
██╔════╝╚██╗██╔╝██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝
█████╗   ╚███╔╝ █████╗  ██║   ██║██████╔╝██║  ███╗█████╗
██╔══╝   ██╔██╗ ██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝
███████╗██╔╝ ██╗██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗
╚══════╝╚═╝  ╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
</pre>

### 🔥 AI-Powered Lead Generation Agent for Web Agencies & Freelancers

**Find weak websites → Audit them → Send personalized reports → Get clients. Automatically.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Claude](https://img.shields.io/badge/Powered%20by-Claude%20Haiku-D97706?style=for-the-badge)](https://anthropic.com)
[![Playwright](https://img.shields.io/badge/Scraping-Playwright-45ba4b?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)
[![Emails Sent](https://img.shields.io/badge/Emails%20Sent-64%2B-ef4444?style=for-the-badge)](https://github.com/shahan24h/exforge)

<br/>

> Built by **[Shahan Ahmed](https://shahanahmed.com)** for **PixelForgeBD**  
> A real agent running real outreach — 64+ cold emails sent autonomously

<br/>

[🚀 Quick Start](#-quick-start) · [⚙️ How It Works](#-how-it-works) · [📁 Project Structure](#-project-structure) · [🗺️ Roadmap](#-roadmap)

</div>

---

## 💡 What Is ExForge?

ExForge is a **fully autonomous lead generation pipeline**. You point it at a niche and a city. It finds small businesses on Google Maps, visits their websites, identifies real problems, writes a personalized audit report as a PDF, and sends a cold email with the report attached — all without you touching anything.

```
You set the niche → ExForge does everything else
```

No manual prospecting. No copy-paste emails. No generic templates.
Every email references **specific issues found on that business's actual website.**

**Proven in production** — ran live targeting local businesses across multiple cities and niches. Generated real PDFs, email drafts, and sent 64+ cold emails autonomously.

---

## 🎬 The Pipeline at a Glance

```
┌──────────┬──────────┬───────────┬──────────┬──────────┬──────────┐
│  SCRAPE  │SHORTLIST │   AUDIT   │  REPORT  │  DRAFT   │   SEND   │
│          │          │           │          │          │          │
│ Google   │  Claude  │ Playwright│  PDF per │  Claude  │   SMTP   │
│  Maps    │  Haiku   │  visits   │ business │  writes  │  sends   │
│ → CSVs   │ scores   │ site +    │scorecard │ personal │ email +  │
│ in data/ │  1–10    │screenshot │+ issues  │  email   │   PDF    │
└──────────┴──────────┴───────────┴──────────┴──────────┴──────────┘
        ↓                                               ↓
  leads.db tracks everything              Never contacts same
  — no duplicate runs ever               business twice
```

---

## ✨ Features

| Feature | Details |
|---|---|
| 🗺️ **Google Maps Scraping** | Finds businesses by niche + location, saves timestamped CSVs |
| 🤖 **AI Lead Scoring** | Claude Haiku rates each lead 1–10, filters chains & franchises |
| 🔍 **Website Auditing** | Checks HTTPS, SEO tags, mobile layout, load speed, alt text |
| 📸 **Screenshots** | Full-page screenshot of each business website saved as PNG |
| 📄 **PDF Report Generation** | Professional audit report with grade, issues & revenue impact |
| 📝 **Email Drafts** | Claude writes unique draft `.txt` per business before sending |
| 📬 **Auto Email Sending** | SMTP dispatch with PDF attached using your business email |
| ✅ **Approval Gate** | Optional human review step before emails go out | It is currently excluded.
| 🔄 **Windows Scheduler** | `run_exforge.bat` for Task Scheduler automation |
| 🗃️ **SQLite State Tracking** | `leads.db` prevents duplicate scrapes and double-sending |

---

## 🚀 Quick Start

### Step 1 — Clone & Install

```bash
git clone https://github.com/shahan24h/exforge.git
cd exforge
pip install -r requirements.txt
playwright install chromium
```

### Step 2 — Create Your `.env` File

```bash
copy .env.example .env      # Windows
cp .env.example .env        # Mac/Linux
```

Open `.env` and fill in your credentials:

```env
# ── Anthropic ──────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-your-key-here

# ── Email (SMTP) ───────────────────────────────────────
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@youragency.com
SMTP_PASSWORD=your-app-password       # Gmail: use App Password, not your account password
FROM_NAME=Your Name / Agency Name

# ── IMAP (for tracking replies) ────────────────────────
IMAP_HOST=imap.gmail.com
IMAP_USER=you@youragency.com
IMAP_PASSWORD=your-app-password

# ── Target ─────────────────────────────────────────────
TARGET_NICHE=restaurants              # Any business type — restaurants, dentists, plumbers, etc.
TARGET_LOCATION=Brooklyn, New York    # Any city, anywhere in the world
MAX_LEADS_PER_RUN=20                  # How many to process per run
MIN_AI_SCORE=6                        # Only proceed with leads scoring 6+
```

> 💡 **Gmail users:** Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) and generate an App Password. Use that as both `SMTP_PASSWORD` and `IMAP_PASSWORD`.

### Step 3 — Run It

```bash
python main.py
```

That's it. ExForge handles the rest.

---

## ⌨️ All Commands

```bash
# ── Full Pipeline ───────────────────────────────────────────────
python main.py                    # Run the complete pipeline

# ── Individual Modules ─────────────────────────────────────────
python main.py --scrape-only      # Only scrape Google Maps → saves CSVs
python main.py --audit-only       # Only audit already-scraped leads
python main.py --report-only      # Only generate PDF reports
python main.py --email-only       # Only send pending email drafts

# ── Utilities ──────────────────────────────────────────────────
python main.py --status           # Show pipeline stats from leads.db
python reset.py                   # Reset the database (start fresh)
python test_imap.py               # Test your IMAP connection for reply tracking

# ── Windows Automation ─────────────────────────────────────────
run_exforge.bat                   # Double-click or add to Task Scheduler
```

---

## ⚙️ How It Works

### 🗺️ Step 1 — Google Maps Scraper (`scraper/maps_scraper.py`)

Playwright opens a headless Chromium browser and searches Google Maps for your `TARGET_NICHE` + `TARGET_LOCATION`. For each result it extracts:

- Business name, address, phone number
- Website URL
- Google rating & review count

Results are saved as **timestamped CSV files** in `data/` like:
```
data/restaurants_Brooklyn_NewYork_20260414_090000.csv
```

You can run multiple search terms automatically to maximize coverage — for example targeting `restaurants`, `cafes`, and `diners` in the same city in a single run.

---

### 🤖 Step 2 — AI Shortlister (`shortlister/shortlist.py`)

Each lead from the CSVs is sent to **Claude Haiku** which assigns a score from **1–10**:

- Is it a local independent business (not a chain or franchise)?
- Does it have a website that could realistically be improved?
- Does the niche typically value online presence?

Leads scoring **below `MIN_AI_SCORE`** (default: 6) are skipped. All results are stored in **`data/leads.db`** — SQLite prevents the same business from ever being processed twice.

---

### 🔍 Step 3 — Website Auditor (`auditor/audit.py`)

Playwright visits each shortlisted business website and checks:

| Check | What It Looks For |
|---|---|
| 🔒 HTTPS | Is the site using a secure connection? |
| 📝 Meta Title | Is a title tag present and well-written? |
| 📋 Meta Description | Is a description tag present? |
| 📱 Mobile Viewport | Does the site declare a responsive viewport? |
| 🖼️ Image Alt Text | Do images have accessibility labels? |
| ⚡ Load Time | How long does the page take to fully load? |
| 📧 Contact Email | Extracts any visible email from the site |

A **full-page screenshot** is saved to `data/screenshots/` as a PNG:
```
data/screenshots/Joes_Pizza.png
data/screenshots/Brooklyn_Plumbing_Co.png
```

---

### 📄 Step 4 — Report Generator (`reporter/report_generator.py`)

A professional PDF audit report is generated per business using `reportlab` and saved to `data/reports/`:

```
┌────────────────────────────────────────────┐
│   [Business Name] — Website Audit Report   │
│   Generated by [Your Agency Name]          │
├────────────────────────────────────────────┤
│   Overall Grade:  D                        │
├────────────────────────────────────────────┤
│   Issues Found:                            │
│    ✗  No HTTPS — site is not secure        │
│    ✗  Missing meta description             │
│    ✗  No mobile responsive design          │
│    ✗  12 images missing alt text           │
│    ✗  Page load time: 8.2 seconds          │
├────────────────────────────────────────────┤
│   Estimated Revenue Impact:                │
│    $3,200 – $8,400 / year                  │
├────────────────────────────────────────────┤
│  [Live Screenshot of Their Website]        │
│                                            │
│  Ready to fix this? Reply for a quote.     │
└────────────────────────────────────────────┘
```

---

### ✉️ Step 5 — Email Composer (`emailer/compose.py`)

The audit data is sent to **Claude Haiku** which writes a short, personalized cold email. Each draft is saved as a `.txt` file in `data/drafts/` before sending:

```
data/drafts/Joes_Pizza_draft.txt
data/drafts/Brooklyn_Plumbing_Co_draft.txt
```

The email references the business by name and mentions **2–3 specific issues** found during the audit — no templates, no generic copy.

**Example output:**

```
Subject: Quick note about Joe's Pizza's website

Hi,

I came across Joe's Pizza while searching for restaurants in Brooklyn
and ran a quick audit on your site.

A few things stood out — the site isn't loading over HTTPS, there's
no mobile layout (most searches happen on phones), and the page takes
over 7 seconds to load which typically costs a significant share of
visitors before they see your menu.

I've attached a short report with the full details.

Happy to chat if you'd like — no obligation.

Best,
[Your Name] · [Agency Name]
```

---

### ✅ Step 6 — Approval Gate (`approvals/approval_gate.py`)

An **optional human review step** before emails go out. Run the approval gate to review each draft and PDF before sending — useful when targeting a new niche or city for the first time.

To skip the approval gate and send automatically, configure `AUTO_APPROVE=true` in `.env`.

---

### 📬 Step 7 — Email Sender (`emailer/send.py`)

Sends the composed email via SMTP using your business email address, with the PDF audit report attached. Each sent lead is marked in `leads.db` so it is **never contacted again**.

---

## 📁 Project Structure

```
exforge/
│
├── main.py                        # Entry point & pipeline orchestration
├── reset.py                       # Wipe leads.db and start fresh
├── run_exforge.bat                # Windows Task Scheduler automation
├── test_imap.py                   # Test IMAP connection for reply tracking
├── requirements.txt               # Python dependencies
├── .env                           # Your credentials (never commit this)
├── .gitignore
├── LICENSE
│
├── scraper/
│   └── maps_scraper.py            # Google Maps scraper (Playwright)
│
├── shortlister/
│   └── shortlist.py               # Claude Haiku lead scoring (1–10)
│
├── auditor/
│   └── audit.py                   # SEO checks + screenshot + email extract
│
├── reporter/
│   └── report_generator.py        # PDF audit report builder (reportlab)
│
├── emailer/
│   ├── compose.py                 # Claude Haiku email writer → saves drafts
│   └── send.py                    # SMTP dispatch with PDF attachment
│
├── approvals/
│   ├── approval_gate.py           # Human review CLI before sending
│   └── approval_gate2.py          # Alternative approval flow
│
└── data/                          # All generated output lives here
    ├── leads.db                   # SQLite — all leads, statuses, history
    ├── *.csv                      # Raw scrape results (timestamped)
    ├── drafts/
    │   └── BusinessName_draft.txt # Email drafts (one per lead)
    ├── reports/
    │   └── BusinessName_report.pdf# Audit PDFs (one per lead)
    └── screenshots/
        └── BusinessName.png       # Website screenshots (one per lead)
```

---

## 📦 Requirements

```txt
anthropic
playwright
reportlab
Pillow
python-dotenv
requests
beautifulsoup4
schedule
```

Install everything:

```bash
pip install -r requirements.txt
playwright install chromium
```

---

## 🖥️ Windows Automation

ExForge includes `run_exforge.bat` for native Windows scheduling.

**To run automatically every morning:**

1. Open **Task Scheduler** → Create Basic Task
2. Set trigger: **Daily at 9:00 AM**
3. Set action: **Start a program** → browse to `run_exforge.bat`
4. Save

ExForge will run silently every morning, process new leads, and send emails while you sleep.

---

## 🌍 Changing Your Target

Edit these lines in `.env`:

```env
TARGET_NICHE=restaurants
TARGET_LOCATION=Brooklyn, New York
```

**Niches that work well:**

```
Local Services       →  plumbers · electricians · landscapers · cleaners
Food & Hospitality   →  restaurants · cafes · bakeries · catering
Health & Wellness    →  dentists · chiropractors · gyms · therapists
Professional         →  law firms · accountants · real estate agents
Beauty               →  barbershops · nail salons · hair salons · spas
```

Any **local, independent business** with an outdated website is a valid target.

---

## 🗺️ Roadmap

- [ ] **Outscraper integration** — replace Google Maps scraping with [Outscraper API](https://outscraper.com) for reliable, ban-free data with built-in email extraction (~$3/1,000 results, pay-per-use)
- [ ] **Camoufox** — stealth Firefox browser as a free alternative to bypass bot detection
- [ ] **Follow-up sequence** — automated 7-day follow-up email for non-replies
- [ ] **Web dashboard** — view pipeline status, sent emails, and reply tracking in browser
- [ ] **Docker deployment** — containerized for 24/7 VPS/Linux hosting
- [ ] **LinkedIn outreach** — parallel channel alongside email
- [ ] **Lighthouse integration** — deep performance scoring per audit

---

## ⚖️ Legal & Compliance

> Use responsibly.

- Only target businesses where cold email outreach is **legally permitted** in your region
- Comply with **CAN-SPAM** (US), **GDPR** (EU), and local email marketing regulations
- Always include your real name, business name, and a way to opt out
- ExForge is a tool — responsible use is entirely the operator's responsibility

---

## 🤝 Contributing

Pull requests are welcome. If you add new scrapers, audit checks, or output formats, open a PR or raise an issue.

---

## 👤 Author

<div align="center">

**Shahan Ahmed**

Data Scientist & ML Engineer 

[![Website](https://img.shields.io/badge/Website-shahanahmed.com-0ea5e9?style=flat-square)](https://shahanahmed.com)
[![GitHub](https://img.shields.io/badge/GitHub-shahan24h-181717?style=flat-square&logo=github)](https://github.com/shahan24h)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/shahan24h/)

</div>

---

<div align="center">

MIT License · Free to use, modify, and distribute

**If ExForge helped you land a client, leave a ⭐ on the repo.**

</div>
