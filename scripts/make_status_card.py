#!/usr/bin/env python3
"""Generate status-hud.svg: a cyberpunk neon HUD status card.

Run from the repo root:
    python scripts/make_status_hud.py

Animation:
  - the neon frame draws itself on, then the panels boot in
  - big countdown number flickers on and glitches (RGB split) every few seconds
  - the segmented progress bar lights up segment by segment
  - rows slide in with a flicker, the LED blinks
  - a scan bar sweeps down the card in a loop, over a CRT scanline overlay

STATIC=1 gives a frozen frame (everything visible, no animation).

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
# Edit these. Anything marked "edit me" is a placeholder guess.
HANDLE = "ASMITCOD"
BUILDING = "a failure triage for  github logs"
LEARNING = "reinforcement learning · ROS navigation"          # edit me
CLASS_OF = "2027 · B.Tech CS (AI & Robotics) · VIT Chennai"

OPEN_TO_WORK = True                                           # edit me
OPEN_TEXT = "open to internships & roles"                     # edit me
BUSY_TEXT = "heads down, not looking right now"

REACH = "github.com/Asmitcod"
EMAIL = ""                                                    # edit me (optional)

DEGREE_START = date(2023, 8, 1)
DEGREE_END = date(2027, 7, 31)

# ---------------------------------------------------------------- style
W, H = 800, 396
CUT = 18                      # chamfered corners (top-left, bottom-right)
CYAN, MAG, GRN, RED = "#00f0ff", "#ff2bd6", "#39ff88", "#ff3860"
TXT, DIM = "#e8f7ff", "#6fa8b8"
SEG_OFF = "#0f2a33"
FONT = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

SEGS = 32
LEFT_X, LEFT_W = 36, 240
RIGHT_X = 324
ROW_Y0, ROW_H = 98, 50


def build():
    today = date.today()
    days_left = (DEGREE_END - today).days
    total = (DEGREE_END - DEGREE_START).days
    pct = max(0.0, min(1.0, (today - DEGREE_START).days / total))
    big = str(days_left) if days_left > 0 else "DONE"
    unit = "DAYS TO GRADUATION" if days_left > 0 else "DEGREE COMPLETE"
    lit = round(pct * SEGS)

    led = GRN if OPEN_TO_WORK else RED
    open_text = OPEN_TEXT if OPEN_TO_WORK else BUSY_TEXT
    reach = REACH + (f" · {EMAIL}" if EMAIL else "")

    frame = f"M{CUT},1 H{W - 1} V{H - CUT} L{W - CUT},{H - 1} H1 V{CUT} Z"
    inner = f"M{CUT + 7},8 H{W - 8} V{H - CUT - 7} L{W - CUT - 7},{H - 8} H8 V{CUT + 7} Z"

    def fade(delay):          # inline delay helper (no-op when static)
        return "" if STATIC else f' style="animation-delay:{delay:.2f}s"'

    out = []

    # --- background, grid, accents
    out.append(f'<path d="{frame}" fill="url(#bg)"/>')
    out.append('<g clip-path="url(#clip)">')
    out.append(f'<rect width="{W}" height="{H}" fill="url(#grid)"/>')
    out.append('</g>')
    out.append(f'<path d="{inner}" fill="none" stroke="{MAG}" stroke-opacity=".35" stroke-width="1"/>')
    out.append(
        f'<path d="M{W - 130},1 H{W - 1}" stroke="{MAG}" stroke-width="3" filter="url(#glow)"/>'
        f'<path d="M1,{H - 1} H130" stroke="{MAG}" stroke-width="3" filter="url(#glow)"/>'
    )

    # --- header
    out.append(
        f'<g class="fade"{fade(0.6)}>'
        f'<text x="36" y="40" font-size="15" font-weight="700" letter-spacing="3" fill="{CYAN}" filter="url(#glow)">'
        f'<tspan fill="{MAG}">//</tspan> STATUS.SYS</text>'
        f'<circle class="led" cx="{W - 140}" cy="35" r="4" fill="{CYAN}" filter="url(#glow)"{fade(0.6)}/>'
        f'<text x="{W - 36}" y="40" text-anchor="end" font-size="12" letter-spacing="2" fill="{DIM}">SYS ONLINE</text>'
        f'<line x1="36" y1="58" x2="{W - 36}" y2="58" stroke="{CYAN}" stroke-opacity=".35"/>'
        f'</g>'
    )

    # --- left: countdown
    ghost = (
        f'<text class="g1" x="{LEFT_X}" y="172" font-size="84" font-weight="700" fill="{MAG}" opacity="0">{escape(big)}</text>'
        f'<text class="g2" x="{LEFT_X}" y="172" font-size="84" font-weight="700" fill="{CYAN}" opacity="0">{escape(big)}</text>'
    )
    out.append(f'<text x="{LEFT_X}" y="98" font-size="11" letter-spacing="3" fill="{MAG}" class="fade"{fade(0.8)}>T-MINUS</text>')
    out.append(ghost)
    out.append(
        f'<text class="num" x="{LEFT_X}" y="172" font-size="84" font-weight="700" fill="{TXT}" '
        f'filter="url(#glow)"{fade(0.9)}>{escape(big)}</text>'
    )
    out.append(f'<text x="{LEFT_X + 2}" y="196" font-size="11" letter-spacing="2" fill="{DIM}" class="fade"{fade(1.2)}>{unit}</text>')

    gap = 2
    sw = (LEFT_W - gap * (SEGS - 1)) / SEGS
    for i in range(SEGS):
        x = LEFT_X + i * (sw + gap)
        out.append(f'<rect x="{x:.2f}" y="216" width="{sw:.2f}" height="12" fill="{SEG_OFF}"/>')
    for i in range(lit):
        x = LEFT_X + i * (sw + gap)
        delay = 1.6 + i * 0.03
        cls = "seg"
        style = fade(delay)
        if i == lit - 1 and not STATIC:
            cls = "seg pulse"
            style = f' style="animation-delay:{delay:.2f}s,{delay + 0.5:.2f}s"'
        out.append(
            f'<rect class="{cls}" x="{x:.2f}" y="216" width="{sw:.2f}" height="12" '
            f'fill="{CYAN}" filter="url(#glow)"{style}/>'
        )
    date_range = f"{DEGREE_START:%b %Y} — {DEGREE_END:%b %Y}".upper()
    out.append(
        f'<text x="{LEFT_X}" y="252" font-size="12" letter-spacing="2" fill="{CYAN}" class="fade"{fade(1.6)}>{round(pct * 100)}% COMPLETE</text>'
        f'<text x="{LEFT_X}" y="272" font-size="10.5" letter-spacing="1.5" fill="{DIM}" class="fade"{fade(1.7)}>{escape(date_range)}</text>'
    )

    # --- divider
    out.append(f'<line x1="300" y1="78" x2="300" y2="330" stroke="url(#div)" stroke-width="1.5" class="fade"{fade(1.0)}/>')

    # --- right: rows
    rows = [
        ("BUILDING", CYAN, BUILDING, None),
        ("LEARNING", MAG, LEARNING, None),
        ("CLASS OF", "#ffe14d", CLASS_OF, None),
        ("OPEN TO", led, open_text, "led"),
        ("REACH", CYAN, reach, None),
    ]
    for i, (label, color, value, kind) in enumerate(rows):
        ry = ROW_Y0 + i * ROW_H
        delay = 1.0 + i * 0.18
        if kind == "led":
            value_svg = (
                f'<circle class="led" cx="{RIGHT_X + 5}" cy="{ry + 17}" r="5" fill="{led}" filter="url(#glow)"{fade(delay + 0.4)}/>'
                f'<text x="{RIGHT_X + 20}" y="{ry + 22}" font-size="14" fill="{led}">{escape(value)}</text>'
            )
        else:
            value_svg = f'<text x="{RIGHT_X}" y="{ry + 22}" font-size="14" fill="{TXT}">{escape(value)}</text>'
        out.append(
            f'<g class="row"{fade(delay)}>'
            f'<text x="{RIGHT_X}" y="{ry}" font-size="10.5" font-weight="700" letter-spacing="2.5" fill="{color}">{label}</text>'
            f'{value_svg}'
            f'<line x1="{RIGHT_X}" y1="{ry + 36}" x2="{W - 36}" y2="{ry + 36}" stroke="{CYAN}" stroke-opacity=".12"/>'
            f'</g>'
        )

    # --- footer
    out.append(
        f'<g class="fade"{fade(2.2)}>'
        f'<text x="36" y="{H - 20}" font-size="10.5" letter-spacing="2" fill="{DIM}">{escape(HANDLE)} // PROFILE.OS</text>'
        f'<text x="{W - 36}" y="{H - 20}" text-anchor="end" font-size="10.5" letter-spacing="2" fill="{DIM}">SYNCED {today.isoformat()}</text>'
        f'</g>'
    )

    # --- scan bar + CRT scanlines (clipped to the chamfered frame)
    out.append('<g clip-path="url(#clip)" pointer-events="none">')
    if not STATIC:
        out.append(f'<rect class="scan" x="0" y="0" width="{W}" height="70" fill="url(#scan)"/>')
    out.append(f'<rect width="{W}" height="{H}" fill="url(#lines)"/>')
    out.append('</g>')

    # --- neon frame on top (draws itself on)
    out.append(f'<path class="frame" d="{frame}" pathLength="1" fill="none" stroke="{CYAN}" stroke-width="2" filter="url(#glow)"/>')

    css = "" if STATIC else """
    .frame { stroke-dasharray: 1; stroke-dashoffset: 1; animation: draw 1.4s ease-out forwards; }
    @keyframes draw { to { stroke-dashoffset: 0; } }
    .fade { animation: fadein .6s ease-out both; }
    @keyframes fadein { from { opacity: 0; } to { opacity: 1; } }
    .row { animation: rowin .7s ease-out both; }
    @keyframes rowin {
      0% { opacity: 0; transform: translateX(-14px); }
      40% { opacity: 1; } 50% { opacity: .35; } 60% { opacity: 1; }
      100% { opacity: 1; transform: none; }
    }
    .num { animation: numin 1s linear both; }
    @keyframes numin {
      0% { opacity: 0; } 15% { opacity: 1; } 25% { opacity: .2; } 35% { opacity: 1; }
      45% { opacity: .5; } 55%, 100% { opacity: 1; }
    }
    .g1 { animation: glitch1 7s infinite 3s; }
    .g2 { animation: glitch2 7s infinite 3s; }
    @keyframes glitch1 {
      0%, 90%, 100% { opacity: 0; transform: translate(0, 0); }
      91% { opacity: .85; transform: translate(-4px, 1px); }
      93% { opacity: .85; transform: translate(3px, -1px); }
      95% { opacity: 0; }
    }
    @keyframes glitch2 {
      0%, 90%, 100% { opacity: 0; transform: translate(0, 0); }
      91% { opacity: .85; transform: translate(4px, -1px); }
      93% { opacity: .85; transform: translate(-3px, 1px); }
      95% { opacity: 0; }
    }
    .seg { animation: segon .25s ease-out both; }
    @keyframes segon { from { opacity: 0; } to { opacity: 1; } }
    .pulse { animation: segon .25s ease-out both, pulse 1.2s ease-in-out infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: .3; } }
    .led { animation: ledblink 1.6s ease-in-out infinite; }
    @keyframes ledblink { 0%, 100% { opacity: 1; } 50% { opacity: .25; } }
    .scan { animation: scan 5s linear infinite; }
    @keyframes scan { from { transform: translateY(-70px); } to { transform: translateY(__H__px); } }
    @media (prefers-reduced-motion: reduce) {
      .frame { animation: none; stroke-dasharray: none; stroke-dashoffset: 0; }
      .fade, .row, .num, .seg, .pulse, .led { animation: none; }
      .g1, .g2, .scan { display: none; }
    }
    """.replace("__H__", str(H))

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Status HUD">
  <defs>
    <clipPath id="clip"><path d="{frame}"/></clipPath>
    <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="2.6" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <radialGradient id="bg" cx="30%" cy="20%" r="95%">
      <stop offset="0" stop-color="#0b1230"/><stop offset="1" stop-color="#04050d"/>
    </radialGradient>
    <linearGradient id="scan" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{CYAN}" stop-opacity="0"/>
      <stop offset=".5" stop-color="{CYAN}" stop-opacity=".13"/>
      <stop offset="1" stop-color="{CYAN}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="div" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{CYAN}" stop-opacity=".7"/>
      <stop offset="1" stop-color="{MAG}" stop-opacity=".7"/>
    </linearGradient>
    <pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse">
      <path d="M28 0H0V28" fill="none" stroke="{CYAN}" stroke-opacity=".06"/>
    </pattern>
    <pattern id="lines" width="4" height="4" patternUnits="userSpaceOnUse">
      <rect width="4" height="1.4" fill="#000" fill-opacity=".24"/>
    </pattern>
  </defs>
  <style>
    text {{ font-family: {FONT}; }}
    {css}
  </style>
  {"".join(out)}
</svg>
"""


def main():
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT} ({'static' if STATIC else 'animated'})")


if __name__ == "__main__":
    main()