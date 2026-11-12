"""
Commit Metro - every line is a language, every stop is a project.

Same dark terminal window as the other profile cards. Languages become metro
lines that converge on an @username hub; repos are the stops. White trains
run through the hub forever (SMIL animation, works inside README <img>).

Data:  GitHub REST API  ->  cached in data/repos.json
       (if the API call fails, the cached file is used)

Usage:
    python scripts/make_metro.py [out.svg]
    STATIC=1 python scripts/make_metro.py        # no animation
    METRO_MONO=1 python scripts/make_metro.py    # pure gray lines

Optional env: GH_PROFILE_USER, GITHUB_TOKEN, MAX_LANGS (default 6),
              MAX_STOPS (default 3), INCLUDE_FORKS=1

Pure standard library - no pip install needed.
"""

import html
import json
import math
import os
import sys
import urllib.request
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT_DIR / "contrib-metro.svg"
CACHE = PROJECT_DIR / "data" / "repos.json"

USERNAME = os.environ.get("GH_PROFILE_USER", "Asmitcod").strip()
TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
STATIC = os.environ.get("STATIC", "").lower() in ("1", "true", "yes")
MONO = os.environ.get("METRO_MONO", "").lower() in ("1", "true", "yes")
INCLUDE_FORKS = os.environ.get("INCLUDE_FORKS", "").lower() in ("1", "true", "yes")
MAX_LANGS = int(os.environ.get("MAX_LANGS", 6))
MAX_STOPS = int(os.environ.get("MAX_STOPS", 3))

# ---------------------------------------------------------------- palette
BG = "#0d1117"
BG2 = "#111722"
FRAME = "#30363d"
TITLE_TEXT = "#7d8590"
INK = "#c9d1d9"
TRAIN = "#f0f6fc"

LANG_COLORS = {
    "Python": "#3572A5", "TypeScript": "#3178c6", "JavaScript": "#f1e05a",
    "Java": "#b07219", "HTML": "#e34c26", "CSS": "#563d7c", "C": "#8a8a8a",
    "C++": "#f34b7d", "Jupyter Notebook": "#DA5B0B", "Shell": "#89e051",
    "Go": "#00ADD8", "Rust": "#dea584", "Kotlin": "#A97BFF", "Dart": "#00B4AB",
    "PowerShell": "#5391fe", "Batchfile": "#C1F12E", "Dockerfile": "#384d54",
}
MONO_SHADES = ["#4a525d", "#3d4550", "#555d68", "#444c57", "#5e6671", "#3a424d"]

# ---------------------------------------------------------------- layout
PAD = 20
TITLEBAR_H = 30
STATUS_H = 30
W = 840
HUB_X = W / 2
ROW_GAP = 82
PILL_W, PILL_H = 112, 26
CAR_W, CAR_H = 18, 8
SPEED = 120.0        # px per second


