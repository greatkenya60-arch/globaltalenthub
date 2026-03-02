import os
import sqlite3
import json
import requests
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, g
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "globaltalenthub-secret-2026-xK9#mP")

DATABASE = os.path.join(os.path.dirname(__file__), "recruitment.db")

# ─── DATABASE ──────────────────────────────────────────────────────────────────

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_db(exc):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def mutate_db(query, args=()):
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id

def init_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    c = db.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            company     TEXT NOT NULL,
            location    TEXT NOT NULL,
            country     TEXT NOT NULL,
            sector      TEXT NOT NULL,
            job_type    TEXT NOT NULL,
            salary      TEXT,
            experience  TEXT,
            description TEXT,
            requirements TEXT,
            benefits    TEXT,
            deadline    TEXT,
            slots       INTEGER DEFAULT 1,
            active      INTEGER DEFAULT 1,
            urgent      INTEGER DEFAULT 0,
            posted_at   TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id          INTEGER NOT NULL,
            job_title       TEXT,
            company         TEXT,
            country         TEXT,
            sector          TEXT,
            full_name       TEXT NOT NULL,
            email           TEXT NOT NULL,
            phone           TEXT,
            nationality     TEXT,
            dob             TEXT,
            current_location TEXT,
            education       TEXT,
            experience      TEXT,
            cover_letter    TEXT,
            linkedin        TEXT,
            portfolio       TEXT,
            status          TEXT DEFAULT 'new',
            applied_at      TEXT,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Default settings
    defaults = {
        "admin_password": "admin2025",
        "bot_token": "",
        "chat_id": "",
        "notifications_enabled": "1",
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    # Seed jobs if empty
    existing = c.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    if existing == 0:
        seed_jobs = [
            ("Senior Registered Nurse", "Melbourne Health Network", "Melbourne, Victoria",
             "Australia", "Medical", "Full-Time", "AUD 90,000–110,000/yr", "3-5 Years",
             "We are seeking experienced Registered Nurses to join our dynamic healthcare team in Melbourne. You will work in our state-of-the-art facility providing exceptional patient care across multiple wards including ICU, general medicine, and surgical.",
             "Bachelor of Nursing or equivalent\nAHPRA registration\n3+ years clinical experience\nStrong communication skills\nAbility to work rotating shifts",
             "Visa sponsorship available\nRelocation assistance AUD 5,000\nComprehensive health insurance\n4 weeks annual leave\nProfessional development allowance",
             "2026-07-30", 5, 1, 1, "2026-03-01"),
            ("Full-Stack Software Engineer", "TechNova Solutions", "London, England",
             "United Kingdom", "Technology", "Full-Time", "GBP 70,000–90,000/yr", "3-5 Years",
             "TechNova is looking for a talented Full-Stack Engineer to build cutting-edge financial technology platforms. You will work with React, Node.js, and cloud technologies in a fast-paced agile environment.",
             "3+ years React/Node.js\nTypeScript proficiency\nAWS or Azure experience\nStrong problem-solving skills\nExperience with microservices",
             "Skilled Worker visa sponsorship\nRemote-friendly 3 days/week\nAnnual performance bonus\n30 days holiday\nHealth & dental package",
             "2026-07-15", 2, 1, 0, "2026-03-01"),
            ("Marine Engineer – Class II", "Pacific Star Shipping", "Perth, Western Australia",
             "Australia", "Maritime", "Contract", "AUD 140,000–170,000/yr", "5-10 Years",
             "Join our fleet as a Class II Marine Engineer. Responsible for maintaining and operating all marine machinery and equipment aboard modern bulk carriers operating in the Asia-Pacific region.",
             "Class II Engineer Certificate\nSTCW certification\n5+ years seagoing experience\nDiesel engine expertise\nValid ENG1 medical certificate",
             "Competitive sea pay\nReturn flights provided\nFull board onboard\n4 months on / 2 months off\nCareer progression to Chief Engineer",
             "2026-08-01", 3, 1, 1, "2026-03-01"),
            ("Civil Engineer – Infrastructure", "BuildRight Canada Inc.", "Toronto, Ontario",
             "Canada", "Engineering", "Full-Time", "CAD 85,000–105,000/yr", "3-5 Years",
             "BuildRight Canada is expanding its infrastructure division and seeking Civil Engineers to work on major highway, bridge, and utilities projects across Ontario and British Columbia.",
             "B.Eng Civil Engineering\nP.Eng or eligibility\n3+ years infrastructure experience\nCivil 3D / AutoCAD skills\nProject management capabilities",
             "Canada PR pathway support\nRelocation package CAD 4,000\nFull health & dental insurance\nRRSP matching 5%\nFlexible working arrangements",
             "2026-06-30", 4, 1, 0, "2026-03-01"),
            ("Hotel Operations Manager", "Emirates Grand Hotels", "Dubai Marina",
             "United Arab Emirates", "Hospitality", "Full-Time", "AED 20,000–28,000/mo", "5-10 Years",
             "Lead operations at one of Dubai's flagship luxury 5-star hotels. Oversee front office, housekeeping, food & beverage, and guest relations departments to deliver an unparalleled world-class hospitality experience.",
             "5+ years hotel management\nDegree in Hospitality Management\nMulti-cultural team leadership\nFluent English (Arabic a plus)\nOpera PMS proficiency",
             "Tax-free salary\nFurnished accommodation\nBusiness class annual flight\n30 days annual leave\nMeals on duty & medical insurance",
             "2026-06-20", 1, 1, 0, "2026-03-01"),
            ("Secondary School Science Teacher", "Auckland International College", "Auckland, North Island",
             "New Zealand", "Education", "Full-Time", "NZD 70,000–88,000/yr", "1-2 Years",
             "We are recruiting passionate Science teachers to join our innovative secondary school in Auckland. You will teach Biology, Chemistry, and Physics to students aged 13-18 using modern inquiry-based learning approaches.",
             "B.Ed or subject degree + PGCE\nNZ Teaching registration eligible\nStrong classroom management\nICT-integrated teaching\nCommitment to student wellbeing",
             "Visa sponsorship\nRelocation allowance NZD 3,500\nProfessional development funding\nSchool holiday breaks\nWarm supportive community",
             "2026-06-10", 2, 1, 1, "2026-03-01"),
            ("Senior Data Analyst", "FinTech Solutions GmbH", "Berlin, Brandenburg",
             "Germany", "Finance", "Full-Time", "EUR 62,000–82,000/yr", "3-5 Years",
             "FinTech Solutions GmbH is seeking a Senior Data Analyst to extract deep insights from large datasets and support strategic decision-making in our rapidly expanding European financial technology company.",
             "Advanced Python & SQL\nPower BI or Tableau\nStatistical modelling skills\nFinancial data experience preferred\nEnglish fluent, German a plus",
             "EU Blue Card sponsorship\nBerlin relocation support\nPublic transport annual card\nGym membership\nRemote Fridays policy",
             "2026-07-05", 2, 1, 0, "2026-03-01"),
            ("Construction Project Director", "Riyadh Vision Development", "Riyadh, Central Region",
             "Saudi Arabia", "Construction", "Contract", "SAR 28,000–40,000/mo", "10+ Years",
             "Oversee mega-scale construction projects in Riyadh as part of Saudi Vision 2030. You will lead teams of 200+ professionals, manage multi-billion SAR budgets, and deliver landmark architectural projects on schedule.",
             "10+ years construction management\nB.Eng Civil/Construction\nPMP & CIOB membership\nNEBOSH safety certification\nGCC project experience required",
             "Tax-free package\nExecutive villa accommodation\nBusiness class flights\nFull medical & family insurance\nPerformance bonus up to 20%",
             "2026-08-15", 2, 1, 1, "2026-03-01"),
            ("Cybersecurity Analyst", "SecureNet Singapore", "Central Business District",
             "Singapore", "Technology", "Full-Time", "SGD 90,000–120,000/yr", "3-5 Years",
             "Join Singapore's leading cybersecurity firm protecting Fortune 500 clients across Asia-Pacific. You will perform penetration testing, threat intelligence analysis, and develop security frameworks.",
             "CEH or CISSP certification\n3+ years SOC experience\nCloud security AWS/Azure\nIncident response expertise\nScripting Python/Bash",
             "Employment Pass sponsorship\nAnnual flight allowance\nCompetitive bonus scheme\nLatest tech equipment\nFlexible working hours",
             "2026-07-20", 3, 1, 0, "2026-03-01"),
            ("Agricultural Farm Supervisor", "GreenFields Australia", "Mildura, Victoria",
             "Australia", "Agriculture", "Full-Time", "AUD 65,000–80,000/yr", "3-5 Years",
             "Supervise daily operations on one of Australia's largest horticultural farms spanning 2,000 hectares. Manage planting, irrigation, harvesting, and quality control for export-grade produce.",
             "Diploma or degree in Agriculture\n3+ years farm supervision\nIrrigation systems knowledge\nPest & disease management\nHeavy equipment licence",
             "457 Regional visa sponsorship\nOn-site accommodation provided\nVehicle provided\nMeals allowance\nAnnual bonuses",
             "2026-07-01", 2, 1, 0, "2026-03-01"),
        ]
        for job in seed_jobs:
            c.execute("""
                INSERT INTO jobs (title, company, location, country, sector, job_type,
                    salary, experience, description, requirements, benefits,
                    deadline, slots, active, urgent, posted_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, job)

    db.commit()
    db.close()
    print("✅ Database initialized.")

# ─── HELPERS ───────────────────────────────────────────────────────────────────

def get_setting(key, default=""):
    row = query_db("SELECT value FROM settings WHERE key=?", (key,), one=True)
    return row["value"] if row else default

def set_setting(key, value):
    mutate_db("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))

def row_to_dict(row):
    return dict(row) if row else None

def rows_to_list(rows):
    return [dict(r) for r in rows]

COUNTRY_FLAGS = {
    "Australia": "🇦🇺", "United Kingdom": "🇬🇧", "United States": "🇺🇸",
    "Canada": "🇨🇦", "United Arab Emirates": "🇦🇪", "Germany": "🇩🇪",
    "New Zealand": "🇳🇿", "Singapore": "🇸🇬", "Qatar": "🇶🇦",
    "Saudi Arabia": "🇸🇦", "Netherlands": "🇳🇱", "Sweden": "🇸🇪",
    "Norway": "🇳🇴", "Japan": "🇯🇵", "South Korea": "🇰🇷",
    "France": "🇫🇷", "Switzerland": "🇨🇭", "Denmark": "🇩🇰",
    "Ireland": "🇮🇪", "Belgium": "🇧🇪",
}

SECTOR_EMOJIS = {
    "Medical": "🏥", "Technology": "💻", "Maritime": "⚓", "Engineering": "⚙️",
    "Finance": "💰", "Education": "📚", "Hospitality": "🍽️", "Construction": "🏗️",
    "Agriculture": "🌾", "Legal": "⚖️", "Manufacturing": "🏭",
    "Transport": "🚢", "Energy": "⚡", "Logistics": "📦",
}

COUNTRIES = list(COUNTRY_FLAGS.keys())
SECTORS = list(SECTOR_EMOJIS.keys())
JOB_TYPES = ["Full-Time", "Part-Time", "Contract", "Freelance", "Internship"]
EXP_LEVELS = ["Entry Level", "1-2 Years", "3-5 Years", "5-10 Years", "10+ Years"]
APP_STATUSES = ["new", "reviewing", "shortlisted", "rejected", "hired"]
STATUS_COLORS = {
    "new": "#3b82f6", "reviewing": "#f59e0b",
    "shortlisted": "#8b5cf6", "rejected": "#ef4444", "hired": "#10b981"
}

app.jinja_env.globals.update(
    COUNTRY_FLAGS=COUNTRY_FLAGS, SECTOR_EMOJIS=SECTOR_EMOJIS,
    COUNTRIES=COUNTRIES, SECTORS=SECTORS, JOB_TYPES=JOB_TYPES,
    EXP_LEVELS=EXP_LEVELS, APP_STATUSES=APP_STATUSES,
    STATUS_COLORS=STATUS_COLORS, now=datetime.now,
)

def send_telegram(token, chat_id, text):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=8,
        )
        return r.ok
    except Exception:
        return False

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

# ─── PUBLIC ROUTES ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    featured_jobs = rows_to_list(query_db(
        "SELECT * FROM jobs WHERE active=1 ORDER BY urgent DESC, id DESC LIMIT 6"
    ))
    total_active = query_db("SELECT COUNT(*) as c FROM jobs WHERE active=1", one=True)["c"]
    # Sector counts
    sector_counts = {}
    for s in SECTORS:
        cnt = query_db("SELECT COUNT(*) as c FROM jobs WHERE active=1 AND sector=?", (s,), one=True)["c"]
        sector_counts[s] = cnt
    return render_template("index.html",
        featured_jobs=featured_jobs,
        total_active=total_active,
        sector_counts=sector_counts,
    )


@app.route("/jobs")
def jobs():
    search   = request.args.get("search", "").strip()
    sector   = request.args.get("sector", "")
    country  = request.args.get("country", "")
    job_type = request.args.get("type", "")

    q = "SELECT * FROM jobs WHERE active=1"
    params = []
    if search:
        q += " AND (title LIKE ? OR company LIKE ? OR location LIKE ? OR sector LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like, like])
    if sector:
        q += " AND sector=?"
        params.append(sector)
    if country:
        q += " AND country=?"
        params.append(country)
    if job_type:
        q += " AND job_type=?"
        params.append(job_type)
    q += " ORDER BY urgent DESC, id DESC"

    all_jobs = rows_to_list(query_db(q, params))
    return render_template("jobs.html",
        all_jobs=all_jobs,
        search=search, sector=sector, country=country, job_type=job_type,
    )


@app.route("/jobs/<int:job_id>")
def job_detail(job_id):
    job = row_to_dict(query_db("SELECT * FROM jobs WHERE id=? AND active=1", (job_id,), one=True))
    if not job:
        flash("Job not found or no longer available.", "error")
        return redirect(url_for("jobs"))
    job["requirements_list"] = [r.strip() for r in (job["requirements"] or "").split("\n") if r.strip()]
    job["benefits_list"]     = [b.strip() for b in (job["benefits"] or "").split("\n") if b.strip()]
    app_count = query_db("SELECT COUNT(*) as c FROM applications WHERE job_id=?", (job_id,), one=True)["c"]
    return render_template("job_detail.html", job=job, app_count=app_count)


@app.route("/apply/<int:job_id>", methods=["GET", "POST"])
def apply(job_id):
    job = row_to_dict(query_db("SELECT * FROM jobs WHERE id=? AND active=1", (job_id,), one=True))
    if not job:
        flash("This job is no longer available.", "error")
        return redirect(url_for("jobs"))

    errors = {}
    form_data = {}

    if request.method == "POST":
        form_data = {
            "full_name":        request.form.get("full_name", "").strip(),
            "email":            request.form.get("email", "").strip(),
            "phone":            request.form.get("phone", "").strip(),
            "nationality":      request.form.get("nationality", "").strip(),
            "dob":              request.form.get("dob", "").strip(),
            "current_location": request.form.get("current_location", "").strip(),
            "education":        request.form.get("education", "").strip(),
            "experience":       request.form.get("experience", "").strip(),
            "cover_letter":     request.form.get("cover_letter", "").strip(),
            "linkedin":         request.form.get("linkedin", "").strip(),
            "portfolio":        request.form.get("portfolio", "").strip(),
        }
        # Validation
        required = ["full_name", "email", "phone", "nationality", "current_location", "education", "experience"]
        for field in required:
            if not form_data[field]:
                errors[field] = "This field is required."
        if "@" not in form_data.get("email", ""):
            errors["email"] = "Please enter a valid email address."

        if not errors:
            app_id = mutate_db("""
                INSERT INTO applications
                    (job_id, job_title, company, country, sector,
                     full_name, email, phone, nationality, dob,
                     current_location, education, experience,
                     cover_letter, linkedin, portfolio, status, applied_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                job["id"], job["title"], job["company"], job["country"], job["sector"],
                form_data["full_name"], form_data["email"], form_data["phone"],
                form_data["nationality"], form_data["dob"], form_data["current_location"],
                form_data["education"], form_data["experience"],
                form_data["cover_letter"], form_data["linkedin"], form_data["portfolio"],
                "new", datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ))

            # Telegram notification
            token = get_setting("bot_token")
            chat_id = get_setting("chat_id")
            notif_on = get_setting("notifications_enabled", "1")
            if token and chat_id and notif_on == "1":
                msg = (
                    f"🔔 <b>New Job Application!</b>\n\n"
                    f"📋 <b>Position:</b> {job['title']}\n"
                    f"🏢 <b>Company:</b> {job['company']}\n"
                    f"🌍 <b>Country:</b> {job['country']}\n\n"
                    f"👤 <b>Applicant:</b> {form_data['full_name']}\n"
                    f"📧 <b>Email:</b> {form_data['email']}\n"
                    f"📱 <b>Phone:</b> {form_data['phone']}\n"
                    f"🌐 <b>Nationality:</b> {form_data['nationality']}\n"
                    f"📍 <b>Location:</b> {form_data['current_location']}\n\n"
                    f"⏰ <b>Applied:</b> {datetime.now().strftime('%d %b %Y, %H:%M')}\n"
                    f"🔗 Application ID: #{app_id}\n\n"
                    f"<i>Login to admin panel to review this application.</i>"
                )
                send_telegram(token, chat_id, msg)

            return redirect(url_for("apply_success",
                name=form_data["full_name"],
                job_title=job["title"],
                company=job["company"],
            ))

    return render_template("apply.html", job=job, errors=errors, form_data=form_data)


@app.route("/apply/success")
def apply_success():
    name      = request.args.get("name", "Applicant")
    job_title = request.args.get("job_title", "")
    company   = request.args.get("company", "")
    return render_template("apply_success.html", name=name, job_title=job_title, company=company)


# ─── ADMIN ROUTES ──────────────────────────────────────────────────────────────

@app.route("/admin")
def admin_index():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("admin_login"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        correct  = get_setting("admin_password", "admin2025")
        if password == correct:
            session["admin_logged_in"] = True
            session.permanent = True
            return redirect(url_for("admin_dashboard"))
        error = "Incorrect password. Please try again."
    return render_template("admin/login.html", error=error)


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    total_jobs    = query_db("SELECT COUNT(*) as c FROM jobs", one=True)["c"]
    active_jobs   = query_db("SELECT COUNT(*) as c FROM jobs WHERE active=1", one=True)["c"]
    total_apps    = query_db("SELECT COUNT(*) as c FROM applications", one=True)["c"]
    new_apps      = query_db("SELECT COUNT(*) as c FROM applications WHERE status='new'", one=True)["c"]
    hired         = query_db("SELECT COUNT(*) as c FROM applications WHERE status='hired'", one=True)["c"]
    recent_apps   = rows_to_list(query_db(
        "SELECT * FROM applications ORDER BY id DESC LIMIT 8"
    ))
    sector_stats  = rows_to_list(query_db(
        "SELECT sector, COUNT(*) as cnt FROM jobs GROUP BY sector ORDER BY cnt DESC"
    ))
    country_stats = rows_to_list(query_db(
        "SELECT country, COUNT(*) as cnt FROM applications GROUP BY country ORDER BY cnt DESC LIMIT 6"
    ))
    return render_template("admin/dashboard.html",
        total_jobs=total_jobs, active_jobs=active_jobs,
        total_apps=total_apps, new_apps=new_apps, hired=hired,
        recent_apps=recent_apps, sector_stats=sector_stats,
        country_stats=country_stats,
    )


@app.route("/admin/jobs")
@admin_required
def admin_jobs():
    all_jobs = rows_to_list(query_db("SELECT * FROM jobs ORDER BY id DESC"))
    for job in all_jobs:
        job["app_count"] = query_db(
            "SELECT COUNT(*) as c FROM applications WHERE job_id=?",
            (job["id"],), one=True
        )["c"]
    return render_template("admin/manage_jobs.html", all_jobs=all_jobs)


@app.route("/admin/jobs/add", methods=["GET", "POST"])
@admin_required
def admin_add_job():
    errors = {}
    form_data = {
        "title": "", "company": "", "location": "", "country": "Australia",
        "sector": "Medical", "job_type": "Full-Time", "salary": "",
        "experience": "Entry Level", "description": "", "requirements": "",
        "benefits": "", "deadline": "", "slots": 1, "active": 1, "urgent": 0,
    }

    if request.method == "POST":
        form_data = {
            "title":       request.form.get("title", "").strip(),
            "company":     request.form.get("company", "").strip(),
            "location":    request.form.get("location", "").strip(),
            "country":     request.form.get("country", "Australia"),
            "sector":      request.form.get("sector", "Medical"),
            "job_type":    request.form.get("job_type", "Full-Time"),
            "salary":      request.form.get("salary", "").strip(),
            "experience":  request.form.get("experience", "Entry Level"),
            "description": request.form.get("description", "").strip(),
            "requirements":request.form.get("requirements", "").strip(),
            "benefits":    request.form.get("benefits", "").strip(),
            "deadline":    request.form.get("deadline", "").strip(),
            "slots":       int(request.form.get("slots", 1) or 1),
            "active":      1 if request.form.get("active") else 0,
            "urgent":      1 if request.form.get("urgent") else 0,
        }
        for f in ["title", "company", "location"]:
            if not form_data[f]:
                errors[f] = "Required."

        if not errors:
            mutate_db("""
                INSERT INTO jobs (title, company, location, country, sector, job_type,
                    salary, experience, description, requirements, benefits,
                    deadline, slots, active, urgent, posted_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                form_data["title"], form_data["company"], form_data["location"],
                form_data["country"], form_data["sector"], form_data["job_type"],
                form_data["salary"], form_data["experience"], form_data["description"],
                form_data["requirements"], form_data["benefits"], form_data["deadline"],
                form_data["slots"], form_data["active"], form_data["urgent"],
                datetime.now().strftime("%Y-%m-%d"),
            ))
            flash("✅ Job posted successfully!", "success")
            return redirect(url_for("admin_jobs"))

    return render_template("admin/add_job.html",
        form_data=form_data, errors=errors, edit_mode=False, job_id=None)


@app.route("/admin/jobs/edit/<int:job_id>", methods=["GET", "POST"])
@admin_required
def admin_edit_job(job_id):
    job = row_to_dict(query_db("SELECT * FROM jobs WHERE id=?", (job_id,), one=True))
    if not job:
        flash("Job not found.", "error")
        return redirect(url_for("admin_jobs"))

    errors = {}
    form_data = dict(job)
    form_data.setdefault("active", 1)
    form_data.setdefault("urgent", 0)

    if request.method == "POST":
        form_data = {
            "title":       request.form.get("title", "").strip(),
            "company":     request.form.get("company", "").strip(),
            "location":    request.form.get("location", "").strip(),
            "country":     request.form.get("country", "Australia"),
            "sector":      request.form.get("sector", "Medical"),
            "job_type":    request.form.get("job_type", "Full-Time"),
            "salary":      request.form.get("salary", "").strip(),
            "experience":  request.form.get("experience", "Entry Level"),
            "description": request.form.get("description", "").strip(),
            "requirements":request.form.get("requirements", "").strip(),
            "benefits":    request.form.get("benefits", "").strip(),
            "deadline":    request.form.get("deadline", "").strip(),
            "slots":       int(request.form.get("slots", 1) or 1),
            "active":      1 if request.form.get("active") else 0,
            "urgent":      1 if request.form.get("urgent") else 0,
        }
        for f in ["title", "company", "location"]:
            if not form_data[f]:
                errors[f] = "Required."

        if not errors:
            mutate_db("""
                UPDATE jobs SET title=?, company=?, location=?, country=?, sector=?,
                    job_type=?, salary=?, experience=?, description=?, requirements=?,
                    benefits=?, deadline=?, slots=?, active=?, urgent=?
                WHERE id=?
            """, (
                form_data["title"], form_data["company"], form_data["location"],
                form_data["country"], form_data["sector"], form_data["job_type"],
                form_data["salary"], form_data["experience"], form_data["description"],
                form_data["requirements"], form_data["benefits"], form_data["deadline"],
                form_data["slots"], form_data["active"], form_data["urgent"], job_id,
            ))
            flash("✅ Job updated successfully!", "success")
            return redirect(url_for("admin_jobs"))

    return render_template("admin/add_job.html",
        form_data=form_data, errors=errors, edit_mode=True, job_id=job_id)


@app.route("/admin/jobs/delete/<int:job_id>", methods=["POST"])
@admin_required
def admin_delete_job(job_id):
    mutate_db("DELETE FROM jobs WHERE id=?", (job_id,))
    flash("🗑️ Job deleted.", "info")
    return redirect(url_for("admin_jobs"))


@app.route("/admin/jobs/toggle/<int:job_id>", methods=["POST"])
@admin_required
def admin_toggle_job(job_id):
    job = query_db("SELECT active FROM jobs WHERE id=?", (job_id,), one=True)
    if job:
        new_status = 0 if job["active"] else 1
        mutate_db("UPDATE jobs SET active=? WHERE id=?", (new_status, job_id))
        flash(f"Job {'activated' if new_status else 'deactivated'}.", "success")
    return redirect(url_for("admin_jobs"))


@app.route("/admin/applications")
@admin_required
def admin_applications():
    status_filter = request.args.get("status", "")
    search        = request.args.get("search", "").strip()
    q = "SELECT * FROM applications WHERE 1=1"
    params = []
    if status_filter:
        q += " AND status=?"
        params.append(status_filter)
    if search:
        like = f"%{search}%"
        q += " AND (full_name LIKE ? OR email LIKE ? OR job_title LIKE ?)"
        params.extend([like, like, like])
    q += " ORDER BY id DESC"
    apps = rows_to_list(query_db(q, params))
    return render_template("admin/applications.html",
        apps=apps, status_filter=status_filter, search=search)


@app.route("/admin/applications/update-status", methods=["POST"])
@admin_required
def admin_update_status():
    app_id = request.form.get("app_id")
    status = request.form.get("status")
    if app_id and status in APP_STATUSES:
        mutate_db("UPDATE applications SET status=? WHERE id=?", (status, app_id))
        flash(f"Status updated to <strong>{status}</strong>.", "success")
    return redirect(url_for("admin_applications",
        status=request.form.get("status_filter", ""),
        search=request.form.get("search_val", ""),
    ))


@app.route("/admin/applications/delete/<int:app_id>", methods=["POST"])
@admin_required
def admin_delete_app(app_id):
    mutate_db("DELETE FROM applications WHERE id=?", (app_id,))
    flash("Application deleted.", "info")
    return redirect(url_for("admin_applications"))


@app.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def admin_settings():
    msg = None
    test_result = None

    if request.method == "POST":
        action = request.form.get("action")

        if action == "save_telegram":
            set_setting("bot_token", request.form.get("bot_token", "").strip())
            set_setting("chat_id",   request.form.get("chat_id", "").strip())
            set_setting("notifications_enabled", "1" if request.form.get("notifications_enabled") else "0")
            flash("✅ Telegram settings saved!", "success")

        elif action == "test_telegram":
            token   = request.form.get("bot_token", "").strip()
            chat_id = request.form.get("chat_id", "").strip()
            ok = send_telegram(token, chat_id,
                "🤖 <b>GlobalTalentHub — Test Message</b>\n\n"
                "✅ Your Telegram bot is connected and working!\n"
                "You will now receive instant notifications for new job applications.")
            if ok:
                flash("✅ Telegram test sent! Check your chat.", "success")
            else:
                flash("❌ Failed. Check your bot token and chat ID.", "error")

        elif action == "change_password":
            new_pw  = request.form.get("new_password", "").strip()
            confirm = request.form.get("confirm_password", "").strip()
            if not new_pw:
                flash("Password cannot be empty.", "error")
            elif new_pw != confirm:
                flash("Passwords do not match.", "error")
            elif len(new_pw) < 6:
                flash("Password must be at least 6 characters.", "error")
            else:
                set_setting("admin_password", new_pw)
                flash("✅ Password updated successfully!", "success")

        return redirect(url_for("admin_settings"))

    settings_data = {
        "bot_token":               get_setting("bot_token"),
        "chat_id":                 get_setting("chat_id"),
        "notifications_enabled":   get_setting("notifications_enabled", "1"),
    }
    return render_template("admin/settings.html", settings=settings_data)


# ─── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)


@app.context_processor
def inject_admin_globals():
    if request.path.startswith('/admin') and session.get('admin_logged_in'):
        cnt = query_db("SELECT COUNT(*) as c FROM applications WHERE status='new'", one=True)
        return {"new_apps_count": cnt["c"] if cnt else 0}
    return {"new_apps_count": 0}
