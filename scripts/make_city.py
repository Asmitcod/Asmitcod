"""
Contribution City - isometric 3D contribution graph.

Same dark terminal window as ascii-portrait.svg / info-card.svg,
monochrome ice-gray buildings, one-shot "buildings rise" animation.

Reads  data/contributions.json   (made by fetch_contributions.py)
Writes contrib-city.svg

Usage:
    python scripts/make_city.py [data.json] [out.svg]
    STATIC=1 python scripts/make_city.py     # no animation (for previews)

Pure standard library - no pip install needed.
"""

import html
import json
import math
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT_DIR / "data" / "contributions.json"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else PROJECT_DIR / "contrib-city.svg"

USERNAME = os.environ.get("GH_USER", "Asmitcod")
STATIC = os.environ.get("STATIC", "").lower() in ("1", "true", "yes")

# ---------------------------------------------------------------- palette
# identical to the other profile cards
BG = "#0d1117"
BG2 = "#111722"
FRAME = "#30363d"
TITLE_TEXT = "#7d8590"
INK = "#c9d1d9"

TILE_TOP = "#1f2733"      # empty day (flat tile)
TILE_STROKE = "#2d3745"

# building tops, level 1..4 (all in the same gray family as the portrait)
LEVELS = ["#59616c", "#8b949e", "#b4bcc6", "#dde3ea"]
PEAK = "#f0f6fc"          # busiest day

# ---------------------------------------------------------------- layout
PAD = 20
TITLEBAR_H = 30
STATUS_H = 30
CANVAS_W = 840

CITY_LEFT = 235           # keeps the left column free for the stats text
CITY_RIGHT = CANVAS_W - PAD
A = (CITY_RIGHT - CITY_LEFT) / 60.0   # half tile width
B = A / 2.0                            # half tile height (2:1 isometric)
FOOT = 0.88                            # footprint -> small gap between tiles

H_FLAT = 2.0
H_MAX = 62.0

RISE_DUR = 0.7
WEEK_STAGGER = 0.045


# ---------------------------------------------------------------- data
def load_counts(path: Path) -> dict:
    """Return {date: count}. Accepts the common shapes:
       - GitHub GraphQL calendar  {"weeks":[{"contributionDays":[...]}]}
         (optionally wrapped in data.user.contributionsCollection...)
       - {"days":[{"date","count"}]}  or a plain list of such dicts
       - {"2025-11-03": 4, ...}
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    counts = {}

    def walk(node):
        if isinstance(node, dict):
            if "contributionDays" in node:
                for d in node["contributionDays"]:
                    add(d)
                return
            if "date" in node and any(k in node for k in ("count", "contributionCount", "value")):
                add(node)
                return
            if node and all(_is_date(k) for k in node.keys()):
                for k, v in node.items():
                    counts[_to_date(k)] = int(v if not isinstance(v, dict) else v.get("count", 0))
                return
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    def add(d):
        c = d.get("contributionCount", d.get("count", d.get("value", 0)))
        counts[_to_date(d["date"])] = int(c or 0)

    walk(raw)
    if not counts:
        raise ValueError(f"No daily contribution data recognised in {path}")
    return counts


def _is_date(s):
    try:
        datetime.strptime(str(s)[:10], "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _to_date(s):
    return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()


def build_grid(counts: dict):
    """53 weeks x 7 days ending with the latest day in the data (Sunday-first)."""
    last = max(counts)
    # Sunday of the last week
    last_sunday = last - timedelta(days=(last.weekday() + 1) % 7)
    first_sunday = last_sunday - timedelta(weeks=52)
    cells = []
    for w in range(53):
        for d in range(7):
            day = first_sunday + timedelta(weeks=w, days=d)
            if day > last:
                continue
            cells.append((w, d, day, counts.get(day, 0)))
    return cells


# ---------------------------------------------------------------- colour helpers
def shade(hex_color: str, k: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (int(r * k), int(g * k), int(b * k))


def quantile_levels(values):
    """GitHub-style levels, but quantile based so one huge day doesn't flatten the rest."""
    vals = sorted(v for v in values if v > 0)
    if not vals:
        return lambda c: 0

    def q(p):
        return vals[min(len(vals) - 1, int(p * len(vals)))]

    t1, t2, t3 = q(0.25), q(0.5), q(0.75)

    def level(c):
        if c <= 0:
            return 0
        if c <= t1:
            return 1
        if c <= t2:
            return 2
        if c <= t3:
            return 3
        return 4

    return level


# ---------------------------------------------------------------- geometry
def project(w, d):
    """grid (week, day) -> ground-center screen coords (before offset)."""
    return (w - d) * A, (w + d) * B


def fmt(n):
    return f"{n:.1f}".rstrip("0").rstrip(".")


