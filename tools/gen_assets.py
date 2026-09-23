#!/usr/bin/env python3
"""Generate the animated SVG assets for the profile README.

Everything animates with SMIL only (no CSS, no <script>) so GitHub's camo proxy
serves it as a plain image and the motion survives. Run:

    python3 tools/gen_assets.py

Needs fontTools + Pillow + numpy (the name is baked into outlines from
tools/fonts/InstrumentSerif-Italic.ttf, since an <img> SVG can't load web fonts).
"""
import base64
import io
import math
import os
import random

import numpy as np
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from PIL import Image

HERE   = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
FONT   = os.path.join(HERE, "fonts", "InstrumentSerif-Italic.ttf")
NAME   = "Bhavith Parna"

# palette: espresso -> walnut -> cinnamon -> caramel -> latte -> sand -> cream
ESPRESSO = "#140D08"
ROAST    = "#22160E"
COFFEE   = "#3A2718"
WALNUT   = "#5C3D26"
CINNAMON = "#8B5A2B"
CARAMEL  = "#C08552"
GOLD     = "#D4A373"
LATTE    = "#DDB892"
SAND     = "#E6CCB2"
CREAM    = "#F5EBE0"
IVORY    = "#FFF8EE"

W = 1200


# ── helpers ──────────────────────────────────────────────────────────────────

def f(x):
    """Short number formatting keeps the files small."""
    s = f"{x:.1f}"
    return s[:-2] if s.endswith(".0") else s


def mix(a, b, t):
    a = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(a, b))


def ramp(stops, t):
    """Sample a multi-stop colour ramp at t in [0, 1]."""
    t = min(max(t, 0), 1) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2)
    return mix(stops[i], stops[i + 1], t - i)


def smooth_path(pts, closed=False):
    """Catmull-Rom through pts, emitted as cubic Béziers."""
    n = len(pts)
    get = (lambda i: pts[i % n]) if closed else (lambda i: pts[min(max(i, 0), n - 1)])
    d = f"M{f(pts[0][0])} {f(pts[0][1])}"
    for i in range(n if closed else n - 1):
        p0, p1, p2, p3 = get(i - 1), get(i), get(i + 1), get(i + 2)
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f"C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(p2[0])} {f(p2[1])}"
    return d + ("Z" if closed else "")


def grain_pattern(pid="grain", size=160, alpha=34, seed=7):
    """A tiling film-grain PNG. Cheaper than feTurbulence, which would be
    recomputed on every animation frame."""
    rng = np.random.default_rng(seed)
    lum = rng.integers(0, 256, (size, size), dtype=np.uint8)
    a = (rng.random((size, size)) * alpha).astype(np.uint8)
    img = Image.fromarray(np.dstack([lum, lum, lum, a]), "RGBA")
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return (f'<pattern id="{pid}" width="{size}" height="{size}" patternUnits="userSpaceOnUse">'
            f'<image width="{size}" height="{size}" href="data:image/png;base64,{b64}"/></pattern>')


def svg(w, h, body, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" '
            f'height="{h}" role="img" aria-label="{label}">\n{body}\n</svg>\n')


def spin(cx, cy, dur, reverse=False, begin=0):
    a, b = (360, 0) if reverse else (0, 360)
    return (f'<animateTransform attributeName="transform" type="rotate" '
            f'from="{a} {cx} {cy}" to="{b} {cx} {cy}" dur="{dur}s" begin="{begin}s" '
            f'repeatCount="indefinite"/>')


def star4(cx, cy, r):
    """Four-point sparkle."""
    k = r * 0.18
    return (f"M{f(cx)} {f(cy - r)}Q{f(cx + k)} {f(cy - k)} {f(cx + r)} {f(cy)}"
            f"Q{f(cx + k)} {f(cy + k)} {f(cx)} {f(cy + r)}"
            f"Q{f(cx - k)} {f(cy + k)} {f(cx - r)} {f(cy)}"
            f"Q{f(cx - k)} {f(cy - k)} {f(cx)} {f(cy - r)}Z")


# ── name outlines ────────────────────────────────────────────────────────────

def name_glyphs(text, size, cx, baseline):
    """Return [(path_d, x_left, advance)] with the run centred on cx."""
    font = TTFont(FONT)
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    upm = font["head"].unitsPerEm
    s = size / upm
    names = [cmap[ord(c)] for c in text]
    adv = [font["hmtx"][g][0] * s for g in names]
    x = cx - sum(adv) / 2
    out = []
    for g, a in zip(names, adv):
        pen = SVGPathPen(gs, ntos=f)
        gs[g].draw(TransformPen(pen, (s, 0, 0, -s, x, baseline)))
        d = pen.getCommands()
        if d:
            out.append((d, x, a))
        x += a
    return out


