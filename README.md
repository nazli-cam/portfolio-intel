# Portfolio Intelligence Platform

A VC portfolio intelligence web app that automatically monitors portfolio companies for key signals using Apollo.io and Claude AI, then sends Gmail alerts and generates monthly reports.

## Architecture

```
portfolio-intel/
├── backend/          # Python FastAPI + SQLite
│   ├── app/
│   │   ├── models/   # SQLAlchemy models (User, Company, Signal, Report)
│   │   ├── routers/  # FastAPI routes (auth, companies, signals, reports)
│   │   ├── schemas/  # Pydantic schemas
│   │   └── services/ # Apollo, Claude, Gmail, Scheduler, Report
│   ├── scripts/      # Gmail OAuth2 setup helper
│   └── Dockerfile
└── frontend/         # React + Vite + Tailwind CSS
    └── src/
        ├── pages/    # Dashboard, Companies, Signals, Reports
        └── services/ # API client (axios)
```

## Features

- **Team Login** — JWT authentication with role-based access (analyst, partner, admin)
- **Portfolio Companies** — CRUD for portfolio companies with LinkedIn/website fields
- **Daily Intelligence Job** — APScheduler runs at 8 AM UTC, fetches Apollo.io data per company
- **Signal Extraction** — Claude Sonnet analyzes company data and extracts new hires, departures, founder posts, funding, partnerships, product launches
- **Gmail Alerts** — Automatic email alerts for medium/high priority signals
- **Monthly Reports** — Claude-generated HTML reports summarizing the month's intelligence
- **Dashboard** — Live overview with unread signal count and recent activity

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker + Docker Compose (for containerized deployment)

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/nazli-cam/portfolio-intel.git
cd portfolio-intel
cp backend/.env.example backend/.env
```

Generate a secure `SECRET_KEY` and paste it into `backend/.env`:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Run with Docker Compose

```bash
# Create the data directory the bind-mount expects
mkdir -p data

docker compose up --build
# API:      http://localhost:8000
# Frontend: http://localhost:5173
```

### 3. Create your first admin user

On first run, the app seeds a default admin account:

```
email:    admin@portfoliointel.com
password: changeme123
```

**Change this immediately in production** using the `create_admin.py` script:

```bash
# From the backend/ directory (or inside the running container):
python scripts/create_admin.py you@yourfirm.com "Your Name" "a-strong-password"
```

The script is idempotent — running it twice with the same email is safe.

To run it inside the Docker container:

```bash
docker compose exec backend python scripts/create_admin.py you@yourfirm.com "Your Name" "a-strong-password"
```

### 4. Local development (without Docker)

**Backend:**

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

alembic upgrade head
uvicorn app.main:app --reload
# API at http://localhost:8000  •  Docs at http://localhost:8000/docs
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
# App at http://localhost:5173
```

## Configuration

### Required API Keys

| Variable | Description | Where to get it |
|---|---|---|
| `SECRET_KEY` | JWT signing key | `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `ANTHROPIC_API_KEY` | Claude API key | console.anthropic.com → API Keys |
| `APOLLO_API_KEY` | Apollo.io API key | app.apollo.io → Settings → Integrations → API |

### Apollo.io Setup

1. Sign in to [Apollo.io](https://app.apollo.io)
2. Go to **Settings → Integrations → API**
3. Copy your API key
4. Set `APOLLO_API_KEY=your-key` in `backend/.env`

### Gmail Setup (App Password)

Gmail alerts use SMTP with an **App Password** — not your account password.

1. Enable **2-Step Verification** on the sending Gmail account (required for App Passwords)
2. Go to **Google Account → Security → App passwords**
3. Select app: **Mail** / Select device: **Other** → name it "Portfolio Intel"
4. Google generates a 16-character password (e.g. `abcd efgh ijkl mnop`)
5. Set in `backend/.env`:
   ```env
   GMAIL_USER=alerts@yourfirm.com
   GMAIL_APP_PASSWORD=abcdefghijklmnop   # spaces are stripped automatically
   ALERT_EMAIL_RECIPIENTS=partner1@yourfirm.com,partner2@yourfirm.com
   ```

### Full `.env` Reference

```env
# Security
SECRET_KEY=                          # python3 -c "import secrets; print(secrets.token_hex(32))"
ACCESS_TOKEN_EXPIRE_MINUTES=480      # 8-hour sessions

# Database
DATABASE_URL=sqlite:///./portfolio_intel.db

