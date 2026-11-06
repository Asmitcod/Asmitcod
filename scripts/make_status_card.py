#!/usr/bin/env python3
"""Generate status-mono.svg: a sleek, black-only status card.

Run from the repo root:
    python scripts/make_status_mono.py

Animation (restrained):
  - content rises in with a short stagger
  - the graduation progress line draws itself
  - the status dot pulses softly
  - a faint scan line sweeps down the card on a loop

STATIC=1 gives a frozen frame (no animation, no sweep).

The countdown is computed when the script runs; the footer shows the sync date.
Re-run it (or schedule it in a GitHub Action) to keep the number current.
"""
import os
from datetime import date
from html import escape
from pathlib import Path

STATIC = os.environ.get("STATIC") == "1"
OUT = Path(__file__).resolve().parent.parent / "status-hud.svg"

# ---------------------------------------------------------------- content
HANDLE = "asmitcod"
BUILDING = "a failure triage for github logs"
LEARNING = "reinforcement learning · ROS navigation"          # edit me
CLASS_OF = "2027 · B.Tech CS (AI & Robotics) · VIT Chennai"

OPEN_TO_WORK = True                                           # edit me
OPEN_TEXT = "open to internships & roles"                     # edit me
BUSY_TEXT = "heads down, not looking right now"

REACH = "github.com/Asmitcod"
EMAIL = ""                                                    # edit me (optional)

DEGREE_START = date(2023, 8, 1)
DEGREE_END = date(2027, 5, 31)

# ---------------------------------------------------------------- style
W, H = 800, 372
R = 16                                    # corner radius
BG, BORDER = "#000000", "#1f1f1f"
FG, LABEL, MUTED, HAIR = "#f2f2f2", "#7a7a7a", "#4d4d4d", "#171717"
FONT = "'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif"

LEFT_X, LEFT_W = 44, 232
DIV_X = 304
RIGHT_X = 344
ROW_Y0, ROW_H = 82, 52