def mix(c1, c2, t):
    """t=0 -> c1, t=1 -> c2"""
    a = [int(c1.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(c2.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def fmt(n):
    return f"{n:.1f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------- data
def fetch_repos():
    url = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&type=owner&sort=pushed"
    headers = {"User-Agent": "commit-metro", "Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=25) as r:
            data = json.load(r)
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(data, indent=1), encoding="utf-8")
        print(f"Fetched {len(data)} repos from the API")
        return data
    except Exception as e:  # noqa: BLE001
        print(f"API fetch failed ({e}); trying cache {CACHE}")
        if CACHE.exists():
            return json.loads(CACHE.read_text(encoding="utf-8"))
        raise SystemExit("No repo data: API failed and data/repos.json does not exist.")


def group_languages(repos):
    langs = {}
    for r in repos:
        if not r.get("language"):
            continue
        if r.get("fork") and not INCLUDE_FORKS:
            continue
        if r.get("archived"):
            continue
        if r["name"].lower() == USERNAME.lower():      # the profile repo itself
            continue
        langs.setdefault(r["language"], []).append(r)
    for lang in langs:
        langs[lang].sort(key=lambda r: r.get("pushed_at", ""), reverse=True)
    ranked = sorted(langs.items(),
                    key=lambda kv: (-len(kv[1]), -max(x.get("pushed_at", "") and
                                                      int(x["pushed_at"][:10].replace("-", "")) for x in kv[1])))
    return ranked[:MAX_LANGS]


# ---------------------------------------------------------------- build lines
repos = fetch_repos()
ranked = group_languages(repos)
if not ranked:
    raise SystemExit("No repositories with a language were found.")

left_langs = ranked[0::2]
right_langs = ranked[1::2]


def offsets(k):
    return [(i - (k - 1) / 2) * ROW_GAP for i in range(k)]


k_max = max(len(left_langs), len(right_langs), 1)
half_span = max(abs(o) for o in offsets(k_max)) if k_max > 1 else 0

HEADER_H = 78
ART_TOP = TITLEBAR_H + HEADER_H
CY = ART_TOP + 34 + half_span + 16
ART_BOTTOM = CY + half_span + 56
STATUS_LINE_Y = ART_BOTTOM
H = STATUS_LINE_Y + STATUS_H
STATUS_Y = STATUS_LINE_Y + 19


def style_for(lang, idx):
    base = LANG_COLORS.get(lang, "#8b949e")
    if MONO:
        line = MONO_SHADES[idx % len(MONO_SHADES)]
        return line, "#1a212b", INK
    return mix(BG, base, 0.42), mix(BG, base, 0.22), mix(base, INK, 0.55)


lines = []   # dicts: side, y, color, pill, text, stops, path_in (pill->hub)
idx = 0
for side, group in (("L", left_langs), ("R", right_langs)):
    offs = offsets(len(group))
    for (lang, rs), off in zip(group, offs):
        y = CY + off
        dy = abs(off)
        line_c, pill_c, text_c = style_for(lang, idx)
        idx += 1
        if side == "L":
            x_pill_end = PAD + 4 + PILL_W
            x_start = x_pill_end - 8
            x_diag = HUB_X - dy
            pts = [(x_start, y), (x_diag, y), (HUB_X, CY)]
            run0, run1 = x_pill_end + 40, x_diag - 26
        else:
            x_pill_start = W - PAD - 4 - PILL_W
            x_start = x_pill_start + 8
            x_diag = HUB_X + dy
            pts = [(x_start, y), (x_diag, y), (HUB_X, CY)]
            run1, run0 = x_pill_start - 40, x_diag + 26
        stops_r = rs[:MAX_STOPS]
        n = len(stops_r)
        lo, hi = min(run0, run1), max(run0, run1)
        if hi - lo < 40:
            hi = lo + 40
        xs = [(lo + hi) / 2] if n == 1 else [lo + (hi - lo) * j / (n - 1) for j in range(n)]
        if side == "R":
            xs = list(reversed(xs))          # first (newest) repo nearest the pill
        lines.append(dict(side=side, y=y, color=line_c, pill_c=pill_c, text_c=text_c,
                          lang=lang, repos=rs, stops=list(zip(stops_r, xs)), pts=pts))


def path_d(pts):
    return "M" + "L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts)


def plen(pts):
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


# ---------------------------------------------------------------- svg
p = []
p.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{fmt(H)}" viewBox="0 0 {W} {fmt(H)}" '
    f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">'
)
p.append(
    f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/></linearGradient>'
    f'<radialGradient id="glow" cx="0.5" cy="0.55" r="0.5">'
    f'<stop offset="0" stop-color="{INK}" stop-opacity="0.06"/>'
    f'<stop offset="1" stop-color="{INK}" stop-opacity="0"/></radialGradient>'
    f'<filter id="tglow" x="-60%" y="-200%" width="220%" height="500%">'
    f'<feGaussianBlur stdDeviation="2.2" result="b"/>'
    f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
)
p.append(f'<rect width="{W}" height="{fmt(H)}" rx="12" fill="url(#bg)"/>')
p.append(f'<rect width="{W}" height="{fmt(H)}" rx="12" fill="url(#glow)"/>')
p.append(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{fmt(H - 1)}" rx="12" fill="none" stroke="{FRAME}"/>')

# title bar
p.append(f'<line x1="0" y1="{TITLEBAR_H}" x2="{W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>')
for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    p.append(f'<circle cx="{PAD + i * 16}" cy="{TITLEBAR_H / 2}" r="5" fill="{c}"/>')
p.append(f'<text x="{W / 2}" y="{TITLEBAR_H / 2 + 4}" fill="{TITLE_TEXT}" font-size="12" '
         f'text-anchor="middle">asmit@github: ~$ ./metro.sh</text>')

# header
p.append(f'<text x="{PAD + 14}" y="{TITLEBAR_H + 30}" fill="{TITLE_TEXT}" font-size="10" '
         f'letter-spacing="3">COMMIT METRO</text>')
p.append(f'<text x="{PAD + 14}" y="{TITLEBAR_H + 58}" fill="{INK}" font-size="20" font-weight="700">'
         f'Every line is a language, every stop a project</text>')

# lines (drawn in)
for n, ln in enumerate(lines):
    d = path_d(ln["pts"])
    if STATIC:
        p.append(f'<path d="{d}" fill="none" stroke="{ln["color"]}" stroke-width="9" '
                 f'stroke-linejoin="round" stroke-linecap="round"/>')
    else:
        p.append(
            f'<path d="{d}" fill="none" stroke="{ln["color"]}" stroke-width="9" stroke-linejoin="round" '
            f'stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1">'
            f'<animate attributeName="stroke-dashoffset" from="1" to="0" dur="1.1s" '
            f'begin="{0.15 + n * 0.12:.2f}s" fill="freeze" calcMode="spline" keyTimes="0;1" '
            f'keySplines="0.3 0.7 0.3 1"/></path>'
        )

# pills
for ln in lines:
    px = PAD + 4 if ln["side"] == "L" else W - PAD - 4 - PILL_W
    py = ln["y"] - PILL_H / 2
    p.append(f'<rect x="{px}" y="{fmt(py)}" width="{PILL_W}" height="{PILL_H}" rx="{PILL_H / 2}" '
             f'fill="{ln["pill_c"]}" stroke="{ln["color"]}" stroke-width="1"/>')
    p.append(f'<text x="{px + PILL_W / 2}" y="{fmt(ln["y"] + 4)}" fill="{ln["text_c"]}" font-size="11" '
             f'font-weight="700" letter-spacing="1" text-anchor="middle">{html.escape(ln["lang"].upper()[:13])}</text>')

# stops + labels
for ln in lines:
    for j, (r, x) in enumerate(ln["stops"]):
        y = ln["y"]
        name = r["name"]
        label = name if len(name) <= 14 else name[:13] + "…"
        above = (j % 2 == 0)
        ty = y - 17 if above else y + 26
        stars = r.get("stargazers_count", 0)
        tip = f'{name} · {ln["lang"]}' + (f" · ★{stars}" if stars else "")
        p.append(
            f'<g><title>{html.escape(tip)}</title>'
            f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="7.5" fill="{BG}" stroke="{INK}" stroke-width="2.5"/>'
            f'<text x="{fmt(x)}" y="{fmt(ty)}" fill="{INK}" font-size="11" text-anchor="middle" '
            f'opacity="0.85">{html.escape(label)}</text></g>'
        )
    extra = len(ln["repos"]) - len(ln["stops"])
    if extra > 0:
        ex = ln["pts"][0][0] + (-1 if ln["side"] == "R" else 1) * 0
        px_end = (PAD + 4 + PILL_W + 6) if ln["side"] == "L" else (W - PAD - 4 - PILL_W - 6)
        anchor = "start" if ln["side"] == "L" else "end"
        p.append(f'<text x="{px_end}" y="{fmt(ln["y"] + 26)}" fill="{TITLE_TEXT}" font-size="10" '
                 f'text-anchor="{anchor}">+{extra} more</text>')

# trains
if not STATIC:
    def route_for(i):
        left = [l for l in lines if l["side"] == "L"]
        right = [l for l in lines if l["side"] == "R"]
        routes = []
        for k in range(max(len(left), len(right))):
            a = left[k] if k < len(left) else None
            b = right[k] if k < len(right) else None
            if a and b:
                fwd = a["pts"] + list(reversed(b["pts"]))[1:]
            else:
                fwd = (a or b)["pts"]
            routes.append(fwd)
        return routes

    routes = route_for(0)
    cars = [(TRAIN, 1.0), (INK, 0.8), (INK, 0.55)]
    for ri, pts in enumerate(routes):
        pts = pts if ri % 2 == 0 else list(reversed(pts))
        d = path_d(pts)
        dur = plen(pts) / SPEED
        for t in range(2):                                   # two trains per route
            start = 1.6 + ri * 0.7 + t * dur / 2
            for ci, (col, op) in enumerate(cars):
                b = start + ci * (CAR_W + 3) / SPEED
                p.append(
                    f'<rect x="{-CAR_W / 2}" y="{-CAR_H / 2}" width="{CAR_W}" height="{CAR_H}" rx="3" '
                    f'fill="{col}" opacity="0" filter="url(#tglow)">'
                    f'<set attributeName="opacity" to="{op}" begin="{b:.2f}s"/>'
                    f'<animateMotion path="{d}" dur="{dur:.2f}s" begin="{b:.2f}s" repeatCount="indefinite" '
                    f'rotate="auto"/></rect>'
                )

# hub
hub_w = 118
p.append(
    f'<ellipse cx="{HUB_X}" cy="{CY}" rx="{hub_w / 2 + 4}" ry="17" fill="none" stroke="{INK}" stroke-width="1" opacity="0.0">'
    + ("" if STATIC else
       f'<animate attributeName="rx" values="{hub_w / 2 + 4};{hub_w / 2 + 26}" dur="3s" repeatCount="indefinite"/>'
       f'<animate attributeName="ry" values="17;30" dur="3s" repeatCount="indefinite"/>'
       f'<animate attributeName="opacity" values="0.35;0" dur="3s" repeatCount="indefinite"/>')
    + '</ellipse>'
)
p.append(f'<rect x="{HUB_X - hub_w / 2}" y="{CY - 14}" width="{hub_w}" height="28" rx="14" fill="#090c10" '
         f'stroke="{FRAME}" stroke-width="1.5"/>')
p.append(f'<text x="{HUB_X}" y="{CY + 4.5}" fill="{INK}" font-size="12" font-weight="700" '
         f'text-anchor="middle">@{html.escape(USERNAME.lower())}</text>')

# status bar
p.append(f'<line x1="0" y1="{fmt(STATUS_LINE_Y)}" x2="{W}" y2="{fmt(STATUS_LINE_Y)}" stroke="{FRAME}"/>')
n_repos = sum(len(l["repos"]) for l in lines)
status = f"asmit@github:~$ ./metro.sh --lines {len(lines)} --stops "
p.append(
    f'<text x="{PAD}" y="{fmt(STATUS_Y)}" fill="{TITLE_TEXT}" font-size="13" xml:space="preserve">'
    f'{html.escape(status)}<tspan fill="{INK}">{n_repos}</tspan></text>'
)
cx = PAD + (len(status) + len(str(n_repos)) + 1) * 13 * 0.6
p.append(
    f'<rect x="{fmt(cx)}" y="{fmt(STATUS_Y - 12)}" width="8" height="14" fill="{INK}">'
    f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" dur="1s" repeatCount="indefinite"/></rect>'
)
p.append("</svg>")

svg = "".join(p)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(svg, encoding="utf-8")

print("--------------------------------")
print("COMMIT METRO GENERATED")
print("--------------------------------")
for l in lines:
    print(f'  {l["side"]} {l["lang"]:<14} {len(l["repos"])} repos -> ' + ", ".join(r["name"] for r, _ in l["stops"]))
print("Output:", OUT)
print("Canvas:", W, "x", round(H), "| size:", len(svg), "bytes")