# AI + data
ANTHROPIC_API_KEY=sk-ant-...
APOLLO_API_KEY=...

# Gmail SMTP
GMAIL_USER=alerts@yourfirm.com
GMAIL_APP_PASSWORD=abcdefghijklmnop  # 16-char App Password, spaces stripped automatically
ALERT_EMAIL_RECIPIENTS=partner1@yourfirm.com,partner2@yourfirm.com

# App
FRONTEND_URL=http://localhost:5173   # set to production URL in deployment
DAILY_SCHEDULER_HOUR=8
DAILY_SCHEDULER_MINUTE=0
ENVIRONMENT=development              # set to "production" in deployment
```

## Deployment

### Scheduler — Single Worker Requirement

The daily job uses an in-process `AsyncIOScheduler` and an in-memory `is_running` flag to prevent concurrent runs. This works correctly with a single uvicorn worker (the default).

**Do not run multiple workers** (`--workers 4`, `gunicorn -w 4`) without replacing the in-memory flag with a distributed lock (Redis `SET NX`, database row, etc.). Each worker process has its own scheduler instance and its own copy of `is_running`, so the duplicate-run guard will not fire across processes and every worker will execute the daily job independently.

The Railway deployment in `railway.toml` uses the default single-worker uvicorn invocation — do not add `--workers` to that command.

### Backend → Railway

1. Push to GitHub
2. Create a new Railway project → **Deploy from GitHub repo**
3. Set the **Root Directory** to `backend/`
4. Add all environment variables from your `.env` (Railway → Variables tab)
5. Railway uses `railway.toml` to configure the Dockerfile build automatically
6. For persistent SQLite, add a **Railway Volume** mounted at `/app/data/` and set:
   ```
   DATABASE_URL=sqlite:////app/data/portfolio_intel.db
   ```

> **Tip**: For production, consider upgrading to PostgreSQL. Change `DATABASE_URL` to a Postgres connection string — SQLAlchemy handles it automatically without any code changes.

### Frontend → Vercel

1. Push to GitHub
2. Import the repo in Vercel
3. Set **Root Directory** to `frontend/`
4. Add environment variable: `VITE_API_URL=https://your-backend.railway.app`
5. Deploy — Vercel detects Vite automatically

`vercel.json` handles SPA routing (all paths serve `index.html`).

## API Reference

Interactive Swagger docs at `http://localhost:8000/docs` when running locally.

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/login` | Sign in, returns JWT |
| `GET` | `/auth/me` | Current user |
| `POST` | `/auth/register` | Register new team member |
| `GET` | `/companies` | List portfolio companies |
| `POST` | `/companies` | Add a company |
| `PUT` | `/companies/{id}` | Update a company |
| `DELETE` | `/companies/{id}` | Remove a company |
| `POST` | `/companies/{id}/refresh` | Trigger manual intelligence refresh |
| `GET` | `/signals` | List signals (filterable) |
| `PATCH` | `/signals/{id}` | Update signal (mark read) |
| `POST` | `/signals/mark-all-read` | Mark all signals read |
| `GET` | `/reports` | List generated reports |
| `POST` | `/reports/generate` | Generate report for a specific month/year |
| `POST` | `/reports/generate/current-month` | Generate report for current month |
| `POST` | `/admin/trigger-daily-job` | Manually trigger the intelligence job |

## How Signal Extraction Works

1. **Daily Scheduler** (APScheduler, 8 AM UTC) iterates each active portfolio company
2. **Apollo.io** is queried for current employees and company enrichment data
3. **Claude Sonnet** (`claude-sonnet-4-6`) analyzes the data with a system prompt cached for cost efficiency, extracting signals across 7 categories
4. New signals are **deduplicated** via a SHA-256 hash of `(company_id, type, title[:80])` stored as a unique DB constraint and saved to SQLite
5. Medium/high importance signals trigger **Gmail alerts** to configured recipients
6. Monthly **report generation** via Claude synthesizes all signals into an HTML report emailed to the team

## Signal Types

| Type | Description |
|---|---|
| `new_hire` | Notable people joining the company |
| `departure` | Key people leaving |
| `founder_post` | Significant founder announcements |
| `funding` | Funding rounds, investor news |
| `partnership` | New strategic partnerships |
| `product_launch` | New products or major features |
| `other` | Other notable signals |

## Adding Team Members

Use the `/auth/register` endpoint:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"email":"analyst@firm.com","name":"Jane Smith","password":"secure123","role":"analyst"}'
```

Roles: `analyst`, `partner`, `admin`
