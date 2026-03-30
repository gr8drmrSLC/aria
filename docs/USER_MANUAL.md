# ARIA User Manual

**Version:** 0.1.0
**Last updated:** 2026-03-29

---

## Overview

ARIA (Autonomous Research Intelligence Agent) is a pipeline that monitors arXiv research
submissions daily, analyzes them using Claude AI, detects anomalies autonomously, and
publishes structured intelligence briefs when significant activity is detected.

---

## Installation

### Prerequisites

- Python 3.11 or higher
- An Anthropic API key (get one at console.anthropic.com)
- ~50MB disk space for the SQLite database after a week of operation

### Steps

```bash
git clone https://github.com/gr8drmrSLC/aria.git
cd aria
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set `ANTHROPIC_API_KEY=sk-ant-...`

---

## Running ARIA

### Run once (test / manual trigger)

```bash
python runner.py --once
```

This runs the full pipeline immediately — ingest, analyze, decide, report — then exits.
Check `logs/aria.log` for the full run trace.

### Run on a daily schedule

```bash
python runner.py               # Runs daily at 07:00 UTC (default)
python runner.py --hour 9     # Runs daily at 09:00 UTC
```

Leave this process running in a terminal or under a process manager (see Deployment below).

### Start the dashboard

```bash
python dashboard/app.py
```

Open `http://localhost:5050` in a browser.

---

## Dashboard

The dashboard has three sections:

**Stat strip (masthead)**
- Papers Today — how many papers were ingested in the most recent run
- Reports Filed — total intelligence briefs published since setup
- In Feed (48h) — papers visible in the live feed

**Intelligence Reports**
- Published reports shown as newspaper-column cards
- Each card shows the date, trigger tags (color-coded by type), and paper count
- Click any card to read the full brief

**Live Paper Feed**
- All papers ingested in the last 48 hours
- Each row shows title (links to arXiv), novelty score with bar, and category tags
- Papers are sorted newest-first

**Report detail page** (`/reports/<id>`)
- Full markdown brief rendered with section headers, a notable papers table, and analyst note
- Back link to main dashboard

**API endpoints** (for integrations or debugging):
- `GET /api/papers` — last 24 hours of papers as JSON
- `GET /api/reports` — last 20 reports as JSON
- `GET /api/stats` — papers today, total reports, avg novelty

---

## The four anomaly triggers

ARIA publishes a report when ANY of these fire:

| Trigger | Fires when | Default threshold |
|---------|-----------|-------------------|
| Volume Spike | Today's paper count > baseline mean × 1.5 | 1.5x |
| Cross-Domain Cluster | 3+ papers bridge multiple domains (AI + bio/robotics) | 3 papers |
| Novelty Burst | >30% of papers score ≥ 7 | 30% |
| Significance Surge | Avg novelty score > baseline avg × 1.3 | 1.3x |

Thresholds are tunable via environment variables — see `.env.example`.

**Note:** For the first 30 days, baseline-dependent triggers (Volume Spike, Significance Surge)
have no historical data to compare against and will not fire. Cross-Domain and Novelty Burst
triggers are active from day one.

---

## Tuning

### Too many reports
Raise the thresholds in `.env`:
```
ARIA_VOLUME_SPIKE=2.0
ARIA_NOVELTY_BURST_PCT=0.40
ARIA_SIGNIFICANCE_SURGE=1.5
ARIA_CROSS_DOMAIN_MIN=5
```

### Too few reports
Lower the thresholds or reduce `ARIA_NOVELTY_THRESHOLD` (default 7) to flag more papers.

### Changing monitored categories
Edit `MONITORED_CATEGORIES` in `core/ingest.py`. Add any valid arXiv category code.

---

## Deployment on EC2

### Setup

```bash
# On your EC2 instance
git clone https://github.com/gr8drmrSLC/aria.git
cd aria
pip install -r requirements.txt
cp .env.example .env && nano .env
```

### Run as a systemd service (pipeline)

Create `/etc/systemd/system/aria.service`:

```ini
[Unit]
Description=ARIA Research Intelligence Agent
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/aria
EnvironmentFile=/home/ubuntu/aria/.env
ExecStart=/usr/bin/python3 runner.py
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable aria
sudo systemctl start aria
sudo systemctl status aria
```

### Run as a systemd service (dashboard)

Create `/etc/systemd/system/aria-dashboard.service`:

```ini
[Unit]
Description=ARIA Dashboard
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/aria
EnvironmentFile=/home/ubuntu/aria/.env
ExecStart=/usr/bin/python3 dashboard/app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable aria-dashboard
sudo systemctl start aria-dashboard
```

### Expose dashboard (optional — nginx reverse proxy)

```nginx
server {
    listen 80;
    server_name your-ec2-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Logs

Pipeline log: `logs/aria.log`

```bash
tail -f logs/aria.log                   # Follow live
grep "Decision:" logs/aria.log          # See all run decisions
grep "Trigger fired:" logs/aria.log     # See all trigger activations
grep "Report #" logs/aria.log           # See published reports
```

---

## Database inspection

```bash
sqlite3 data/aria.db
.tables
SELECT count(*) FROM papers;
SELECT title, novelty_score FROM papers ORDER BY novelty_score DESC LIMIT 10;
SELECT title, created_at FROM reports;
.quit
```

---

## Troubleshooting

**No papers fetched**
arXiv submissions are typically available after 18:00 ET on submission days (Mon–Fri).
Run after 00:00 UTC to reliably catch the previous day's submissions.

**Claude API errors**
Check that `ANTHROPIC_API_KEY` is set correctly. The reporter has a fallback mode that
generates a minimal report without Claude if the API is unavailable.

**Dashboard shows no data**
Run `python runner.py --once` first to populate the database, then start the dashboard.

**Baselines are empty (no Volume Spike / Significance Surge triggers)**
This is expected for the first 30 days. The baseline triggers need historical data.
Cross-Domain and Novelty Burst triggers are active immediately.
