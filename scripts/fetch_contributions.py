
#!/usr/bin/env python3
"""
Fetch public GitHub contribution data and generate:
data/contributions.json

No GitHub token or authentication required.
"""

import datetime
import json
import os
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# --------------------------------------------------
# Configuration
# --------------------------------------------------

USERNAME = os.getenv("GH_PROFILE_USER", "Asmitcod").strip()

URL = f"https://github.com/users/{USERNAME}/contributions"

ROOT_DIR = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT_DIR / "data" / "contributions.json"

HEADERS = {
    "User-Agent": "profile-readme-bot/1.0",
    "Accept": "text/html",
}


# --------------------------------------------------
# Fetch contribution calendar
# --------------------------------------------------

def fetch_days():
    try:
        response = requests.get(
            URL,
            headers=HEADERS,
            timeout=30
        )
        response.raise_for_status()

    except requests.RequestException as error:
        print(f"GitHub request failed: {error}", file=sys.stderr)
        sys.exit(1)

    soup = BeautifulSoup(response.text, "html.parser")

    cells = soup.select("td.ContributionCalendar-day")

    if not cells:
        print(
            "ERROR: No contribution cells found. "
            "GitHub may have changed its HTML structure.",
            file=sys.stderr
        )
        sys.exit(1)

    days = []

    for td in cells:
        date = td.get("data-date")

        if not date:
            continue

        try:
            datetime.date.fromisoformat(date)
        except ValueError:
            print(f"Invalid contribution date: {date}", file=sys.stderr)
            continue

        td_id = td.get("id")

        tooltip = (
            soup.find("tool-tip", attrs={"for": td_id})
            if td_id else None
        )

        tooltip_text = (
            tooltip.get_text(" ", strip=True)
            if tooltip else ""
        )

        # Fallback to accessible labels if tooltip is unavailable.
        if not tooltip_text:
            tooltip_text = (
                td.get("aria-label")
                or td.get("title")
                or ""
            )

        # Extract actual contribution count.
        if re.search(r"no contributions", tooltip_text, re.I):
            count = 0

        else:
            match = re.search(
                r"(\d[\d,]*)\s+contributions?",
                tooltip_text,
                re.I
            )

            if match:
                count = int(match.group(1).replace(",", ""))

            elif int(td.get("data-level") or 0) == 0:
                # Level zero means no contributions.
                count = 0

            else:
                print(
                    f"WARNING: Could not parse count for {date}: "
                    f"{tooltip_text!r}",
                    file=sys.stderr
                )
                continue

        days.append({
            "date": date,
            "count": count,
            "level": int(td.get("data-level") or 0)
        })

    days.sort(key=lambda day: day["date"])

    if not days:
        print("ERROR: No valid contribution days found.", file=sys.stderr)
        sys.exit(1)

    # Detect missing dates rather than silently producing incorrect streaks.
    for previous, current in zip(days, days[1:]):
        previous_date = datetime.date.fromisoformat(previous["date"])
        current_date = datetime.date.fromisoformat(current["date"])

        if (current_date - previous_date).days != 1:
            print(
                f"WARNING: Missing calendar dates between "
                f"{previous['date']} and {current['date']}",
                file=sys.stderr
            )

    return days


# --------------------------------------------------
# Current streak
# --------------------------------------------------

def compute_current_streak(days):

    if not days:
        return 0, None, None

    idx = len(days) - 1

    today = datetime.datetime.now(
        datetime.timezone.utc
    ).date().isoformat()

    # Ignore today only when it has zero contributions.
    # Today may still be in progress.
    if days[idx]["date"] == today and days[idx]["count"] == 0:
        idx -= 1

    streak = 0
    end_idx = idx

    while idx >= 0 and days[idx]["count"] > 0:
        streak += 1
        idx -= 1

    if streak == 0:
        return 0, None, None

    start_idx = idx + 1

    return (
        streak,
        days[start_idx]["date"],
        days[end_idx]["date"]
    )


# --------------------------------------------------
# Longest streak
# --------------------------------------------------

def compute_longest_streak(days):

    longest = 0
    run = 0

    longest_start = None
    longest_end = None

    run_start_idx = None

    for i, day in enumerate(days):

        if day["count"] > 0:

            if run == 0:
                run_start_idx = i

            run += 1

            if run > longest:
                longest = run
                longest_start = days[run_start_idx]["date"]
                longest_end = day["date"]

        else:
            run = 0

    return longest, longest_start, longest_end


# --------------------------------------------------
# Build contribution statistics
# --------------------------------------------------

def build_data(days):

    if not days:
        raise ValueError("Cannot build statistics from empty data.")

    total = sum(day["count"] for day in days)

    active_days = sum(
        1 for day in days if day["count"] > 0
    )

    best = max(
        days,
        key=lambda day: day["count"]
    )

    cur_len, cur_start, cur_end = compute_current_streak(days)

    long_len, long_start, long_end = compute_longest_streak(days)

    # Monthly contribution totals
    monthly = {}

    for day in days:

        month = day["date"][:7]

        monthly[month] = (
            monthly.get(month, 0) + day["count"]
        )

    monthly_list = [
        {
            "month": month,
            "total": count
        }
        for month, count in sorted(monthly.items())
    ]

    return {
        "username": USERNAME,

        "generated_at": datetime.datetime.now(
            datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ"),

        "range": {
            "start": days[0]["date"],
            "end": days[-1]["date"]
        },

        "total_contributions": total,

        "active_days": active_days,

        "avg_per_active_day": round(
            total / active_days, 1
        ) if active_days else 0,

        "current_streak": {
            "length": cur_len,
            "start": cur_start,
            "end": cur_end
        },

        "longest_streak": {
            "length": long_len,
            "start": long_start,
            "end": long_end
        },

        "best_day": {
            "date": best["date"],
            "count": best["count"]
        },

        "monthly": monthly_list,

        "days": days
    }


# --------------------------------------------------
# Main
# --------------------------------------------------

if __name__ == "__main__":

    print(f"Fetching contributions for Asmitcod...")

    days = fetch_days()

    data = build_data(days)

    OUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(OUT_PATH, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )

    print("\nSuccessfully generated contribution data!")
    print(f"Output: {OUT_PATH}")
    print(f"Total contributions: {data['total_contributions']}")
    print(f"Active days: {data['active_days']}")
    print(f"Current streak: {data['current_streak']['length']} days")
    print(f"Longest streak: {data['longest_streak']['length']} days")
    print(
        f"Best day: {data['best_day']['date']} "
        f"({data['best_day']['count']} contributions)"
    )
