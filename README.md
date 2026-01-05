# Waco Surf Availability Watcher

Monitors [Waco Surf](https://www.wacosurf.com/) for available surf sessions and sends email alerts when slots open up.

## Setup

### 1. Fork/Clone this repo

### 2. Configure GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Description | Example |
|--------|-------------|---------|
| `DATE_RANGE_START` | Start of date range to watch (YYYY-MM-DD) | `2026-03-01` |
| `DATE_RANGE_END` | End of date range to watch (YYYY-MM-DD) | `2026-04-30` |
| `EMAIL_RECIPIENTS` | Comma-separated email addresses | `you@email.com,friend@email.com` |
| `SMTP_USER` | Gmail address for sending | `your.alerts@gmail.com` |
| `SMTP_PASS` | Gmail App Password (not your regular password) | `abcd efgh ijkl mnop` |
| `USE_MOCK_DATA` | Set to `true` to test with mock data | `false` |

### 3. Gmail App Password Setup

1. Enable 2-Factor Authentication on your Gmail account
2. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
3. Create a new app password for "Mail"
4. Use this 16-character password as `SMTP_PASS`

### 4. Enable the Workflow

The workflow runs hourly by default. You can also trigger it manually from the Actions tab.

## Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Test with mock data (no email)
DATE_RANGE_START=2026-03-01 DATE_RANGE_END=2026-04-30 \
EMAIL_RECIPIENTS=test@example.com USE_MOCK_DATA=true \
python waco_watcher.py

# Test with real SMTP
DATE_RANGE_START=2026-03-01 DATE_RANGE_END=2026-04-30 \
EMAIL_RECIPIENTS=your@email.com \
SMTP_USER=alerts@gmail.com SMTP_PASS="your-app-password" \
USE_MOCK_DATA=true \
python waco_watcher.py
```

## How It Works

1. Queries FareHarbor's API for each day in the configured range
2. Filters for bookable sessions with available capacity
3. Sends a formatted HTML email with booking links if slots are found
4. Does nothing if no availability (no spam!)

