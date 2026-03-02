# GlobalTalentHub — Flask Recruitment Platform

A full-stack worldwide job recruitment platform built with Flask + SQLite.

## Features
- 🌍 **Public site** — homepage, job listings, job detail, multi-field application form
- 🔒 **Hidden admin dashboard** — accessible at `/admin` (no link on public site)
- 🗄️ **SQLite database** — persistent jobs + applications storage, auto-seeded
- 📲 **Telegram bot** — instant notification when anyone submits a job application
- ✏️ **Job management** — add, edit, activate/deactivate, delete jobs
- 👥 **Applications** — view all applicants, update status, search & filter

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the app
```bash
python app.py
```

The app starts at **http://localhost:5000**

---

## Admin Access
Go to: **http://localhost:5000/admin**

Default password: `admin2025`
> Change it in Admin → Settings after first login

---

## Telegram Bot Setup
1. Open Telegram → search **@BotFather**
2. Send `/newbot` → follow prompts → copy the **token**
3. Start a chat with your new bot
4. Get your **Chat ID** from **@userinfobot**
5. Go to Admin → Settings → paste token + chat ID → Save
6. Click **"Test Connection"** to verify

Every new application sends a rich Telegram message with:
- Position & company
- Applicant name, email, phone, nationality, location
- Timestamp & application ID

---

## File Structure
```
recruitment/
├── app.py                  # Flask app, routes, DB, Telegram
├── requirements.txt
├── recruitment.db          # SQLite database (auto-created)
└── templates/
    ├── base.html           # Public site base layout
    ├── index.html          # Homepage
    ├── jobs.html           # Job listings with filters
    ├── job_detail.html     # Full job detail page
    ├── apply.html          # Application form
    ├── apply_success.html  # Success page
    └── admin/
        ├── base.html       # Admin dashboard layout
        ├── login.html      # Admin login
        ├── dashboard.html  # Stats + recent activity
        ├── manage_jobs.html# Job list table
        ├── add_job.html    # Post/edit job form
        ├── applications.html # All applications
        └── settings.html   # Telegram + password
```

---

## Production Deployment
For production use, replace the development server with Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

Set a strong secret key via environment variable:
```bash
export SECRET_KEY="your-very-long-random-secret-key-here"
```
