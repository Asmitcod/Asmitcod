#!/usr/bin/env python3
"""Generate info-card.svg: a neofetch-style terminal panel.

Usage:
    python scripts/make_info_card.py            # animated (staggered fade/slide-in)
    STATIC=1 python scripts/make_info_card.py   # frozen frame for Quick Look previews
"""
import os
from html import escape
from pathlib import Path

STATIC = os.environ.get("STATIC") == "1"
OUT = Path(__file__).resolve().parent.parent / "info-card.svg"

# ---------------------------------------------------------------- content
USER_HOST = "asmit@asmitcod"
TITLE = "asmit — neofetch"

# (key, key color, [value lines])
ROWS = [
    ("Now", "#58a6ff", [
        "Final-year B.Tech CS (AI & Robotics) @ VIT Chennai",
    ]),
    ("Prev", "#d2a8ff", [
        "Software Engineering Intern @ Sankalp Sewa Sansthan",
    ]),
    ("Stack", "#3fb950", [
        "Python · Java · C/C++ · SQL · Bash",
        "Flask · Socket.IO · PostgreSQL · DynamoDB",
        "ROS · ESP32 · Reinforcement Learning",
    ]),
    ("Highlights", "#f2cc60", [
        "Smart India Hackathon 2025: Top 100 of 864",
        "Devshouse 2025: Top 65",
        "RL-based Smart Traffic Management System",
    ]),
]

# ---------------------------------------------------------------- layout
W = 680
PAD_X = 28
KEY_W = 118              # width reserved for the key column
BAR_H = 38
LINE_H = 22
ROW_GAP = 12
FONT = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
FS = 13.5

BG = "#0d1117"
BAR = "#161b22"
BORDER = "#30363d"
FG = "#c9d1d9"
MUTED = "#8b949e"
PALETTE = ["#ff7b72", "#f2cc60", "#3fb950", "#56d4dd", "#58a6ff", "#d2a8ff", "#c9d1d9", "#484f58"]

STAGGER = 0.12           # seconds between lines
START = 0.3              # delay before the first line


def build() -> str:
    parts = []
    idx = 0  # running line index drives the stagger

    def line(inner: str, y: float) -> str:
        nonlocal idx
        delay = START + idx * STAGGER
        idx += 1
        style = "" if STATIC else f' style="animation-delay:{delay:.2f}s"'
        return f'<g transform="translate(0 {y:.1f})"><g class="l"{style}>{inner}</g></g>'

    y = BAR_H + 36

    # user@host header + underline
    header = (
        f'<text x="{PAD_X}" y="0" fill="#58a6ff" font-weight="700">{escape(USER_HOST)}</text>'
    )
    parts.append(line(header, y))
    y += 12
    rule = (
        f'<text x="{PAD_X}" y="0" fill="{MUTED}">{"─" * len(USER_HOST)}</text>'
    )
    parts.append(line(rule, y + 4))
    y += LINE_H + 4

    # key/value rows
    for key, color, values in ROWS:
        for i, val in enumerate(values):
            k = (
                f'<text x="{PAD_X}" y="0" fill="{color}" font-weight="700">{escape(key)}</text>'
                f'<text x="{PAD_X + KEY_W - 14}" y="0" fill="{MUTED}">:</text>'
                if i == 0 else ""
            )
            v = f'<text x="{PAD_X + KEY_W}" y="0" fill="{FG}">{escape(val)}</text>'
            parts.append(line(k + v, y))
            y += LINE_H
        y += ROW_GAP

    # neofetch-style palette blocks
    blocks = "".join(
        f'<rect x="{PAD_X + i * 26}" y="-12" width="22" height="16" rx="3" fill="{c}"/>'
        for i, c in enumerate(PALETTE)
    )
    parts.append(line(blocks, y))
    y += 28

    H = int(y)
    anim_css = "" if STATIC else """
    .l { opacity: 0; animation: in .55s cubic-bezier(.2,.7,.2,1) forwards; }
    @keyframes in {
      from { opacity: 0; transform: translateX(-14px); }
      to   { opacity: 1; transform: none; }
    }
    @media (prefers-reduced-motion: reduce) { .l { animation: none; opacity: 1; } }
    """

    body = "\n  ".join(parts)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Neofetch-style info card">
  <style>
    text {{ font-family: {FONT}; font-size: {FS}px; white-space: pre; }}
    {anim_css}
  </style>
  <rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>
  <path d="M.5 {BAR_H} V10.5 a10 10 0 0 1 10 -10 H{W - 10.5} a10 10 0 0 1 10 10 V{BAR_H} Z" fill="{BAR}" stroke="{BORDER}"/>
  <circle cx="22" cy="{BAR_H / 2}" r="6" fill="#ff5f56"/>
  <circle cx="42" cy="{BAR_H / 2}" r="6" fill="#ffbd2e"/>
  <circle cx="62" cy="{BAR_H / 2}" r="6" fill="#27c93f"/>
  <text x="{W / 2}" y="{BAR_H / 2 + 4.5}" text-anchor="middle" fill="{MUTED}" font-size="12.5">{escape(TITLE)}</text>
  {body}
</svg>
"""


def main() -> None:
    OUT.write_text(build(), encoding="utf-8")
    mode = "static" if STATIC else "animated"
    print(f"wrote {OUT} ({mode})")


if __name__ == "__main__":
    main()