def build():
    today = date.today()
    days_left = (DEGREE_END - today).days
    total = (DEGREE_END - DEGREE_START).days
    pct = max(0.0, min(1.0, (today - DEGREE_START).days / total))
    big = str(days_left) if days_left > 0 else "done"
    unit = "days to go" if days_left > 0 else "degree complete"
    date_range = f"{DEGREE_START:%b %Y} – {DEGREE_END:%b %Y}".lower()
    reach = REACH + (f" · {EMAIL}" if EMAIL else "")

    def rise(delay):
        """Class + inline delay for the fade/rise-in (nothing when static)."""
        if STATIC:
            return ""
        return f' class="in" style="animation-delay:{delay:.2f}s"'

    out = []

    # --- left: countdown
    out.append(f'<text x="{LEFT_X}" y="{ROW_Y0}" font-size="12" fill="{LABEL}"{rise(0.15)}>graduation</text>')
    out.append(
        f'<text x="{LEFT_X - 3}" y="172" font-size="96" font-weight="300" letter-spacing="-3" '
        f'fill="{FG}"{rise(0.3)}>{escape(big)}</text>'
    )
    out.append(f'<text x="{LEFT_X}" y="200" font-size="13" fill="{LABEL}"{rise(0.45)}>{unit}</text>')

    track_y = 228
    out.append(f'<rect x="{LEFT_X}" y="{track_y}" width="{LEFT_W}" height="2" rx="1" fill="#242424"/>')
    fill_cls = "" if STATIC else ' class="fill" style="animation-delay:.6s"'
    out.append(
        f'<rect{fill_cls} x="{LEFT_X}" y="{track_y}" width="{LEFT_W * pct:.2f}" height="2" rx="1" fill="{FG}"/>'
    )
    out.append(f'<text x="{LEFT_X}" y="252" font-size="12" fill="{LABEL}"{rise(0.7)}>{round(pct * 100)}% of the degree</text>')
    out.append(f'<text x="{LEFT_X}" y="270" font-size="12" fill="{MUTED}"{rise(0.8)}>{escape(date_range)}</text>')

    # --- divider
    out.append(f'<line x1="{DIV_X}" y1="52" x2="{DIV_X}" y2="{H - 52}" stroke="{HAIR}"/>')

    # --- right: rows
    rows = [
        ("building", BUILDING, False),
        ("learning", LEARNING, False),
        ("class of", CLASS_OF, False),
        ("status", OPEN_TEXT if OPEN_TO_WORK else BUSY_TEXT, True),
        ("contact", reach, False),
    ]
    for i, (label, value, is_status) in enumerate(rows):
        ry = ROW_Y0 + i * ROW_H
        delay = 0.25 + i * 0.12
        if is_status:
            cx, cy = RIGHT_X + 4, ry + 17
            if OPEN_TO_WORK:
                dot = (
                    f'<circle cx="{cx}" cy="{cy}" r="4" fill="{FG}"/>'
                    f'<circle class="ring" cx="{cx}" cy="{cy}" r="4" fill="none" stroke="{FG}" stroke-width="1"/>'
                )
            else:
                dot = f'<circle cx="{cx}" cy="{cy}" r="3.5" fill="none" stroke="{LABEL}" stroke-width="1.2"/>'
            value_svg = dot + f'<text x="{RIGHT_X + 18}" y="{ry + 22}" font-size="15" fill="{FG}">{escape(value)}</text>'
        else:
            value_svg = f'<text x="{RIGHT_X}" y="{ry + 22}" font-size="15" fill="{FG}">{escape(value)}</text>'

        sep = (
            f'<line x1="{RIGHT_X}" y1="{ry + 36}" x2="{W - 44}" y2="{ry + 36}" stroke="{HAIR}"/>'
            if i < len(rows) - 1 else ""
        )
        out.append(
            f'<g{rise(delay)}>'
            f'<text x="{RIGHT_X}" y="{ry}" font-size="12" fill="{LABEL}">{label}</text>'
            f'{value_svg}{sep}</g>'
        )

    # --- footer
    out.append(f'<line x1="44" y1="{H - 38}" x2="{W - 44}" y2="{H - 38}" stroke="{HAIR}"/>')
    out.append(
        f'<g{rise(0.9)}>'
        f'<text x="44" y="{H - 14}" font-size="11" fill="{MUTED}">{escape(HANDLE)}</text>'
        f'<text x="{W - 44}" y="{H - 14}" text-anchor="end" font-size="11" fill="{MUTED}">synced {today.isoformat()}</text>'
        f'</g>'
    )

    # --- scan sweep (clipped to the rounded card)
    if not STATIC:
        out.append(
            '<g clip-path="url(#clip)" pointer-events="none">'
            '<g class="scan">'
            f'<rect x="0" y="0" width="{W}" height="90" fill="url(#trail)"/>'
            f'<rect x="0" y="89" width="{W}" height="1" fill="#ffffff" fill-opacity=".22"/>'
            '</g></g>'
        )

    css = "" if STATIC else """
    .in { animation: rise .8s cubic-bezier(.2,.7,.2,1) both; }
    @keyframes rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
    .fill { transform-box: fill-box; transform-origin: left center; transform: scaleX(0);
            animation: grow 1.6s cubic-bezier(.2,.7,.2,1) forwards; }
    @keyframes grow { to { transform: scaleX(1); } }
    .ring { transform-box: fill-box; transform-origin: center; animation: ring 2.6s ease-out infinite; }
    @keyframes ring { 0% { opacity: .5; transform: scale(1); } 70%, 100% { opacity: 0; transform: scale(3); } }
    .scan { animation: scan 6s linear infinite; }
    @keyframes scan { from { transform: translateY(-90px); } to { transform: translateY(__H__px); } }
    @media (prefers-reduced-motion: reduce) {
      .in { animation: none; }
      .fill { animation: none; transform: none; }
      .ring, .scan { display: none; }
    }
    """.replace("__H__", str(H))

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Status card">
  <defs>
    <clipPath id="clip"><rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="{R}"/></clipPath>
    <linearGradient id="trail" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff" stop-opacity="0"/>
      <stop offset="1" stop-color="#ffffff" stop-opacity=".07"/>
    </linearGradient>
  </defs>
  <style>
    text {{ font-family: {FONT}; }}
    {css}
  </style>
  <rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="{R}" fill="{BG}" stroke="{BORDER}"/>
  {"".join(out)}
</svg>
"""


def main():
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT} ({'static' if STATIC else 'animated'})")


if __name__ == "__main__":
    main()