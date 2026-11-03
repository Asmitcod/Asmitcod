
#!/usr/bin/env python3
"""
Render a clean GitHub-style contribution heatmap.

Input:  data/contributions.json
Output: contrib-heatmap.svg

Features:
- Minimal dark background
- Rounded GitHub-style contribution cells
- Month and weekday labels
- Contribution total
- Staggered one-time animation
- STATIC=1 for frozen previews
"""

import datetime
import html
import json
import os
from pathlib import Path

# --------------------------------------------------
# Paths and configuration
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent

IN_PATH = ROOT / "data" / "contributions.json"
OUT_PATH = ROOT / "contrib-heatmap.svg"

STATIC = os.getenv("STATIC", "0") == "1"

BG = "#0d1117"
EMPTY = "#161b22"
PALETTE = [
    EMPTY,
    "#0e4429",
    "#006d32",
    "#26a641",
    "#39d353",
]

TEXT = "#f0f6fc"
MUTED = "#848d97"

CELL = 15
GAP = 4
STEP = CELL + GAP

PAD_X = 30
PAD_TOP = 28
LEFT_LABEL_W = 40

COL_T = 0.015
ROW_T = 0.035
CELL_DUR = 0.4


# --------------------------------------------------
# Contribution levels
# --------------------------------------------------

def level_for(count):

    if count <= 0:
        return 0
    if count <= 5:
        return 1
    if count <= 15:
        return 2
    if count <= 30:
        return 3

    return 4


# --------------------------------------------------
# Load data
# --------------------------------------------------

