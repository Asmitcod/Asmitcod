
#!/usr/bin/env python3
"""
Render GitHub contribution data into an animated contribution heatmap.

Input:
    data/contributions.json

Output:
    contrib-heatmap.svg

Features:
    - GitHub-style contribution calendar
    - Six-level green contribution palette
    - Diagonal staggered reveal animation
    - Less / More legend
    - Current and longest streak statistics
    - Best contribution day
    - STATIC=1 for frozen previews
"""

import datetime
import html
import json
import os
import sys
from pathlib import Path

# --------------------------------------------------
# Configuration
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent

IN_PATH = ROOT / "data" / "contributions.json"
OUT_PATH = ROOT / "contrib-heatmap.svg"

PALETTE = [
    "#161b22",
    "#0e4429",
    "#006d32",
    "#26a641",
    "#39d353",
    "#69f0a0",
]

CELL = 12
GAP = 3
STEP = CELL + GAP

PAD = 22
LEFT_LABEL_W = 30
TOP_LABEL_H = 22
TITLEBAR_H = 32

BG = "#0a0e14"
BG2 = "#0d1420"
FRAME = "#1f6feb"
MUTED = "#7d8590"
TEXT = "#e6edf3"
ACCENT = "#22d3ee"
GREEN = "#39d353"
GOLD = "#f2cc60"

STATIC = os.getenv("STATIC", "0") == "1"

COL_T = 0.018
ROW_T = 0.045
CELL_DUR = 0.42


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def safe_text(value):
    """Escape text for safe SVG/XML insertion."""
    return html.escape(str(value), quote=True)


def level_for(count):
    """Map contribution count to one of six color levels."""

    if count <= 0:
        return 0
    elif count <= 5:
        return 1
    elif count <= 15:
        return 2
    elif count <= 30:
        return 3
    elif count <= 50:
        return 4

    return 5


