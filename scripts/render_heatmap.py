#!/usr/bin/env python3
"""
Render a clean GitHub-style contribution heatmap.

Input:  data/contributions.json
Output: contrib-heatmap.svg

Animation:
1. Opening: cells reveal from left to right (plays once).
2. Streak comet: after the opening finishes, a glowing head travels cell by
   cell along your longest streak, leaving a fading trail, and then repeats.

STATIC=1 gives a frozen frame (no animation, no comet) for previews.
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

# Opening reveal (left to right)
COL_T = 0.015
ROW_T = 0.035
CELL_DUR = 0.4

# Streak comet
COMET_GLOW = "#39d353"      # soft halo around the lit cell
COMET_CORE = "#c9ffd9"      # bright core of the lit cell
COMET_WAIT = 0.5            # seconds to wait after the opening before the comet starts
COMET_TARGET = 4.0          # seconds for the head to cross the whole streak
COMET_MIN_STEP = 0.03       # fastest hop between cells (long streaks)
COMET_MAX_STEP = 0.25       # slowest hop between cells (short streaks)
COMET_HEAD = 0.10           # seconds for a cell to flare up to full brightness
COMET_TRAIL_CELLS = 8       # how many cells long the fading tail is
COMET_TRAIL_MAX = 1.2       # cap on tail duration in seconds
COMET_PAUSE = 2.0           # rest between loops


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
# Longest streak
# --------------------------------------------------

def longest_streak(days):
    """Return the dates of the longest run of consecutive active days.

    On a tie, the most recent streak wins.
    """

    best = []
    run = []

    for d in sorted(days, key=lambda d: d["date"]):

        date = datetime.date.fromisoformat(d["date"])

        if int(d["count"]) <= 0:
            run = []
            continue

        if run and (date - run[-1]).days == 1:
            run.append(date)
        else:
            run = [date]

        if len(run) >= len(best):
            best = list(run)

    return best


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
# Comet timing
# --------------------------------------------------

def comet_timing(columns, n_cells):
    """Work out when the comet starts, how fast it hops and how long a loop is."""

    reveal_end = (columns - 1) * COL_T + 6 * ROW_T + CELL_DUR
    start = reveal_end + COMET_WAIT

    step = COMET_TARGET / max(n_cells, 1)
    step = max(COMET_MIN_STEP, min(COMET_MAX_STEP, step))

    trail = min(COMET_TRAIL_CELLS * step, COMET_TRAIL_MAX)

    cycle = (n_cells - 1) * step + COMET_HEAD + trail + COMET_PAUSE

    return start, step, trail, cycle


# --------------------------------------------------
# Animation
# --------------------------------------------------

def make_css(comet=None):

    if STATIC:
        return ".cell { opacity: 1; }"

    css = f"""
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
    """

    reduced = ".cell { animation: none; opacity: 1; }"

    if comet:

        _, _, trail, cycle = comet

        p_head = COMET_HEAD / cycle * 100
        p_mid = (COMET_HEAD + trail * 0.35) / cycle * 100
        p_end = (COMET_HEAD + trail) / cycle * 100

        # Every streak cell shares this keyframe and cycle length; only the
        # animation-delay differs, which is what makes the head "travel".
        css += f"""
    @keyframes comet {{
        0%            {{ opacity: 0;  transform: scale(1); }}
        {p_head:.3f}% {{ opacity: 1;  transform: scale(1.18); }}
        {p_mid:.3f}%  {{ opacity: .4; transform: scale(1); }}
        {p_end:.3f}%  {{ opacity: 0;  transform: scale(1); }}
        100%          {{ opacity: 0;  transform: scale(1); }}
    }}

    .comet {{
        opacity: 0;
        transform-box: fill-box;
        transform-origin: center;
        pointer-events: none;
        animation: comet {cycle:.3f}s linear infinite backwards;
    }}
    """
        reduced += " .comet { animation: none; opacity: 0; }"

    css += f"""
    @media (prefers-reduced-motion: reduce) {{
        {reduced}
    }}
    """

    return css


# --------------------------------------------------
# Render SVG
# --------------------------------------------------

def render(data):

    days = data["days"]

    grid = build_grid(days)
    month_labels = get_month_labels(grid)

    columns = len(grid)

    # Longest streak -> comet path (chronological order = grid order)
    streak = longest_streak(days)
    use_comet = (not STATIC) and len(streak) >= 2
    comet = comet_timing(columns, len(streak)) if use_comet else None

    grid_left = PAD_X + LEFT_LABEL_W
    grid_top = PAD_TOP + 40

    grid_width = columns * STEP
    grid_height = 7 * STEP

    width = grid_left + grid_width + PAD_X
    height = grid_top + grid_height + 55

    parts = []
    positions = {}

    # SVG opening
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'font-family="Arial, Helvetica, sans-serif">'
    )

    parts.append(f'<style>{make_css(comet)}</style>')

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

    # Contribution cells (opening reveal: left to right)
    for ci, column in enumerate(grid):

        for ri, cell in enumerate(column):

            if cell is None:
                continue

            date_s, count, level = cell

            x = grid_left + ci * STEP
            y = grid_top + ri * STEP

            positions[date_s] = (x, y)

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

    # Streak comet overlay (drawn on top of the cells)
    if comet:

        start, step, _, _ = comet

        for i, date in enumerate(streak):

            x, y = positions[date.isoformat()]
            delay = start + i * step

            parts.append(
                f'<g class="comet" style="animation-delay:{delay:.3f}s">'
                f'<rect x="{x - 3}" y="{y - 3}" '
                f'width="{CELL + 6}" height="{CELL + 6}" '
                f'rx="5" fill="{COMET_GLOW}" opacity=".35"/>'
                f'<rect x="{x}" y="{y}" '
                f'width="{CELL}" height="{CELL}" '
                f'rx="3" fill="{COMET_CORE}"/>'
                f'</g>'
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

    return "\n".join(parts), streak, comet


# --------------------------------------------------
# Main
# --------------------------------------------------

if __name__ == "__main__":

    try:

        print("Loading contribution data...")

        data = load_data()

        print("Rendering heatmap with opening reveal + streak comet...")

        svg, streak, comet = render(data)

        OUT_PATH.write_text(svg, encoding="utf-8")

        print("\nHeatmap generated successfully!")
        print(f"File: {OUT_PATH}")
        print(f"Size: {len(svg):,} bytes")
        print(f"Static mode: {STATIC}")

        if streak:
            print(f"Longest streak: {len(streak)} days "
                  f"({streak[0]} to {streak[-1]})")
        if comet:
            print(f"Comet starts at {comet[0]:.1f}s, loops every {comet[3]:.1f}s")

    except Exception as error:

        print(f"ERROR: {error}")
        raise SystemExit(1)