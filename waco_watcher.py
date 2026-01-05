#!/usr/bin/env python3
"""Waco Surf availability watcher - sends email alerts when surf sessions open up."""

import json
import os
import smtplib
import sys
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests

BASE_URL = "https://fareharbor.com"
FLOW = "784809"


def get_config():
    """Load configuration from environment variables."""
    return {
        "start_date": os.environ.get("DATE_RANGE_START"),
        "end_date": os.environ.get("DATE_RANGE_END"),
        "emails": [e.strip() for e in os.environ.get("EMAIL_RECIPIENTS", "").split(",") if e.strip()],
        "smtp_user": os.environ.get("SMTP_USER"),
        "smtp_pass": os.environ.get("SMTP_PASS"),
        "use_mock": os.environ.get("USE_MOCK_DATA", "").lower() == "true",
    }


def date_range(start: date, end: date):
    """Yield dates from start to end inclusive."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def fetch_availabilities(d: date, use_mock: bool = False) -> list[dict]:
    """Fetch availability data for a single day from FareHarbor."""
    if use_mock:
        mock_file = Path(__file__).parent / "mock_data.json"
        if mock_file.exists():
            with open(mock_file) as f:
                mock = json.load(f)
                return [a for a in mock.get("availabilities", []) if a.get("start_at", "").startswith(d.isoformat())]
        return []

    url = f"{BASE_URL}/api/v1/companies/wacosurf/search/availabilities/date/{d.isoformat()}/"
    params = {"allow_grouped": "yes", "bookable_only": "yes", "flow": FLOW}
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json().get("availabilities", [])


def find_available_slots(start: date, end: date, use_mock: bool = False) -> list[dict]:
    """Find all bookable slots in the date range."""
    slots = []
    for d in date_range(start, end):
        for av in fetch_availabilities(d, use_mock):
            if not av.get("is_bookable"):
                continue
            item = av.get("item", {})
            start_at = av.get("start_at", "")
            book_url = av.get("book_url", "")
            slots.append({
                "date": start_at[:10],
                "time": datetime.fromisoformat(start_at).strftime("%-I:%M %p") if start_at else "",
                "sort_key": start_at,
                "session": item.get("name", "Unknown"),
                "capacity": av.get("bookable_capacity"),
                "book_url": f"{BASE_URL}{book_url}" if book_url else "",
            })
    return sorted(slots, key=lambda x: x["sort_key"])


def format_email_html(slots: list[dict], start_date: str, end_date: str) -> str:
    """Generate HTML email body."""
    rows = "\n".join(
        f"""<tr>
            <td style="padding:8px;border-bottom:1px solid #ddd;">{s['date']}</td>
            <td style="padding:8px;border-bottom:1px solid #ddd;">{s['time']}</td>
            <td style="padding:8px;border-bottom:1px solid #ddd;">{s['session']}</td>
            <td style="padding:8px;border-bottom:1px solid #ddd;">{s['capacity']} spots</td>
            <td style="padding:8px;border-bottom:1px solid #ddd;">
                <a href="{s['book_url']}" style="color:#0066cc;">Book Now</a>
            </td>
        </tr>"""
        for s in slots
    )
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:system-ui,sans-serif;max-width:800px;margin:0 auto;padding:20px;">
    <h2 style="color:#2563eb;">🏄 Waco Surf Slots Available!</h2>
    <p>Found <strong>{len(slots)}</strong> available session(s) between {start_date} and {end_date}:</p>
    <table style="border-collapse:collapse;width:100%;margin:20px 0;">
        <thead>
            <tr style="background:#f3f4f6;">
                <th style="padding:10px;text-align:left;border-bottom:2px solid #ddd;">Date</th>
                <th style="padding:10px;text-align:left;border-bottom:2px solid #ddd;">Time</th>
                <th style="padding:10px;text-align:left;border-bottom:2px solid #ddd;">Session</th>
                <th style="padding:10px;text-align:left;border-bottom:2px solid #ddd;">Availability</th>
                <th style="padding:10px;text-align:left;border-bottom:2px solid #ddd;">Action</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    <p style="color:#666;font-size:14px;">
        Book quickly - these spots go fast!<br>
        <a href="https://fareharbor.com/embeds/book/wacosurf/?flow=784809">Browse all availability</a>
    </p>
</body>
</html>"""


def format_email_text(slots: list[dict], start_date: str, end_date: str) -> str:
    """Generate plain text email body."""
    lines = [f"🏄 Waco Surf Slots Available!", "", f"Found {len(slots)} available session(s) between {start_date} and {end_date}:", ""]
    for s in slots:
        lines.append(f"• {s['date']} @ {s['time']} - {s['session']} ({s['capacity']} spots)")
        lines.append(f"  Book: {s['book_url']}")
        lines.append("")
    lines.append("Book quickly - these spots go fast!")
    return "\n".join(lines)


def send_email(recipients: list[str], slots: list[dict], start_date: str, end_date: str, smtp_user: str, smtp_pass: str):
    """Send notification email via Gmail SMTP."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🏄 {len(slots)} Waco Surf Slot(s) Available ({start_date} - {end_date})"
    msg["From"] = smtp_user
    msg["To"] = ", ".join(recipients)

    msg.attach(MIMEText(format_email_text(slots, start_date, end_date), "plain"))
    msg.attach(MIMEText(format_email_html(slots, start_date, end_date), "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(smtp_user, smtp_pass.replace('\xa0', ' '))  # Fix non-breaking spaces from copy-paste
        server.sendmail(smtp_user, recipients, msg.as_string())
    print(f"Email sent to {', '.join(recipients)}")


def main():
    config = get_config()

    if not config["start_date"] or not config["end_date"]:
        print("Error: DATE_RANGE_START and DATE_RANGE_END must be set")
        sys.exit(1)

    if not config["emails"]:
        print("Error: EMAIL_RECIPIENTS must be set")
        sys.exit(1)

    start = datetime.strptime(config["start_date"], "%Y-%m-%d").date()
    end = datetime.strptime(config["end_date"], "%Y-%m-%d").date()

    print(f"Checking Waco Surf availability from {start} to {end}...")
    print(f"Mock mode: {config['use_mock']}")

    slots = find_available_slots(start, end, config["use_mock"])

    if not slots:
        print("No available slots found.")
        return

    print(f"Found {len(slots)} available slot(s)!")

    if not config["smtp_user"] or not config["smtp_pass"]:
        print("SMTP credentials not configured - printing results only:")
        for s in slots:
            print(f"  {s['date']} @ {s['time']} - {s['session']} ({s['capacity']} spots) - {s['book_url']}")
        return

    send_email(config["emails"], slots, config["start_date"], config["end_date"], config["smtp_user"], config["smtp_pass"])


if __name__ == "__main__":
    main()

