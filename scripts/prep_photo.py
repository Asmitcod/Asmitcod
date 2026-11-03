
"""
Prepare a portrait with an already-white background
for ASCII conversion.

Output: data/source-prepped.png
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

PROJECT_DIR = Path(__file__).resolve().parent.parent

INPUT = Path(sys.argv[1]) if len(sys.argv) > 1 else (
    PROJECT_DIR / "source-photo.png"
)

OUTPUT = Path(sys.argv[2]) if len(sys.argv) > 2 else (
    PROJECT_DIR / "data" / "source-prepped.png"
)

# ORIGINAL GOOD SETTINGS
BACKGROUND_THRESHOLD = 12
PADDING = 60
LINE_WEIGHT = 0.45

print("1. Loading photograph...")

if not INPUT.exists():
    raise FileNotFoundError(f"Image not found: {INPUT}")

rgb = np.array(Image.open(INPUT).convert("RGB"))
gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

print("2. Detecting subject...")

difference = 255 - gray

mask = (
    difference > BACKGROUND_THRESHOLD
).astype(np.uint8) * 255

kernel = np.ones((5, 5), np.uint8)

mask = cv2.morphologyEx(
    mask, cv2.MORPH_OPEN, kernel
)

mask = cv2.morphologyEx(
    mask, cv2.MORPH_CLOSE, kernel, iterations=2
)

contours, _ = cv2.findContours(
    mask,
    cv2.RETR_EXTERNAL,
    cv2.CHAIN_APPROX_SIMPLE
)

if not contours:
    raise ValueError("No subject detected.")

largest = max(contours, key=cv2.contourArea)

x, y, w, h = cv2.boundingRect(largest)

print("3. Smoothing image...")

smooth = gray.copy()

for _ in range(2):
    smooth = cv2.bilateralFilter(
        smooth, 9, 40, 9
    )

print("4. Enhancing local contrast...")

clahe = cv2.createCLAHE(
    clipLimit=2.0,
    tileGridSize=(8, 8)
)

enhanced = clahe.apply(smooth)

print("5. Enhancing facial details...")

fine = cv2.GaussianBlur(
    enhanced, (0, 0), 1.5
).astype(np.float32)

coarse = cv2.GaussianBlur(
    enhanced, (0, 0), 6
).astype(np.float32)

lines = np.clip(
    (coarse - fine) / 40.0,
    0,
    1
)

result = enhanced.astype(np.float32) - (
    LINE_WEIGHT * lines * 255
)

result = np.clip(result, 0, 255)

print("6. Compositing onto white...")

soft_mask = cv2.GaussianBlur(
    mask.astype(np.float32) / 255.0,
    (0, 0),
    1.0
)

result = (
    result * soft_mask +
    255.0 * (1.0 - soft_mask)
)

result = np.clip(result, 0, 255).astype(np.uint8)

print("7. Cropping subject...")

side = max(w, h) + PADDING

cx = x + w // 2
cy = y + h // 2

x0 = cx - side // 2
y0 = cy - side // 2

canvas = np.full(
    (side, side), 255, dtype=np.uint8
)

sx0 = max(0, x0)
sy0 = max(0, y0)

sx1 = min(result.shape[1], x0 + side)
sy1 = min(result.shape[0], y0 + side)

dx0 = sx0 - x0
dy0 = sy0 - y0

dx1 = dx0 + sx1 - sx0
dy1 = dy0 + sy1 - sy0

canvas[dy0:dy1, dx0:dx1] = result[
    sy0:sy1, sx0:sx1
]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

Image.fromarray(canvas).save(OUTPUT)

print("--------------------------------")
print("PHOTO PREPARATION COMPLETE")
print("--------------------------------")
print("Output:", OUTPUT)
print("Dimensions:", canvas.shape)