def faces(cx, cy, h):
    a, b = A * FOOT, B * FOOT
    top = (f"M{fmt(cx)} {fmt(cy - b - h)}L{fmt(cx + a)} {fmt(cy - h)}"
           f"L{fmt(cx)} {fmt(cy + b - h)}L{fmt(cx - a)} {fmt(cy - h)}Z")
    left = (f"M{fmt(cx - a)} {fmt(cy - h)}L{fmt(cx)} {fmt(cy + b - h)}"
            f"L{fmt(cx)} {fmt(cy + b)}L{fmt(cx - a)} {fmt(cy)}Z")
    right = (f"M{fmt(cx + a)} {fmt(cy - h)}L{fmt(cx)} {fmt(cy + b - h)}"
             f"L{fmt(cx)} {fmt(cy + b)}L{fmt(cx + a)} {fmt(cy)}Z")
    return top, left, right


def height_for(count, peak):
    if count <= 0:
        return H_FLAT
    return H_FLAT + 4 + (H_MAX - H_FLAT - 4) * (count / peak) ** 0.62


def anim(flat_d, full_d, begin):
    return (f'<animate attributeName="d" dur="{RISE_DUR}s" begin="{begin:.3f}s" fill="freeze" '
            f'calcMode="spline" keyTimes="0;1" keySplines="0.2 0.9 0.25 1" '
            f'values="{flat_d};{full_d}"/>')


# ---------------------------------------------------------------- main
counts = load_counts(SRC)
cells = build_grid(counts)

in_range = [c[3] for c in cells]
total = sum(in_range)
active = sum(1 for c in in_range if c > 0)
peak = max(in_range) if in_range else 0
level_of = quantile_levels(in_range)
peak_cell = max(cells, key=lambda c: c[3]) if peak else None

# vertical placement
y_top_margin = H_MAX + 26
city_h = 58 * B + 2 * B
art_top = TITLEBAR_H + 8
origin_y = art_top + y_top_margin          # screen y of ground-center for (0,0)
origin_x = CITY_LEFT + 6 * A + A           # leftmost vertex lands on CITY_LEFT

art_bottom = origin_y + city_h + 22
status_line_y = art_bottom + 4
CANVAS_H = status_line_y + STATUS_H
status_y = status_line_y + 19

p = []
p.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{fmt(CANVAS_H)}" '
    f'viewBox="0 0 {CANVAS_W} {fmt(CANVAS_H)}" '
    f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">'
)
p.append(
    f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/></linearGradient>'
    f'<radialGradient id="glow" cx="0.72" cy="0.62" r="0.55">'
    f'<stop offset="0" stop-color="{INK}" stop-opacity="0.07"/>'
    f'<stop offset="1" stop-color="{INK}" stop-opacity="0"/></radialGradient></defs>'
)
p.append(f'<rect width="{CANVAS_W}" height="{fmt(CANVAS_H)}" rx="12" fill="url(#bg)"/>')
p.append(f'<rect width="{CANVAS_W}" height="{fmt(CANVAS_H)}" rx="12" fill="url(#glow)"/>')
p.append(f'<rect x="0.5" y="0.5" width="{CANVAS_W - 1}" height="{fmt(CANVAS_H - 1)}" rx="12" '
         f'fill="none" stroke="{FRAME}"/>')

# title bar (same as the other cards)
p.append(f'<line x1="0" y1="{TITLEBAR_H}" x2="{CANVAS_W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>')
for i, color in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    p.append(f'<circle cx="{PAD + i * 16}" cy="{TITLEBAR_H / 2}" r="5" fill="{color}"/>')
p.append(f'<text x="{CANVAS_W / 2}" y="{TITLEBAR_H / 2 + 4}" fill="{TITLE_TEXT}" font-size="12" '
         f'text-anchor="middle">asmit@github: ~$ ./city.sh</text>')

# stats column
sx = PAD + 14
sy = art_top + 40
p.append(f'<text x="{sx}" y="{sy}" fill="{TITLE_TEXT}" font-size="10" letter-spacing="3">CONTRIBUTION CITY</text>')
p.append(f'<text x="{sx}" y="{sy + 40}" fill="{INK}" font-size="40" font-weight="700">{total}</text>')
p.append(f'<text x="{sx}" y="{sy + 62}" fill="{INK}" font-size="12">contributions in the last year</text>')
p.append(f'<text x="{sx}" y="{sy + 92}" fill="{TITLE_TEXT}" font-size="11.5">{active} active days</text>')
p.append(f'<text x="{sx}" y="{sy + 110}" fill="{TITLE_TEXT}" font-size="11.5">Busiest day: {peak}</text>')

