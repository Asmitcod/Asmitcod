#!/usr/bin/env python3
"""Generate stats-card.svg: a terminal-style GitHub stats panel.

Usage (from repo root):
    set GITHUB_TOKEN=ghp_xxx           (PowerShell: $env:GITHUB_TOKEN="ghp_xxx")
    python scripts/make_stats_card.py

Preview without a token (fake data):
    DEMO=1 python scripts/make_stats_card.py      (PowerShell: $env:DEMO=1)

Frozen frame, no animation:
    STATIC=1 python scripts/make_stats_card.py
"""
import json
import os
import random
import urllib.request
from datetime import date, timedelta
from html import escape
from pathlib import Path

LOGIN = os.environ.get("GH_LOGIN", "Asmitcod")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
DEMO = os.environ.get("DEMO") == "1"
STATIC = os.environ.get("STATIC") == "1"
OUT = Path(__file__).resolve().parent.parent / "info-card.svg"

TITLE = f"{LOGIN.lower()}@github: ~$ ./stats.sh"

# ------------------------------------------------------------------ data


def fetch_days():
    """Return a sorted list of (date, count) for the last ~year."""
    today = date.today()
    if DEMO:
        rnd = random.Random(7)
        out = []
        for i in range(366, -1, -1):
            d = today - timedelta(days=i)
            out.append((d, 0 if rnd.random() < 0.08 else rnd.randint(2, 60)))
        return out

    if not TOKEN:
        raise SystemExit("Set GITHUB_TOKEN (or run with DEMO=1 to preview).")

    query = """
    query($login:String!,$from:DateTime!,$to:DateTime!){
      user(login:$login){
        contributionsCollection(from:$from,to:$to){
          contributionCalendar{ weeks{ contributionDays{ date contributionCount } } }
        }
      }
    }"""
    variables = {
        "login": LOGIN,
        "from": f"{today - timedelta(days=365)}T00:00:00Z",
        "to": f"{today}T23:59:59Z",
    }
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(f"GitHub API error: {payload['errors']}")
    weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [
        (date.fromisoformat(d["date"]), d["contributionCount"])
        for w in weeks for d in w["contributionDays"]
    ]
    return sorted(x for x in days if x[0] <= today)


def fmt_day(d):
    return f"{d.strftime('%b')} {d.day}"  # avoids %-d (breaks on Windows)


def fmt_range(a, b):
    return f"{fmt_day(a)} – {fmt_day(b)}"


def compute(days):
    counts = {d: c for d, c in days}
    first, last = days[0][0], days[-1][0]

    # longest streak
    best_len, best_start, best_end = 0, None, None
    run, run_start = 0, None
    for d, c in days:
        if c > 0:
            if run == 0:
                run_start = d
            run += 1
            if run > best_len:
                best_len, best_start, best_end = run, run_start, d
        else:
            run = 0

    # current streak (today may still be empty -> start from yesterday)
    cur_end = last if counts[last] > 0 else last - timedelta(days=1)
    cur_len, d = 0, cur_end
    while d >= first and counts.get(d, 0) > 0:
        cur_len += 1
        d -= timedelta(days=1)
    cur_start = cur_end - timedelta(days=cur_len - 1) if cur_len else None

    total = sum(counts.values())
    active = sum(1 for c in counts.values() if c > 0)
    best_day = max(days, key=lambda x: x[1])

    # last 13 calendar months, oldest first
    months, y, m = [], last.year, last.month
    for _ in range(13):
        months.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    months.reverse()
    per_month = {k: 0 for k in months}
    for d, c in days:
        if (d.year, d.month) in per_month:
            per_month[(d.year, d.month)] += c

    return {
        "cur_len": cur_len, "cur_range": fmt_range(cur_start, cur_end) if cur_len else "no streak",
        "long_len": best_len, "long_range": fmt_range(best_start, best_end) if best_len else "–",
        "total": total, "active": active, "n_days": len(days),
        "pct": round(100 * active / len(days)),
        "best_val": best_day[1], "best_date": fmt_day(best_day[0]),
        "avg": total / active if active else 0,
        "months": [(f"{date(y, m, 1):%b}"[0], per_month[(y, m)]) for y, m in months],
    }


# ------------------------------------------------------------------ svg

W = 500
M = 12
GAP = 10
TILE_W = (W - 2 * M - GAP) / 2
TILE_H = 90
TOP = 44

BG, PANEL, TILE, BORDER = "#0d1117", "#0d1117", "#161b22", "#30363d"
FG, MUTED, GREEN, BAR = "#e6edf3", "#8b949e", "#39d353", "#26a641"
FONT = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

_n = 0


def anim(kind="t"):
    """Return class+style attrs with a growing stagger delay."""
    global _n
    if STATIC:
        return ""
    delay = 0.15 + _n * 0.07
    _n += 1
    return f' class="{kind}" style="animation-delay:{delay:.2f}s"'