def load_data():
    """Load and validate contribution JSON."""

    if not IN_PATH.exists():
        raise FileNotFoundError(
            f"Contribution data not found: {IN_PATH}\n"
            "Run fetch_contributions.py first."
        )

    with open(IN_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    days = data.get("days")

    if not isinstance(days, list) or not days:
        raise ValueError("No contribution days found in JSON.")

    for day in days:
        if "date" not in day or "count" not in day:
            raise ValueError(f"Invalid contribution entry: {day}")

        datetime.date.fromisoformat(day["date"])

        if int(day["count"]) < 0:
            raise ValueError(f"Negative contribution count: {day}")

    days.sort(key=lambda item: item["date"])

    return data


# --------------------------------------------------
# Build calendar grid
# --------------------------------------------------

def build_grid(days):
    """
    Create a Sunday-first calendar grid.

    Missing dates are represented as empty cells.
    Each column represents one week.
    """

    contributions = {}

    for day in days:
        date = datetime.date.fromisoformat(day["date"])
        contributions[date] = int(day["count"])

    first_date = min(contributions)
    last_date = max(contributions)

    # Move to the Sunday before the first date.
    grid_start = first_date - datetime.timedelta(
        days=(first_date.weekday() + 1) % 7
    )

    # Move to the Saturday after the last date.
    grid_end = last_date + datetime.timedelta(
        days=(5 - last_date.weekday()) % 7
    )

    grid = []
    current = grid_start

    while current <= grid_end:

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
    """Find the first visible column of each month."""

    labels = []
    seen = set()

    for ci, column in enumerate(grid):

        for cell in column:

            if cell is None:
                continue

            date = datetime.date.fromisoformat(cell[0])

            key = (date.year, date.month)

            if key not in seen and date.day <= 7:
                seen.add(key)
                labels.append((ci, date.strftime("%b")))

            break

    return labels


# --------------------------------------------------
# Animation CSS
# --------------------------------------------------

def make_css():

    if STATIC:
        return """
        .c {
            opacity: 1;
        }
        """

    return f"""
    @keyframes cell {{
        0% {{
            opacity: 0;
            transform: translateY(-6px);
        }}

        100% {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}

    .c {{
        opacity: 0;
        animation-name: cell;
        animation-duration: {CELL_DUR}s;
        animation-timing-function: cubic-bezier(.2,.8,.2,1);
        animation-fill-mode: both;
    }}
    """


# --------------------------------------------------
# Render contribution cells
# --------------------------------------------------

def render_cells(grid, grid_left, grid_top):

    parts = []

    for ci, column in enumerate(grid):

        gx = grid_left + ci * STEP

        for ri, cell in enumerate(column):

            if cell is None:
                continue

            date_s, count, level = cell

            gy = grid_top + ri * STEP

            delay = ci * COL_T + ri * ROW_T

            animation_style = (
                f' style="animation-delay:{delay:.3f}s"'
                if not STATIC else ""
            )

            plural = "s" if count != 1 else ""

            parts.append(
                f'<rect class="c" '
                f'x="{gx}" y="{gy}" '
                f'width="{CELL}" height="{CELL}" '
                f'rx="2.5" '
                f'fill="{PALETTE[level]}"'
                f'{animation_style}>'
                f'<title>{safe_text(date_s)}: '
                f'{count} contribution{plural}</title>'
                f'</rect>'
            )

    return parts


# --------------------------------------------------
# Main SVG renderer
# --------------------------------------------------

def render(data):

    days = data["days"]

    grid = build_grid(days)

    n_cols = len(grid)

    art_w = n_cols * STEP
    art_h = 7 * STEP

    month_labels = get_month_labels(grid)

    canvas_w = PAD + LEFT_LABEL_W + art_w + PAD

    grid_top = TITLEBAR_H + TOP_LABEL_H
    grid_left = PAD + LEFT_LABEL_W

    # Layout dimensions
    stats_h = 88

    canvas_h = (
        TITLEBAR_H
        + TOP_LABEL_H
        + art_h
        + CELL
        + 14
        + 24
        + stats_h
    )

    css = make_css()

    parts = [

        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{canvas_w}" height="{canvas_h}" '
        f'viewBox="0 0 {canvas_w} {canvas_h}" '
        f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',

        f'<style>{css}</style>',

        '<defs>',

        f'<linearGradient id="hbg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BG2}"/>'
        f'<stop offset="1" stop-color="{BG}"/>'
        '</linearGradient>',

        '</defs>',

        f'<rect width="{canvas_w}" height="{canvas_h}" '
        f'rx="12" fill="url(#hbg)"/>',

        f'<rect x="0.5" y="0.5" '
        f'width="{canvas_w-1}" height="{canvas_h-1}" '
        f'rx="12" fill="none" stroke="{FRAME}" '
        f'stroke-width="1" stroke-opacity="0.55"/>',

        f'<line x1="0" y1="{TITLEBAR_H}" '
        f'x2="{canvas_w}" y2="{TITLEBAR_H}" '
        f'stroke="{FRAME}" stroke-opacity="0.35"/>',
    ]

    # --------------------------------------------------
    # Terminal title bar
    # --------------------------------------------------

    for i, color in enumerate([
        "#ff5f56",
        "#ffbd2e",
        "#27c93f"
    ]):

        parts.append(
            f'<circle cx="{PAD + i*16}" '
            f'cy="{TITLEBAR_H/2}" r="5" fill="{color}"/>'
        )

    username = safe_text(data.get("username", "github"))

    parts.append(
        f'<text x="{canvas_w/2}" '
        f'y="{TITLEBAR_H/2 + 4}" '
        f'fill="{MUTED}" font-size="12" '
        f'text-anchor="middle">'
        f'{username}@github: ~/contributions --graph'
        f'</text>'
    )

    # --------------------------------------------------
    # Month labels
    # --------------------------------------------------

    for ci, label in month_labels:

        x = grid_left + ci * STEP

        parts.append(
            f'<text x="{x}" y="{TITLEBAR_H + 15}" '
            f'fill="{MUTED}" font-size="10">'
            f'{label}</text>'
        )

    # --------------------------------------------------
    # Weekday labels
    # --------------------------------------------------

    for wi, name in [
        (1, "Mon"),
        (3, "Wed"),
        (5, "Fri")
    ]:

        y = grid_top + wi * STEP + CELL * 0.78

        parts.append(
            f'<text x="{PAD}" y="{y:.1f}" '
            f'fill="{MUTED}" font-size="9">'
            f'{name}</text>'
        )

    # --------------------------------------------------
    # Contribution boxes
    # --------------------------------------------------

    parts.extend(
        render_cells(grid, grid_left, grid_top)
    )

    # --------------------------------------------------
    # Less / More legend
    # --------------------------------------------------

    leg_y = grid_top + art_h + 6

    leg_x = (
        canvas_w
        - PAD
        - (len(PALETTE) * (CELL - 1) + 70)
    )

    parts.append(
        f'<text x="{leg_x}" '
        f'y="{leg_y + CELL*0.8:.1f}" '
        f'fill="{MUTED}" font-size="10" '
        f'text-anchor="end">Less</text>'
    )

    lx = leg_x + 8

    for color in PALETTE:

        parts.append(
            f'<rect x="{lx}" y="{leg_y}" '
            f'width="{CELL-1}" height="{CELL-1}" '
            f'rx="2.2" fill="{color}"/>'
        )

        lx += CELL

    parts.append(
        f'<text x="{lx + 4}" '
        f'y="{leg_y + CELL*0.8:.1f}" '
        f'fill="{MUTED}" font-size="10">More</text>'
    )

    # --------------------------------------------------
    # Statistics footer
    # --------------------------------------------------

    sep_y = leg_y + CELL + 14

    parts.append(
        f'<line x1="0" y1="{sep_y}" '
        f'x2="{canvas_w}" y2="{sep_y}" '
        f'stroke="{FRAME}" stroke-opacity="0.25"/>'
    )

    current = data.get("current_streak", {})
    longest = data.get("longest_streak", {})
    best = data.get("best_day", {})
    date_range = data.get("range", {})

    total = int(data.get("total_contributions", 0))
    active = int(data.get("active_days", 0))

    cs = int(current.get("length", 0))
    ls = int(longest.get("length", 0))

    ly = sep_y + 24

    # Total contributions
    parts.append(
        f'<text x="{PAD}" y="{ly}" '
        f'font-size="13" fill="{GREEN}">'
        f'<tspan font-weight="700">{total:,}</tspan>'
        f'<tspan fill="{MUTED}">'
        f' contributions in the last year'
        f'</tspan></text>'
    )

    parts.append(
        f'<text x="{canvas_w-PAD}" y="{ly}" '
        f'font-size="12" fill="{MUTED}" '
        f'text-anchor="end">'
        f'{safe_text(date_range.get("start", ""))} '
        f'&#8594; '
        f'{safe_text(date_range.get("end", ""))}'
        f'</text>'
    )

    ly += 24

    # Streaks
    parts.append(
        f'<text x="{PAD}" y="{ly}" '
        f'font-size="13" fill="{MUTED}">'
        f'current streak '
        f'<tspan fill="{ACCENT}" font-weight="700">'
        f'{cs} days</tspan>'
        f'<tspan fill="{MUTED}">   &#183;   longest </tspan>'
        f'<tspan fill="{ACCENT}" font-weight="700">'
        f'{ls} days</tspan>'
        f'</text>'
    )

    # Best day
    best_date = safe_text(best.get("date", "N/A"))
    best_count = int(best.get("count", 0))

    parts.append(
        f'<text x="{canvas_w-PAD}" y="{ly}" '
        f'font-size="12" fill="{MUTED}" '
        f'text-anchor="end">'
        f'best day '
        f'<tspan fill="{GOLD}" font-weight="700">'
        f'{best_count}</tspan>'
        f' on {best_date}</text>'
    )

    # Active days
    ly += 22

    parts.append(
        f'<text x="{PAD}" y="{ly}" '
        f'font-size="11" fill="{MUTED}">'
        f'{active} active days'
        f'</text>'
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

        print("Rendering contribution heatmap...")

        svg = render(data)

        OUT_PATH.write_text(svg, encoding="utf-8")

        print("\nSuccessfully generated heatmap!")
        print(f"Output: {OUT_PATH}")
        print(f"Size: {len(svg):,} bytes")
        print(f"Static mode: {STATIC}")

    except Exception as error:

        print(f"\nERROR: {error}", file=sys.stderr)
        sys.exit(1)