# ── 1. hero ──────────────────────────────────────────────────────────────────

def hero():
    H = 520
    cx, cy = W / 2, 250
    rnd = random.Random(11)
    p = []
    p.append(f'''<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{ESPRESSO}"/><stop offset="0.55" stop-color="{ROAST}"/>
    <stop offset="1" stop-color="#1A100A"/>
  </linearGradient>''')
    blobs = [(CARAMEL, 0.55, 340), (CINNAMON, 0.6, 380), (GOLD, 0.32, 260),
             (WALNUT, 0.7, 420), ("#C9957A", 0.28, 300), (LATTE, 0.18, 240)]
    for i, (c, o, _) in enumerate(blobs):
        p.append(f'  <radialGradient id="b{i}"><stop offset="0" stop-color="{c}" stop-opacity="{o}"/>'
                 f'<stop offset="0.6" stop-color="{c}" stop-opacity="{o * 0.35:.2f}"/>'
                 f'<stop offset="1" stop-color="{c}" stop-opacity="0"/></radialGradient>')
    p.append(f'''  <linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="-700" y1="0" x2="0" y2="0" spreadMethod="repeat">
    <stop offset="0" stop-color="{CARAMEL}"/><stop offset="0.38" stop-color="{LATTE}"/>
    <stop offset="0.5" stop-color="{IVORY}"/><stop offset="0.62" stop-color="{LATTE}"/>
    <stop offset="1" stop-color="{CARAMEL}"/>
    <animateTransform attributeName="gradientTransform" type="translate" from="0 0" to="700 0" dur="6s" repeatCount="indefinite"/>
  </linearGradient>
  <linearGradient id="rule" x1="0" x2="1">
    <stop offset="0" stop-color="{GOLD}" stop-opacity="0"/><stop offset="0.5" stop-color="{SAND}"/>
    <stop offset="1" stop-color="{GOLD}" stop-opacity="0"/>
  </linearGradient>
  <radialGradient id="vig" cx="0.5" cy="0.5" r="0.75">
    <stop offset="0.6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.45"/>
  </radialGradient>
  <radialGradient id="dot"><stop offset="0" stop-color="{IVORY}"/><stop offset="0.35" stop-color="{LATTE}" stop-opacity="0.8"/>
    <stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>
  <filter id="soft" x="-20%" y="-40%" width="140%" height="180%"><feGaussianBlur stdDeviation="10"/></filter>
  {grain_pattern()}
  <clipPath id="card"><rect width="{W}" height="{H}" rx="20"/></clipPath>
</defs>
<rect width="{W}" height="{H}" rx="20" fill="url(#bg)"/>
<g clip-path="url(#card)">''')

    # drifting colour fields
    for i, (_, _, r) in enumerate(blobs):
        pts = [(rnd.uniform(80, W - 80), rnd.uniform(40, H - 40)) for _ in range(4)]
        pts.append(pts[0])
        vals = ";".join(f"{f(x)} {f(y)}" for x, y in pts)
        dur = rnd.uniform(18, 30)
        p.append(f'  <circle r="{r}" fill="url(#b{i})"><animateTransform attributeName="transform" '
                 f'type="translate" values="{vals}" dur="{dur:.1f}s" calcMode="spline" '
                 f'keySplines="{";".join(["0.45 0 0.55 1"] * 4)}" repeatCount="indefinite"/></circle>')

    # counter-rotating orbit rings behind the name
    for k, r in enumerate(range(150, 700, 34)):
        dash = ["", ' stroke-dasharray="2 10"', ' stroke-dasharray="40 14 4 14"', ' stroke-dasharray="1 5"'][k % 4]
        op = 0.05 + 0.07 * (k % 3 == 0)
        p.append(f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{SAND}" stroke-opacity="{op:.2f}" '
                 f'stroke-width="1"{dash}>{spin(cx, cy, 90 + k * 17, reverse=k % 2)}</circle>')

    # a tilted orbit with a travelling light
    orbit = f"M{cx - 470} {cy}A470 110 0 1 1 {cx + 470} {cy}A470 110 0 1 1 {cx - 470} {cy}"
    p.append(f'''  <g transform="rotate(-9 {cx} {cy})">
    <path d="{orbit}" fill="none" stroke="{LATTE}" stroke-opacity="0.22" stroke-width="1"/>
    <circle r="16" fill="url(#dot)"><animateMotion dur="14s" repeatCount="indefinite" path="{orbit}"/></circle>
    <circle r="9" fill="url(#dot)" opacity="0.7"><animateMotion dur="14s" begin="-7s" repeatCount="indefinite" path="{orbit}"/></circle>
  </g>''')

    # rising dust
    for _ in range(90):
        x = rnd.uniform(0, W)
        r = rnd.choice([0.8, 1, 1.2, 1.6, 2.2])
        dur = rnd.uniform(9, 22)
        drift = rnd.uniform(-60, 60)
        op = rnd.uniform(0.3, 0.9)
        p.append(f'  <circle cx="{f(x)}" cy="{H + 10}" r="{r}" fill="{rnd.choice([CREAM, SAND, LATTE, GOLD])}">'
                 f'<animateTransform attributeName="transform" type="translate" from="0 0" to="{f(drift)} {-H - 40}" '
                 f'dur="{dur:.1f}s" begin="{-rnd.uniform(0, dur):.1f}s" repeatCount="indefinite"/>'
                 f'<animate attributeName="opacity" values="0;{op:.2f};{op * 0.4:.2f};{op:.2f};0" dur="{dur:.1f}s" '
                 f'begin="{-rnd.uniform(0, dur):.1f}s" repeatCount="indefinite"/></circle>')

    # sparkles
    for x, y, r, b in [(212, 118, 11, 0), (1010, 96, 8, 1.3), (960, 404, 12, 2.1), (240, 392, 7, 3.2),
                       (120, 250, 5, 0.7), (1085, 250, 6, 2.6), (600, 64, 7, 1.9)]:
        p.append(f'  <path d="{star4(x, y, r)}" fill="{IVORY}" opacity="0">'
                 f'<animate attributeName="opacity" values="0;1;0" dur="3.6s" begin="{b + 1.5}s" repeatCount="indefinite"/>'
                 f'{spin(x, y, 7)}</path>')

    # the name: stroke draws on, then the shimmering fill arrives
    glyphs = name_glyphs(NAME, 158, cx, cy + 46)
    all_d = "".join(d for d, _, _ in glyphs)
    p.append(f'  <path d="{all_d}" fill="{GOLD}" opacity="0" filter="url(#soft)">'
             f'<animate attributeName="opacity" values="0;0.55;0.3;0.55" keyTimes="0;0.2;0.6;1" dur="6s" begin="2.4s" '
             f'fill="freeze" repeatCount="indefinite"/></path>')
    for i, (d, _, _) in enumerate(glyphs):
        b = 0.25 + i * 0.13
        p.append(f'  <path d="{d}" pathLength="1" fill="url(#shine)" fill-opacity="0" stroke="{SAND}" '
                 f'stroke-width="1.4" stroke-dasharray="1" stroke-dashoffset="1">'
                 f'<animate attributeName="stroke-dashoffset" from="1" to="0" dur="1.8s" begin="{b:.2f}s" '
                 f'calcMode="spline" keySplines="0.6 0 0.3 1" keyTimes="0;1" fill="freeze"/>'
                 f'<animate attributeName="fill-opacity" from="0" to="1" dur="1.1s" begin="{b + 1.3:.2f}s" fill="freeze"/>'
                 f'<animate attributeName="stroke-opacity" from="1" to="0.25" dur="1.1s" begin="{b + 1.5:.2f}s" fill="freeze"/>'
                 f'</path>')

    # rule under the name, opening from the centre
    ry = cy + 96
    p.append(f'''  <line x1="{cx}" y1="{ry}" x2="{cx}" y2="{ry}" stroke="url(#rule)" stroke-width="1.2">
    <animate attributeName="x1" to="{cx - 300}" dur="1.4s" begin="2.6s" calcMode="spline" keySplines="0.2 0 0.2 1" keyTimes="0;1" fill="freeze"/>
    <animate attributeName="x2" to="{cx + 300}" dur="1.4s" begin="2.6s" calcMode="spline" keySplines="0.2 0 0.2 1" keyTimes="0;1" fill="freeze"/>
  </line>
  <g opacity="0"><animate attributeName="opacity" to="1" dur="0.8s" begin="3.4s" fill="freeze"/>
    <path d="{star4(cx, ry, 9)}" fill="{CREAM}">{spin(cx, ry, 12)}</path>
    <circle cx="{cx - 310}" cy="{ry}" r="2.4" fill="{LATTE}"/><circle cx="{cx + 310}" cy="{ry}" r="2.4" fill="{LATTE}"/>
  </g>''')

    p.append(f'''  <rect width="{W}" height="{H}" fill="url(#vig)"/>
  <rect width="{W}" height="{H}" fill="url(#grain)"/>
</g>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="19.5" fill="none" stroke="{GOLD}" stroke-opacity="0.22"/>''')
    return svg(W, H, "\n".join(p), NAME)