def tile(x, y, title, value, suffix, sub, value_color=FG):
    big_w = len(value) * 18
    suffix_el = (
        f'<text x="{x + 16 + big_w + 8}" y="{y + 62}" fill="{MUTED}" font-size="15">{escape(suffix)}</text>'
        if suffix else ""
    )
    return (
        f'<g{anim()}>'
        f'<rect x="{x}" y="{y}" width="{TILE_W}" height="{TILE_H}" rx="8" fill="{TILE}" stroke="{BORDER}"/>'
        f'<text x="{x + 16}" y="{y + 25}" fill="{MUTED}" font-size="13">$ {escape(title)}</text>'
        f'<text x="{x + 16}" y="{y + 62}" fill="{value_color}" font-size="30" font-weight="700">{escape(value)}</text>'
        f'{suffix_el}'
        f'<text x="{x + 16}" y="{y + 80}" fill="{MUTED}" font-size="12">{escape(sub)}</text>'
        f'</g>'
    )


def chart(y, months):
    h = 190
    x0 = M
    inner_w = W - 2 * M
    pad = 24
    slot = (inner_w - 2 * pad) / len(months)
    bar_w = 22
    base = y + h - 30
    max_h = 100
    peak = max(v for _, v in months) or 1
    peak_i = max(range(len(months)), key=lambda i: months[i][1])

    out = [
        f'<g{anim()}>'
        f'<rect x="{x0}" y="{y}" width="{inner_w}" height="{h}" rx="8" fill="{TILE}" stroke="{BORDER}"/>'
        f'<text x="{x0 + 16}" y="{y + 25}" fill="{MUTED}" font-size="13">$ contributions / month</text>'
        f'</g>'
    ]
    for i, (label, v) in enumerate(months):
        bh = max(2, v / peak * max_h) if v else 2
        cx = x0 + pad + slot * i + slot / 2
        color = GREEN if i == peak_i else BAR
        out.append(
            f'<rect{anim("b")} x="{cx - bar_w / 2:.1f}" y="{base - bh:.1f}" width="{bar_w}" '
            f'height="{bh:.1f}" rx="3" fill="{color}"/>'
        )
        if i == peak_i:
            out.append(
                f'<text x="{cx:.1f}" y="{base - bh - 8:.1f}" text-anchor="middle" '
                f'fill="{FG}" font-size="11" font-weight="700">{v:,}</text>'
            )
        lc = "#58a6ff" if i == 0 else "#d29922" if i == len(months) - 1 else MUTED
        out.append(
            f'<text x="{cx:.1f}" y="{base + 20}" text-anchor="middle" fill="{lc}" font-size="11">{escape(label)}</text>'
        )
    return "".join(out), h


def build(s):
    tiles = [
        ("current streak", str(s["cur_len"]), "days", s["cur_range"], GREEN),
        ("longest streak", str(s["long_len"]), "days", s["long_range"], FG),
        ("contributions", f"{s['total']:,}", "", "in the last year", FG),
        ("active days", str(s["active"]), f"/ {s['n_days']}", f"{s['pct']}% of the year", FG),
        ("best day", str(s["best_val"]), "", s["best_date"], FG),
        ("avg / active day", f"{s['avg']:.1f}", "", "contributions", FG),
    ]
    body = []
    for i, (t, v, suf, sub, col) in enumerate(tiles):
        x = M + (i % 2) * (TILE_W + GAP)
        y = TOP + (i // 2) * (TILE_H + GAP)
        body.append(tile(x, y, t, v, suf, sub, col))

    chart_y = TOP + 3 * (TILE_H + GAP)
    chart_svg, ch = chart(chart_y, s["months"])
    body.append(chart_svg)
    H = int(chart_y + ch + M)

    css = "" if STATIC else """
    .t { opacity: 0; animation: fade .5s ease-out forwards; }
    .b { opacity: 0; transform-box: fill-box; transform-origin: bottom;
         animation: grow .6s cubic-bezier(.2,.7,.2,1) forwards; }
    @keyframes fade { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
    @keyframes grow { from { opacity: 0; transform: scaleY(0); } to { opacity: 1; transform: none; } }
    @media (prefers-reduced-motion: reduce) { .t, .b { animation: none; opacity: 1; } }
    """

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub stats card">
  <style>
    text {{ font-family: {FONT}; }}
    {css}
  </style>
  <rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>
  <circle cx="20" cy="16" r="5" fill="#ff5f56"/>
  <circle cx="38" cy="16" r="5" fill="#ffbd2e"/>
  <circle cx="56" cy="16" r="5" fill="#27c93f"/>
  <text x="{W / 2}" y="20" text-anchor="middle" fill="{MUTED}" font-size="10.5">{escape(TITLE)}</text>
  <line x1="1" y1="32" x2="{W - 1}" y2="32" stroke="{BORDER}"/>
  {"".join(body)}
</svg>
"""


def main():
    stats = compute(fetch_days())
    OUT.write_text(build(stats), encoding="utf-8")
    mode = "demo data" if DEMO else "live data"
    print(f"wrote {OUT} ({mode}{', static' if STATIC else ''})")


if __name__ == "__main__":
    main()