# city: back-to-front
cells.sort(key=lambda c: (c[0] + c[1], c[1]))
for w, d, day, cnt in cells:
    gx, gy = project(w, d)
    cx, cy = origin_x + gx, origin_y + gy
    lv = level_of(cnt)
    is_peak = peak_cell is not None and (w, d) == (peak_cell[0], peak_cell[1])

    if lv == 0:
        top_c = TILE_TOP
    elif is_peak:
        top_c = PEAK
    else:
        top_c = LEVELS[lv - 1]
    left_c, right_c = shade(top_c, 0.72), shade(top_c, 0.5)

    h_full = height_for(cnt, peak)
    ft, fl, fr = faces(cx, cy, H_FLAT)
    gt, gl, gr = faces(cx, cy, h_full)

    stroke = f' stroke="{TILE_STROKE}" stroke-width="0.5"' if lv == 0 else ""
    tip = f"{day.isoformat()}: {cnt} contribution{'s' if cnt != 1 else ''}"

    if lv == 0 or STATIC:
        shown = (ft, fl, fr) if lv == 0 else (gt, gl, gr)
        p.append(
            f'<g><title>{tip}</title>'
            f'<path d="{shown[1]}" fill="{left_c}"/>'
            f'<path d="{shown[2]}" fill="{right_c}"/>'
            f'<path d="{shown[0]}" fill="{top_c}"{stroke}/></g>'
        )
        continue

    begin = 0.3 + w * WEEK_STAGGER + d * 0.01
    pulse = ""
    if is_peak and not STATIC:
        pulse = (f'<animate attributeName="opacity" values="1;0.7;1" dur="2.4s" '
                 f'begin="{begin + RISE_DUR + 0.4:.2f}s" repeatCount="indefinite"/>')
    p.append(
        f'<g><title>{tip}</title>'
        f'<path d="{fl}" fill="{left_c}">{anim(fl, gl, begin)}</path>'
        f'<path d="{fr}" fill="{right_c}">{anim(fr, gr, begin)}</path>'
        f'<path d="{ft}" fill="{top_c}">{anim(ft, gt, begin)}{pulse}</path></g>'
    )

# label above the busiest building
if peak_cell:
    w, d, day, cnt = peak_cell
    gx, gy = project(w, d)
    cx, cy = origin_x + gx, origin_y + gy
    top_y = cy - height_for(cnt, peak) - B - 4
    appear = 0.3 + w * WEEK_STAGGER + RISE_DUR
    op = "" if STATIC else f' opacity="0"><animate attributeName="opacity" to="1" begin="{appear:.2f}s" dur="0.4s" fill="freeze"/'
    p.append(
        f'<g{op}>'
        f'<line x1="{fmt(cx)}" y1="{fmt(top_y)}" x2="{fmt(cx)}" y2="{fmt(top_y - 12)}" stroke="{TITLE_TEXT}" stroke-width="1"/>'
        f'<text x="{fmt(cx)}" y="{fmt(top_y - 16)}" fill="{INK}" font-size="11" text-anchor="middle">{cnt}</text>'
        f'</g>'
    )

# legend + handle, bottom-left (empty corner of the isometric strip)
ly = art_bottom - 24
p.append(f'<text x="{sx}" y="{ly}" fill="{INK}" font-size="11">@{html.escape(USERNAME)}</text>')
p.append(f'<text x="{sx}" y="{ly + 16}" fill="{TITLE_TEXT}" font-size="10">less</text>')
for i, col in enumerate([TILE_TOP] + LEVELS):
    x = sx + 28 + i * 14
    p.append(f'<rect x="{x}" y="{ly + 7}" width="10" height="10" rx="2" fill="{col}" stroke="{TILE_STROKE}" stroke-width="0.5"/>')
p.append(f'<text x="{sx + 28 + 5 * 14 + 4}" y="{ly + 16}" fill="{TITLE_TEXT}" font-size="10">more</text>')

# status bar (same as the portrait card)
p.append(f'<line x1="0" y1="{fmt(status_line_y)}" x2="{CANVAS_W}" y2="{fmt(status_line_y)}" stroke="{FRAME}"/>')
status = "asmit@github:~$ git log --since=1.year | wc -l "
p.append(
    f'<text x="{PAD}" y="{fmt(status_y)}" fill="{TITLE_TEXT}" font-size="13" xml:space="preserve">'
    f'{html.escape(status)}<tspan fill="{INK}">{total}</tspan></text>'
)
cursor_x = PAD + (len(status) + len(str(total)) + 1) * 13 * 0.6
p.append(
    f'<rect x="{fmt(cursor_x)}" y="{fmt(status_y - 12)}" width="8" height="14" fill="{INK}">'
    f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" dur="1s" repeatCount="indefinite"/></rect>'
)

p.append("</svg>")
svg = "".join(p)

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(svg, encoding="utf-8")

print("--------------------------------")
print("CONTRIBUTION CITY GENERATED")
print("--------------------------------")
print("Source:", SRC)
print("Output:", OUT)
print(f"Days: {len(cells)}  total: {total}  active: {active}  busiest: {peak}")
print("Canvas:", CANVAS_W, "x", round(CANVAS_H))
print("File size:", len(svg), "bytes")