def load_data():

    if not IN_PATH.exists():
        raise FileNotFoundError(
            f"Missing {IN_PATH}. Run fetch_contributions.py first."
        )

    with open(IN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    days = data.get("days", [])

    if not days:
        raise ValueError("No contribution data available.")

    seen_dates = set()

    for day in days:
        date = datetime.date.fromisoformat(day["date"])
        count = int(day["count"])

        if count < 0:
            raise ValueError(f"Invalid contribution count: {count}")

        if date in seen_dates:
            raise ValueError(f"Duplicate contribution date: {date}")

        seen_dates.add(date)

    days.sort(key=lambda d: d["date"])

    return data


# --------------------------------------------------
# Build calendar grid
# --------------------------------------------------

def build_grid(days):

    contributions = {
        datetime.date.fromisoformat(d["date"]): int(d["count"])
        for d in days
    }

    first = min(contributions)
    last = max(contributions)

    # Sunday-first calendar
    start = first - datetime.timedelta(
        days=(first.weekday() + 1) % 7
    )

    end = last + datetime.timedelta(
        days=(5 - last.weekday()) % 7
    )

    grid = []
    current = start

    while current <= end:

        column = []

        for _ in range(7):

            count = contributions.get(current)

            if count is None:
                column.append(None)
            else:
                column.append((
                    current.isoformat(),
                    count,
                    level_for(count)
                ))

            current += datetime.timedelta(days=1)

        grid.append(column)

    return grid


# --------------------------------------------------
# Month labels
# --------------------------------------------------

def get_month_labels(grid):

    labels = []
    previous_month = None

    for ci, column in enumerate(grid):

        for cell in column:

            if cell is None:
                continue

            date = datetime.date.fromisoformat(cell[0])

            key = (date.year, date.month)

            if key != previous_month:
                labels.append((ci, date.strftime("%b")))
                previous_month = key

            break

    return labels


# --------------------------------------------------
# Animation
# --------------------------------------------------

def make_css():

    if STATIC:
        return ".cell { opacity: 1; }"

    return f"""
    @keyframes reveal {{
        from {{
            opacity: 0;
            transform: translateY(-5px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}

    .cell {{
        opacity: 0;
        animation: reveal {CELL_DUR}s ease-out both;
    }}

    @media (prefers-reduced-motion: reduce) {{
        .cell {{
            animation: none;
            opacity: 1;
        }}
    }}
    """


# --------------------------------------------------
# Render SVG
# --------------------------------------------------

def render(data):

    days = data["days"]

    grid = build_grid(days)
    month_labels = get_month_labels(grid)

    columns = len(grid)

    grid_left = PAD_X + LEFT_LABEL_W
    grid_top = PAD_TOP + 40

    grid_width = columns * STEP
    grid_height = 7 * STEP

    width = grid_left + grid_width + PAD_X
    height = grid_top + grid_height + 55

    parts = []

    # SVG opening
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'font-family="Arial, Helvetica, sans-serif">'
    )

    parts.append(f'<style>{make_css()}</style>')

    # Plain dark background
    parts.append(
        f'<rect width="{width}" height="{height}" fill="{BG}"/>'
    )

    # Heading
    parts.append(
        f'<text x="{width/2}" y="29" '
        f'text-anchor="middle" '
        f'font-size="20" font-weight="bold" '
        f'fill="{TEXT}">'
        f'GitHub Contributions'
        f'</text>'
    )

    # Month labels
    for ci, month in month_labels:

        x = grid_left + ci * STEP

        parts.append(
            f'<text x="{x}" y="{grid_top - 13}" '
            f'font-size="13" fill="{MUTED}">'
            f'{month}</text>'
        )

    # Weekday labels
    for ri, name in [
        (1, "Mon"),
        (3, "Wed"),
        (5, "Fri")
    ]:

        y = grid_top + ri * STEP + CELL - 2

        parts.append(
            f'<text x="{PAD_X}" y="{y}" '
            f'font-size="12" fill="{MUTED}">'
            f'{name}</text>'
        )

    # Contribution cells
    for ci, column in enumerate(grid):

        for ri, cell in enumerate(column):

            if cell is None:
                continue

            date_s, count, level = cell

            x = grid_left + ci * STEP
            y = grid_top + ri * STEP

            delay = ci * COL_T + ri * ROW_T

            style = (
                f' style="animation-delay:{delay:.3f}s"'
                if not STATIC else ""
            )

            plural = "s" if count != 1 else ""

            parts.append(
                f'<rect class="cell" '
                f'x="{x}" y="{y}" '
                f'width="{CELL}" height="{CELL}" '
                f'rx="3" '
                f'fill="{PALETTE[level]}"'
                f'{style}>'
                f'<title>{html.escape(date_s)}: '
                f'{count} contribution{plural}</title>'
                f'</rect>'
            )

    # Contribution total
    total = int(data.get("total_contributions", 0))

    footer_y = grid_top + grid_height + 25

    parts.append(
        f'<text x="{grid_left}" y="{footer_y}" '
        f'font-size="16" font-weight="bold" '
        f'fill="{TEXT}">'
        f'{total:,} contributions in the last year'
        f'</text>'
    )

    # Less / More legend
    legend_y = footer_y + 22

    legend_width = 6 * (CELL - 1) + 70

    legend_x = width - PAD_X - legend_width

    parts.append(
        f'<text x="{legend_x}" y="{legend_y + 11}" '
        f'font-size="11" fill="{MUTED}" '
        f'text-anchor="end">Less</text>'
    )

    lx = legend_x + 8

    for color in PALETTE:

        parts.append(
            f'<rect x="{lx}" y="{legend_y}" '
            f'width="{CELL-1}" height="{CELL-1}" '
            f'rx="2" fill="{color}"/>'
        )

        lx += CELL

    parts.append(
        f'<text x="{lx + 4}" y="{legend_y + 11}" '
        f'font-size="11" fill="{MUTED}">More</text>'
    )

    parts.append("</svg>")

    return "\n".join(parts)


# --------------------------------------------------
# Main
# --------------------------------------------------

if __name__ == "__main__":

    try:

        print("Loading contribution data...")

        data = load_data()

        print("Rendering clean GitHub-style heatmap...")

        svg = render(data)

        OUT_PATH.write_text(svg, encoding="utf-8")

        print("\nHeatmap generated successfully!")
        print(f"File: {OUT_PATH}")
        print(f"Size: {len(svg):,} bytes")
        print(f"Static mode: {STATIC}")

    except Exception as error:

        print(f"ERROR: {error}")
        raise SystemExit(1)
