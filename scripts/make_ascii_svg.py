
"""
Animated monochrome ASCII portrait.
Dark terminal interface with one-shot typing animation.
"""

from PIL import Image, ImageEnhance
from pathlib import Path
import html
import os
import sys

PROJECT_DIR = Path(__file__).resolve().parent.parent

SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else (
    PROJECT_DIR / "data" / "source-prepped.png"
)

OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else (
    PROJECT_DIR / "ascii-portrait.svg"
)

DISPLAY_NAME = "Asmit Bisht"

if not SRC.exists():
    raise FileNotFoundError(f"Image not found: {SRC}")

# ORIGINAL GOOD SETTINGS - DO NOT CHANGE
COLS = int(os.environ.get("COLS", 180))

ART_W_TARGET = 800
CELL_W = ART_W_TARGET / COLS
CELL_H = CELL_W * 15 / 8

ROWS = round(COLS * 8 / 15)

RAMP = " .`:-=+*cs#%@"

CONTRAST = 1.08
BRIGHTNESS = 1.0
GAMMA = 1.12
WHITE_FLOOR = 0.82

# Terminal design
PAD = 20
TITLEBAR_H = 30
STATUS_H = 30

ART_W = COLS * CELL_W
ART_H = ROWS * CELL_H

CANVAS_W = ART_W + PAD * 2
CANVAS_H = TITLEBAR_H + ART_H + STATUS_H + PAD

BG = "#0d1117"
BG2 = "#111722"
FRAME = "#30363d"

TITLE_TEXT = "#7d8590"
INK = "#c9d1d9"
CURSOR = "#c9d1d9"

# Animation
ROW_DUR = 5.8 / ROWS
STAGGER = ROW_DUR

STATIC = os.environ.get("STATIC", "").lower() in (
    "1", "true", "yes"
)

# 1. Load image
print("1. Loading prepared portrait...")

im = Image.open(SRC).convert("L")

im = ImageEnhance.Brightness(im).enhance(BRIGHTNESS)
im = ImageEnhance.Contrast(im).enhance(CONTRAST)

im = im.resize(
    (COLS, ROWS),
    Image.Resampling.LANCZOS
)

px = im.load()

# 2. Convert to ASCII
print("2. Converting image to ASCII...")

rows_txt = []

for y in range(ROWS):

    chars = []

    for x in range(COLS):

        lum = px[x, y] / 255.0
        lum = pow(lum, GAMMA)

        if lum >= WHITE_FLOOR:
            chars.append(" ")
            continue

        idx = int(
            (1.0 - lum) * (len(RAMP) - 1) + 0.5
        )

        idx = max(0, min(len(RAMP) - 1, idx))

        chars.append(RAMP[idx])

    rows_txt.append("".join(chars))

# 3. Build SVG
print("3. Building terminal interface...")

art_top = TITLEBAR_H + PAD * 0.35

parts = []

parts.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'width="{CANVAS_W}" height="{CANVAS_H}" '
    f'viewBox="0 0 {CANVAS_W} {CANVAS_H}" '
    f'font-family="ui-monospace, SFMono-Regular, '
    f'Menlo, Consolas, monospace">'
)

parts.append(
    f'<defs><linearGradient id="bg" '
    f'x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0" stop-color="{BG2}"/>'
    f'<stop offset="1" stop-color="{BG}"/>'
    f'</linearGradient></defs>'
)

parts.append(
    f'<rect width="{CANVAS_W}" '
    f'height="{CANVAS_H}" rx="12" fill="url(#bg)"/>'
)

parts.append(
    f'<rect x="0.5" y="0.5" '
    f'width="{CANVAS_W-1}" height="{CANVAS_H-1}" '
    f'rx="12" fill="none" stroke="{FRAME}"/>'
)

# 4. Terminal title bar
parts.append(
    f'<line x1="0" y1="{TITLEBAR_H}" '
    f'x2="{CANVAS_W}" y2="{TITLEBAR_H}" '
    f'stroke="{FRAME}"/>'
)

