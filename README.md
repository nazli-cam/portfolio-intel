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

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your API keys (see Configuration below)

uvicorn app.main:app --reload
# API available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

Default login: `admin@portfoliointel.com` / `changeme123`

### Frontend

```bash
cd frontend
npm install

cp .env.example .env
# VITE_API_URL=http://localhost:8000

npm run dev
# App available at http://localhost:5173
```

## Configuration

### Required API Keys

| Variable | Description | Where to get it |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude API key | console.anthropic.com |
| `APOLLO_API_KEY` | Apollo.io API key | apollo.io → Settings → API |
| `SECRET_KEY` | JWT signing key | `python -c "import secrets; print(secrets.token_hex(32))"` |

### Gmail Setup (for email alerts)

1. Go to Google Cloud Console and create a project
2. Enable the **Gmail API**
3. Create **OAuth2 credentials** (Desktop app type)
4. Set `GMAIL_CLIENT_ID` and `GMAIL_CLIENT_SECRET` in `.env`
5. Run the setup script to get your refresh token:
   ```bash
   cd backend
   python scripts/gmail_setup.py
   ```
6. Copy the printed refresh token to `GMAIL_REFRESH_TOKEN` in `.env`
7. Set `GMAIL_SENDER_EMAIL` and `ALERT_EMAIL_RECIPIENTS`

### Full `.env` Reference

```env
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=480

DATABASE_URL=sqlite:///./portfolio_intel.db

ANTHROPIC_API_KEY=sk-ant-...
APOLLO_API_KEY=your-apollo-key

GMAIL_CLIENT_ID=...apps.googleusercontent.com
GMAIL_CLIENT_SECRET=GOCSPX-...
GMAIL_REFRESH_TOKEN=1//...
GMAIL_SENDER_EMAIL=alerts@yourfirm.com
ALERT_EMAIL_RECIPIENTS=partner1@yourfirm.com,partner2@yourfirm.com

FRONTEND_URL=https://your-app.vercel.app
DAILY_SCHEDULER_HOUR=8
DAILY_SCHEDULER_MINUTE=0
```

## Deployment

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