# ── 2. silk ribbon ───────────────────────────────────────────────────────────

def silk():
    H = 300
    n, cols, frames = 44, 16, 8
    p = [f'''<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{ESPRESSO}"/><stop offset="0.5" stop-color="#1E130C"/><stop offset="1" stop-color="{ESPRESSO}"/>
  </linearGradient>
  <linearGradient id="thread" x1="0" x2="1">
    <stop offset="0" stop-color="{CINNAMON}" stop-opacity="0"/><stop offset="0.2" stop-color="{CARAMEL}"/>
    <stop offset="0.5" stop-color="{IVORY}"/><stop offset="0.8" stop-color="{CARAMEL}"/>
    <stop offset="1" stop-color="{CINNAMON}" stop-opacity="0"/>
  </linearGradient>
  <radialGradient id="glow" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="{CARAMEL}" stop-opacity="0.32"/><stop offset="1" stop-color="{CARAMEL}" stop-opacity="0"/>
  </radialGradient>
  <clipPath id="card"><rect width="{W}" height="{H}" rx="20"/></clipPath>
</defs>
<rect width="{W}" height="{H}" rx="20" fill="url(#bg)"/>
<g clip-path="url(#card)">
  <ellipse cx="{W / 2}" cy="{H / 2}" rx="620" ry="170" fill="url(#glow)">
    <animate attributeName="rx" values="560;680;560" dur="9s" repeatCount="indefinite"/>
  </ellipse>''']
    cy = H / 2
    for i in range(n):
        u = i / (n - 1) - 0.5                     # position across the ribbon
        ds = []
        for fr in range(frames + 1):
            ph = 2 * math.pi * fr / frames
            pts = []
            for j in range(cols + 1):
                x = -40 + (W + 80) * j / cols
                t = x / W
                env = math.sin(math.pi * min(max(t, 0), 1)) ** 0.8 * 0.85 + 0.15
                twist = math.cos(ph + t * 5.2 + 0.6)
                y = (cy + 62 * math.sin(ph + t * 6.3) * env
                     + u * 170 * twist * env
                     + 22 * math.sin(2 * ph - t * 9 + u * 3))
                pts.append((x, y))
            ds.append(smooth_path(pts))
        op = 0.22 + 0.7 * (1 - abs(u) * 2) ** 1.5
        wdt = 0.7 + 0.8 * (1 - abs(u) * 2)
        p.append(f'  <path fill="none" stroke="url(#thread)" stroke-width="{wdt:.2f}" stroke-opacity="{op:.2f}" d="{ds[0]}">'
                 f'<animate attributeName="d" values="{";".join(ds)}" dur="16s" repeatCount="indefinite"/></path>')
    p.append("</g>")
    p.append(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="19.5" fill="none" stroke="{GOLD}" stroke-opacity="0.18"/>')
    return svg(W, H, "\n".join(p), "silk threads twisting")


# ── 3. gallery: mandala / dot globe / liquid ─────────────────────────────────

def tile_open(S, extra_defs=""):
    return f'''<defs>
  <radialGradient id="bg" cx="0.5" cy="0.45" r="0.75">
    <stop offset="0" stop-color="#2E1F14"/><stop offset="1" stop-color="{ESPRESSO}"/>
  </radialGradient>
  <clipPath id="card"><rect width="{S}" height="{S}" rx="20"/></clipPath>
  {extra_defs}
</defs>
<rect width="{S}" height="{S}" rx="20" fill="url(#bg)"/>
<g clip-path="url(#card)">'''


def tile_close(S):
    return (f'</g>\n<rect x="0.5" y="0.5" width="{S - 1}" height="{S - 1}" rx="19.5" fill="none" '
            f'stroke="{GOLD}" stroke-opacity="0.2"/>')


def mandala():
    S = 400
    c = S / 2
    p = [tile_open(S, f'''<radialGradient id="core"><stop offset="0" stop-color="{IVORY}"/>
    <stop offset="0.4" stop-color="{GOLD}" stop-opacity="0.7"/><stop offset="1" stop-color="{CARAMEL}" stop-opacity="0"/></radialGradient>''')]

    def petal(r0, r1, w):
        """A vesica pointing up from radius r0 to r1."""
        m = (r0 + r1) / 2
        return (f"M{f(c)} {f(c - r0)}Q{f(c + w)} {f(c - m)} {f(c)} {f(c - r1)}"
                f"Q{f(c - w)} {f(c - m)} {f(c)} {f(c - r0)}Z")

    rings = [  # (count, r0, r1, width, colour, dur, reverse, fill-opacity)
        (8, 16, 70, 22, IVORY, 40, False, 0.10),
        (12, 46, 112, 20, LATTE, 60, True, 0.05),
        (16, 86, 150, 16, GOLD, 80, False, 0.04),
        (24, 132, 176, 9, CARAMEL, 110, True, 0.0),
    ]
    for cnt, r0, r1, w, col, dur, rev, fo in rings:
        d = petal(r0, r1, w)
        g = "".join(f'<path d="{d}" transform="rotate({360 * k / cnt:.2f} {c} {c})"/>' for k in range(cnt))
        p.append(f'  <g fill="{col}" fill-opacity="{fo}" stroke="{col}" stroke-opacity="0.7" stroke-width="0.9">{g}'
                 f'{spin(c, c, dur, rev)}</g>')
    for r, dash, dur, rev in [(40, "1 4", 30, True), (122, "3 6", 70, False), (160, "1 3", 50, True),
                              (184, "30 8 2 8", 120, False)]:
        p.append(f'  <circle cx="{c}" cy="{c}" r="{r}" fill="none" stroke="{SAND}" stroke-opacity="0.45" '
                 f'stroke-dasharray="{dash}">{spin(c, c, dur, rev)}</circle>')
    # beads riding the outer ring
    beads = "".join(f'<circle cx="{f(c + 184 * math.cos(2 * math.pi * k / 6))}" '
                    f'cy="{f(c + 184 * math.sin(2 * math.pi * k / 6))}" r="3.2" fill="{CREAM}"/>' for k in range(6))
    p.append(f'  <g>{beads}{spin(c, c, 24)}</g>')
    # breathing core
    p.append(f'''  <circle cx="{c}" cy="{c}" r="34" fill="url(#core)">
    <animate attributeName="r" values="26;42;26" dur="4s" calcMode="spline" keySplines="0.4 0 0.6 1;0.4 0 0.6 1" repeatCount="indefinite"/>
  </circle>
  <path d="{star4(c, c, 12)}" fill="{IVORY}">{spin(c, c, 10, True)}</path>''')
    # expanding pulse rings
    for k in range(3):
        p.append(f'  <circle cx="{c}" cy="{c}" r="20" fill="none" stroke="{GOLD}" stroke-width="1.2">'
                 f'<animate attributeName="r" from="20" to="200" dur="6s" begin="{-2 * k}s" repeatCount="indefinite"/>'
                 f'<animate attributeName="stroke-opacity" from="0.6" to="0" dur="6s" begin="{-2 * k}s" repeatCount="indefinite"/></circle>')
    p.append(tile_close(S))
    return svg(S, S, "\n".join(p), "rotating mandala")


def globe():
    S = 400
    c = S / 2
    R = 128
    tilt = math.radians(24)
    period = 24
    steps = 30
    p = [tile_open(S, f'''<radialGradient id="halo"><stop offset="0.55" stop-color="{CARAMEL}" stop-opacity="0.35"/>
    <stop offset="1" stop-color="{CARAMEL}" stop-opacity="0"/></radialGradient>
  <radialGradient id="body" cx="0.38" cy="0.32" r="0.8"><stop offset="0" stop-color="#5A3B24"/>
    <stop offset="1" stop-color="#1A100A"/></radialGradient>
  <radialGradient id="moon"><stop offset="0" stop-color="{IVORY}"/><stop offset="0.5" stop-color="{LATTE}" stop-opacity="0.8"/>
    <stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>''')]
    p.append(f'  <circle cx="{c}" cy="{c}" r="{R + 60}" fill="url(#halo)"/>')
    p.append(f'  <circle cx="{c}" cy="{c}" r="{R}" fill="url(#body)" stroke="{GOLD}" stroke-opacity="0.35"/>')

    # back half of the orbit ring, drawn behind the sphere dots
    orx, ory = R + 50, 26
    p.append(f'  <g transform="rotate(-18 {c} {c})"><path d="M{c - orx} {c}A{orx} {ory} 0 0 1 {c + orx} {c}" '
             f'fill="none" stroke="{LATTE}" stroke-opacity="0.25"/></g>')

    lats = [-70, -52, -35, -18, 0, 18, 35, 52, 70]
    for lat in lats:
        phi = math.radians(lat)
        ndots = max(8, round(26 * math.cos(phi)))
        xs, ys, ops, rs = [], [], [], []
        for s in range(steps + 1):
            lam = 2 * math.pi * s / steps
            x = R * math.cos(phi) * math.sin(lam)
            y = R * math.sin(phi)
            z = R * math.cos(phi) * math.cos(lam)
            yp = y * math.cos(tilt) - z * math.sin(tilt)
            zp = y * math.sin(tilt) + z * math.cos(tilt)
            front = (zp / R + 1) / 2
            xs.append(f"{f(x)} {f(-yp)}")
            ops.append(f"{0.12 + 0.88 * front ** 1.6:.2f}")
            rs.append(f"{1.1 + 2.1 * front:.1f}")
        vals, ov, rv = ";".join(xs), ";".join(ops), ";".join(rs)
        col = ramp([CARAMEL, LATTE, CREAM, LATTE, CARAMEL], (lat + 90) / 180)
        for k in range(ndots):
            b = -period * k / ndots
            p.append(f'  <circle cx="{c}" cy="{c}" fill="{col}">'
                     f'<animateTransform attributeName="transform" type="translate" values="{vals}" dur="{period}s" begin="{b:.2f}s" repeatCount="indefinite"/>'
                     f'<animate attributeName="opacity" values="{ov}" dur="{period}s" begin="{b:.2f}s" repeatCount="indefinite"/>'
                     f'<animate attributeName="r" values="{rv}" dur="{period}s" begin="{b:.2f}s" repeatCount="indefinite"/></circle>')

    # front half of the orbit ring + the moon, which dips behind the globe
    p.append(f'''  <g transform="rotate(-18 {c} {c})">
    <path d="M{c + orx} {c}A{orx} {ory} 0 0 1 {c - orx} {c}" fill="none" stroke="{LATTE}" stroke-opacity="0.55"/>
    <circle r="11" fill="url(#moon)">
      <animateMotion dur="9s" repeatCount="indefinite" path="M{c + orx} {c}A{orx} {ory} 0 0 1 {c - orx} {c}A{orx} {ory} 0 0 1 {c + orx} {c}"/>
      <animate attributeName="opacity" values="1;1;0.15;0.15;1" keyTimes="0;0.5;0.55;0.95;1" dur="9s" repeatCount="indefinite"/>
    </circle>
  </g>''')
    p.append(tile_close(S))
    return svg(S, S, "\n".join(p), "spinning dot globe")


def liquid():
    S = 400
    c = S / 2
    rnd = random.Random(5)
    p = [tile_open(S, f'''<linearGradient id="l0" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{WALNUT}"/><stop offset="1" stop-color="{CINNAMON}"/></linearGradient>
  <linearGradient id="l1" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{CARAMEL}"/><stop offset="1" stop-color="{CINNAMON}"/></linearGradient>
  <linearGradient id="l2" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{CREAM}"/><stop offset="1" stop-color="{GOLD}"/></linearGradient>
  <radialGradient id="gloss" cx="0.35" cy="0.3" r="0.5"><stop offset="0" stop-color="{IVORY}" stop-opacity="0.55"/>
    <stop offset="1" stop-color="{IVORY}" stop-opacity="0"/></radialGradient>''')]

    def blob(r, wob, pts=11):
        return [(c + (r + rnd.uniform(-wob, wob)) * math.cos(2 * math.pi * k / pts),
                 c + (r + rnd.uniform(-wob, wob)) * math.sin(2 * math.pi * k / pts)) for k in range(pts)]

    layers = [("l0", 150, 34, 14, 1), ("l1", 112, 30, 11, 0.95), ("l2", 70, 22, 8, 0.95)]
    for gid, r, wob, dur, op in layers:
        shapes = [smooth_path(blob(r, wob), closed=True) for _ in range(4)]
        shapes.append(shapes[0])
        p.append(f'  <path fill="url(#{gid})" opacity="{op}" d="{shapes[0]}">'
                 f'<animate attributeName="d" values="{";".join(shapes)}" dur="{dur}s" calcMode="spline" '
                 f'keySplines="{";".join(["0.45 0 0.55 1"] * 4)}" repeatCount="indefinite"/>'
                 f'{spin(c, c, dur * 3, gid == "l1")}</path>')
    p.append(f'  <ellipse cx="{c - 18}" cy="{c - 26}" rx="44" ry="30" fill="url(#gloss)"/>')
    # contour lines echoing the blob
    for k, r in enumerate([168, 180, 192]):
        shapes = [smooth_path(blob(r, 10, 12), closed=True) for _ in range(3)]
        shapes.append(shapes[0])
        p.append(f'  <path fill="none" stroke="{SAND}" stroke-opacity="{0.35 - k * 0.1:.2f}" stroke-dasharray="{["", "2 5", "1 7"][k]}" d="{shapes[0]}">'
                 f'<animate attributeName="d" values="{";".join(shapes)}" dur="{12 + k * 3}s" repeatCount="indefinite"/></path>')
    # droplets orbiting
    for k in range(5):
        rr = rnd.uniform(160, 186)
        p.append(f'  <circle cx="{c + rr}" cy="{c}" r="{rnd.uniform(2.5, 5):.1f}" fill="{LATTE}">'
                 f'{spin(c, c, rnd.uniform(10, 22), k % 2, begin=-rnd.uniform(0, 10))}</circle>')
    p.append(tile_close(S))
    return svg(S, S, "\n".join(p), "molten caramel")


# ── 4. dot-matrix ripple ─────────────────────────────────────────────────────

def ripple():
    H = 240
    cols, rows = 64, 11
    gap_x, gap_y = W / cols, H / rows
    srcs = [(W * 0.2, H * 1.6), (W * 0.8, -H * 0.6)]
    dur = 4.2
    p = [f'''<defs><clipPath id="card"><rect width="{W}" height="{H}" rx="20"/></clipPath>
  <linearGradient id="bg" x1="0" x2="1"><stop offset="0" stop-color="{ESPRESSO}"/><stop offset="0.5" stop-color="#20150D"/>
    <stop offset="1" stop-color="{ESPRESSO}"/></linearGradient></defs>
<rect width="{W}" height="{H}" rx="20" fill="url(#bg)"/>
<g clip-path="url(#card)">''']
    for j in range(rows):
        for i in range(cols):
            x = gap_x * (i + 0.5)
            y = gap_y * (j + 0.5)
            d = min(math.hypot(x - sx, y - sy) for sx, sy in srcs)
            b = (d / 70) % dur
            col = ramp([CINNAMON, CARAMEL, LATTE, CREAM, LATTE, CARAMEL, CINNAMON], i / (cols - 1))
            p.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="1.6" fill="{col}">'
                     f'<animate attributeName="r" values="1.6;1.6;5.6;1.6;1.6" keyTimes="0;0.3;0.5;0.7;1" dur="{dur}s" begin="{-b:.2f}s" repeatCount="indefinite"/>'
                     f'<animate attributeName="opacity" values="0.35;0.35;1;0.35;0.35" keyTimes="0;0.3;0.5;0.7;1" dur="{dur}s" begin="{-b:.2f}s" repeatCount="indefinite"/></circle>')
    p.append("</g>")
    p.append(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="19.5" fill="none" stroke="{GOLD}" stroke-opacity="0.18"/>')
    return svg(W, H, "\n".join(p), "rippling dot matrix")


# ── 5. dunes at dusk ─────────────────────────────────────────────────────────

def dunes():
    H = 380
    rnd = random.Random(3)
    sx, sy = 820, 210
    p = [f'''<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#170E08"/><stop offset="0.35" stop-color="#3B2416"/>
    <stop offset="0.62" stop-color="#9A5E33"/><stop offset="0.8" stop-color="{GOLD}"/><stop offset="1" stop-color="{SAND}"/>
  </linearGradient>
  <radialGradient id="sunglow"><stop offset="0" stop-color="{IVORY}" stop-opacity="0.9"/>
    <stop offset="0.25" stop-color="{LATTE}" stop-opacity="0.55"/><stop offset="1" stop-color="{CARAMEL}" stop-opacity="0"/></radialGradient>
  <linearGradient id="sun" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{IVORY}"/><stop offset="1" stop-color="{LATTE}"/></linearGradient>
  {grain_pattern(alpha=30)}
  <clipPath id="card"><rect width="{W}" height="{H}" rx="20"/></clipPath>
  <clipPath id="disc"><circle cx="{sx}" cy="{sy}" r="68"/></clipPath>
</defs>
<rect width="{W}" height="{H}" rx="20" fill="url(#sky)"/>
<g clip-path="url(#card)">''']
    for _ in range(60):
        x, y = rnd.uniform(0, W), rnd.uniform(6, 150)
        dur = rnd.uniform(2.5, 6)
        p.append(f'  <circle cx="{f(x)}" cy="{f(y)}" r="{rnd.choice([0.7, 0.9, 1.2, 1.5])}" fill="{CREAM}">'
                 f'<animate attributeName="opacity" values="0.1;0.9;0.1" dur="{dur:.1f}s" begin="{-rnd.uniform(0, dur):.1f}s" repeatCount="indefinite"/></circle>')
    p.append(f'''  <circle cx="{sx}" cy="{sy}" r="230" fill="url(#sunglow)">
    <animate attributeName="r" values="210;250;210" dur="7s" repeatCount="indefinite"/>
  </circle>''')
    for k in range(4):
        p.append(f'  <circle cx="{sx}" cy="{sy}" r="70" fill="none" stroke="{CREAM}" stroke-width="1">'
                 f'<animate attributeName="r" from="70" to="300" dur="8s" begin="{-2 * k}s" repeatCount="indefinite"/>'
                 f'<animate attributeName="stroke-opacity" from="0.5" to="0" dur="8s" begin="{-2 * k}s" repeatCount="indefinite"/></circle>')
    p.append(f'  <circle cx="{sx}" cy="{sy}" r="68" fill="url(#sun)"/>')
    # sun stripes, retro-style, cut out of the lower half and sliding down
    p.append('  <g clip-path="url(#disc)">')
    for k in range(5):
        p.append(f'  <rect x="{sx - 72}" y="{sy + 8}" width="144" height="3" fill="#B87A48">'
                 f'<animate attributeName="y" from="{sy + 6}" to="{sy + 70}" dur="5s" begin="{-k}s" repeatCount="indefinite"/>'
                 f'<animate attributeName="height" from="1" to="9" dur="5s" begin="{-k}s" repeatCount="indefinite"/></rect>')
    p.append('  </g>')
    # parallax dune layers, each a 2-period strip sliding left by one period
    layers = [(238, 26, 3, "#C9955F", 90), (262, 30, 2, "#A56B3C", 60), (290, 34, 3, "#7A4A28", 42),
              (322, 28, 2, "#4E2F1A", 28), (352, 22, 3, "#2A190F", 18)]
    for base, amp, waves, col, dur in layers:
        ph = rnd.uniform(0, 6)
        pts = [(x, base - amp * (0.6 * math.sin(2 * math.pi * waves * x / W + ph)
                                 + 0.4 * math.sin(2 * math.pi * (waves * 2) * x / W + ph * 1.7)))
               for x in range(0, 2 * W + 1, 40)]
        d = smooth_path(pts) + f"L{2 * W} {H}L0 {H}Z"
        p.append(f'  <path d="{d}" fill="{col}"><animateTransform attributeName="transform" type="translate" '
                 f'from="0 0" to="{-W} 0" dur="{dur}s" repeatCount="indefinite"/></path>')
    # blowing sand
    for _ in range(50):
        y = rnd.uniform(240, H - 4)
        dur = rnd.uniform(3, 7)
        p.append(f'  <circle cx="{W + 10}" cy="{f(y)}" r="{rnd.choice([0.8, 1, 1.3])}" fill="{SAND}" opacity="{rnd.uniform(0.3, 0.8):.2f}">'
                 f'<animateTransform attributeName="transform" type="translate" values="0 0;{-W / 2} {-rnd.uniform(4, 20):.0f};{-W - 30} 0" '
                 f'dur="{dur:.1f}s" begin="{-rnd.uniform(0, dur):.1f}s" repeatCount="indefinite"/></circle>')
    p.append(f'  <rect width="{W}" height="{H}" fill="url(#grain)"/>\n</g>')
    p.append(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="19.5" fill="none" stroke="{GOLD}" stroke-opacity="0.22"/>')
    return svg(W, H, "\n".join(p), "dunes at dusk")


# ── 6. divider ───────────────────────────────────────────────────────────────

def divider():
    H = 36
    cy = H / 2
    return svg(W, H, f'''<defs>
  <linearGradient id="t" x1="0" x2="1"><stop offset="0" stop-color="{CINNAMON}" stop-opacity="0"/>
    <stop offset="0.5" stop-color="{GOLD}"/><stop offset="1" stop-color="{CINNAMON}" stop-opacity="0"/></linearGradient>
  <radialGradient id="g"><stop offset="0" stop-color="{IVORY}"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>
</defs>
<line x1="40" y1="{cy}" x2="{W - 40}" y2="{cy}" stroke="url(#t)" stroke-width="1"/>
<ellipse cy="{cy}" rx="60" ry="3" fill="url(#g)">
  <animate attributeName="cx" values="100;{W - 100};100" dur="7s" calcMode="spline" keySplines="0.5 0 0.5 1;0.5 0 0.5 1" repeatCount="indefinite"/>
</ellipse>
<path d="{star4(W / 2, cy, 8)}" fill="{LATTE}">{spin(W / 2, cy, 9)}</path>
<circle cx="{W / 2 - 22}" cy="{cy}" r="1.8" fill="{CARAMEL}"/><circle cx="{W / 2 + 22}" cy="{cy}" r="1.8" fill="{CARAMEL}"/>''',
               "")


def main():
    out = {
        "hero.svg": hero(),
        "silk.svg": silk(),
        "mandala.svg": mandala(),
        "globe.svg": globe(),
        "liquid.svg": liquid(),
        "ripple.svg": ripple(),
        "dunes.svg": dunes(),
        "divider.svg": divider(),
    }
    for name, body in out.items():
        with open(os.path.join(ASSETS, name), "w") as fh:
            fh.write(body)
        print(f"{name:12s} {len(body) / 1024:7.1f} KB")


if __name__ == "__main__":
    main()