for i, color in enumerate(
    ["#ff5f56", "#ffbd2e", "#27c93f"]
):

    parts.append(
        f'<circle cx="{PAD + i*16}" '
        f'cy="{TITLEBAR_H/2}" r="5" fill="{color}"/>'
    )

parts.append(
    f'<text x="{CANVAS_W/2}" '
    f'y="{TITLEBAR_H/2 + 4}" '
    f'fill="{TITLE_TEXT}" font-size="12" '
    f'text-anchor="middle">'
    f'asmit@github: ~$ ./portrait.sh</text>'
)

# 5. ASCII animation
print("4. Creating typing animation...")

font_size = CELL_H * 0.86

for ry, line in enumerate(rows_txt):

    y = art_top + ry * CELL_H + CELL_H * 0.74
    row_y = art_top + ry * CELL_H

    delay = ry * STAGGER
    safe = html.escape(line)

    # Natural monospace spacing
    text = (
        f'<text xml:space="preserve" '
        f'x="{PAD}" y="{y:.1f}" '
        f'fill="{INK}" '
        f'font-size="{font_size:.1f}">'
        f'{safe}</text>'
    )

    if STATIC:
        parts.append(text)
        continue

    # Row clipping animation
    parts.append(
        f'<clipPath id="r{ry}">'
        f'<rect x="{PAD}" y="{row_y:.1f}" '
        f'height="{CELL_H}" width="0">'
        f'<animate attributeName="width" '
        f'from="0" to="{ART_W}" '
        f'begin="{delay:.3f}s" '
        f'dur="{ROW_DUR:.2f}s" fill="freeze"/>'
        f'</rect></clipPath>'
    )

    parts.append(
        f'<g clip-path="url(#r{ry})">{text}</g>'
    )

    # Moving block cursor
    parts.append(
        f'<rect y="{row_y+1:.1f}" '
        f'width="{CELL_W}" '
        f'height="{CELL_H-2}" '
        f'fill="{CURSOR}" opacity="0">'
        f'<animate attributeName="x" '
        f'from="{PAD}" to="{PAD+ART_W}" '
        f'begin="{delay:.3f}s" '
        f'dur="{ROW_DUR:.2f}s" fill="freeze"/>'
        f'<set attributeName="opacity" '
        f'to="0.85" begin="{delay:.3f}s"/>'
        f'<set attributeName="opacity" '
        f'to="0" begin="{delay+ROW_DUR:.3f}s"/>'
        f'</rect>'
    )

# 6. Terminal status bar
status_line_y = TITLEBAR_H + ART_H + PAD * 0.35
status_y = status_line_y + 19

parts.append(
    f'<line x1="0" y1="{status_line_y:.1f}" '
    f'x2="{CANVAS_W}" y2="{status_line_y:.1f}" '
    f'stroke="{FRAME}"/>'
)

parts.append(
    f'<text x="{PAD}" y="{status_y:.1f}" '
    f'fill="{TITLE_TEXT}" font-size="13">'
    f'asmit@github:~$ whoami '
    f'<tspan fill="{INK}">{html.escape(DISPLAY_NAME)}</tspan>'
    f'</text>'
)

status_chars = len(
    f"asmit@github:~$ whoami {DISPLAY_NAME} "
)

cursor_x = PAD + status_chars * 13 * 0.6

parts.append(
    f'<rect x="{cursor_x:.1f}" '
    f'y="{status_y-12:.1f}" '
    f'width="8" height="14" fill="{INK}">'
    f'<animate attributeName="opacity" '
    f'values="1;1;0;0" '
    f'keyTimes="0;0.5;0.51;1" '
    f'dur="1s" repeatCount="indefinite"/>'
    f'</rect>'
)

# 7. Save
parts.append("</svg>")

svg = "".join(parts)

OUT.parent.mkdir(parents=True, exist_ok=True)

OUT.write_text(svg, encoding="utf-8")

print("--------------------------------")
print("ASCII PORTRAIT GENERATED!")
print("--------------------------------")
print("Output:", OUT)
print("Grid:", COLS, "x", ROWS)
print("Canvas:", round(CANVAS_W), "x", round(CANVAS_H))
print("File size:", len(svg), "bytes")
