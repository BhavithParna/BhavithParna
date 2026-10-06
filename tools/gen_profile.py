#!/usr/bin/env python3
"""Render the GitHub profile as one animated SVG, in the portfolio's palette.

    python3 tools/gen_profile.py [out.svg]        # default: assets/profile.svg

Night sky from the portfolio's About page (navy → deep night, an ember glow of
dusk at the horizon, film grain), the Big Dipper drawing itself in the corner,
a shooting star now and then, the name set like the site's wordmark (Playfair
bold with a terracotta outline echo; an italic ember "parna"), and along the
bottom an automated iced-coffee station: a stepping conveyor, an espresso head
that pours into each cup as it stops underneath, a straw dropped in at the next
stop, and the cups rolling off the end. "Iced, always."

Rules (so it animates on GitHub): SMIL only — no CSS, no <script>, no web
fonts. Every piece of text is baked to outlines with fontTools, and the grain
is a tiny embedded PNG rather than a filter.
"""
import base64
import io
import math
import os
import random
import sys

import numpy as np
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
F_SERIF = os.path.join(FONTS, "PlayfairDisplay[wght].ttf")
F_SERIF_I = os.path.join(FONTS, "PlayfairDisplay-Italic[wght].ttf")
F_MONO = os.path.join(FONTS, "JetBrainsMono[wght].ttf")
F_HAND = os.path.join(FONTS, "Caveat[wght].ttf")

# ── palette: lifted from the portfolio's about.css ───────────────────────────
NIGHT = "#0e2238"
DEEP = "#060d18"
CREAM = "#f4ecd8"
CREAM2 = "#e9dfc9"
EMBER = "#e8763f"
TERRA = "#c1502e"
TEAL = "#3c7268"
INK = "#1d1712"
COFFEE = "#4a2a16"
COFFEE2 = "#8a5a34"
CREMA = "#c9a27a"

W, H = 1200, 760
SEED = 11

# conveyor timing
STOPS = 8            # cup stops across the belt
STEP = 2.0           # seconds per stop (dwell + move)
DWELL = 1.1
PERIOD = STOPS * STEP
X0, SPACING = -120, 200
BELT_Y = 648         # top of the belt
POUR_STOP = 5        # cup index under the spout
STRAW_STOP = 6


def f(x):
    s = f"{x:.1f}"
    return s[:-2] if s.endswith(".0") else s


# ── text → outlines ─────────────────────────────────────────────────────────
_cache = {}


def _font(path, wght):
    key = (path, wght)
    if key not in _cache:
        font = TTFont(path)
        if "fvar" in font and wght is not None:
            font = instancer.instantiateVariableFont(font, {"wght": wght})
        _cache[key] = font
    return _cache[key]


def text_paths(text, path, size, x, baseline, wght=None, align="left", tracking=0.0):
    """Outline `text`; returns (list of path d strings, total advance)."""
    font = _font(path, wght)
    gs, cmap = font.getGlyphSet(), font.getBestCmap()
    s = size / font["head"].unitsPerEm
    names = [cmap.get(ord(c)) or cmap.get(ord("?")) for c in text]
    adv = [font["hmtx"][g][0] * s + tracking * size for g in names]
    total = sum(adv) - tracking * size
    cx = x if align == "left" else x - total / 2 if align == "center" else x - total
    out = []
    for g, a in zip(names, adv):
        pen = SVGPathPen(gs, ntos=f)
        gs[g].draw(TransformPen(pen, (s, 0, 0, -s, cx, baseline)))
        if pen.getCommands():
            out.append(pen.getCommands())
        cx += a
    return out, total


def text(text_, path, size, x, baseline, fill, wght=None, align="left", tracking=0.0, opacity=None, extra=""):
    ds, _ = text_paths(text_, path, size, x, baseline, wght, align, tracking)
    op = f' opacity="{opacity}"' if opacity is not None else ""
    return f'<g fill="{fill}"{op}{extra}>' + "".join(f'<path d="{d}"/>' for d in ds) + "</g>"


# ── bits ─────────────────────────────────────────────────────────────────────
def grain_pattern(size=160, alpha=30):
    rng = np.random.default_rng(SEED)
    lum = rng.integers(0, 256, (size, size), dtype=np.uint8)
    a = (rng.random((size, size)) * alpha).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(np.dstack([lum, lum, lum, a]), "RGBA").save(buf, "PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return (f'<pattern id="grain" width="{size}" height="{size}" patternUnits="userSpaceOnUse">'
            f'<image width="{size}" height="{size}" href="data:image/png;base64,{b64}"/></pattern>')


def sky():
    out = [f'<rect width="{W}" height="{H}" fill="url(#sky)"/>',
           f'<rect width="{W}" height="{H}" fill="url(#dusk)"/>']
    rng = random.Random(SEED)
    for i in range(170):
        x, y = rng.uniform(0, W), rng.uniform(0, BELT_Y - 60)
        r = rng.choice([0.7, 0.9, 1.1, 1.4])
        o = rng.uniform(0.35, 0.9)
        if i % 4 == 0:
            d = rng.uniform(2.2, 5.5)
            out.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{r}" fill="{CREAM}" opacity="{f(o)}">'
                       f'<animate attributeName="opacity" values="{f(o)};{f(min(1, o + 0.5))};{f(o * 0.4)};{f(o)}" '
                       f'dur="{f(d)}s" begin="{f(-rng.uniform(0, d))}s" repeatCount="indefinite"/></circle>')
        else:
            out.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{r}" fill="{CREAM}" opacity="{f(o)}"/>')
    return "".join(out)


def dipper():
    """The Big Dipper, handle → bowl, the bowl closed back on Megrez. The line
    draws itself, holds, fades, and draws again. Positions mirror the site."""
    pts = [(7, 30), (21, 21), (34, 27), (47, 36), (51, 66), (74, 72), (72, 38), (47, 36)]
    ox, oy, sw, sh = 830, 70, 320, 170
    P = [(ox + x / 100 * sw, oy + y / 100 * sh) for x, y in pts]
    length = sum(math.dist(P[i], P[i + 1]) for i in range(len(P) - 1))
    poly = " ".join(f"{f(x)},{f(y)}" for x, y in P)
    out = [f'<polyline points="{poly}" fill="none" stroke="url(#line)" stroke-width="1.2" '
           f'stroke-dasharray="{f(length)}" stroke-dashoffset="{f(length)}" opacity="0.9">'
           f'<animate attributeName="stroke-dashoffset" values="{f(length)};0;0;0" keyTimes="0;0.45;0.8;1" '
           f'dur="14s" repeatCount="indefinite"/>'
           f'<animate attributeName="opacity" values="0.9;0.9;0.9;0" keyTimes="0;0.45;0.8;1" dur="14s" repeatCount="indefinite"/>'
           f'</polyline>']
    names = ["Alkaid", "Mizar", "Alioth", "Megrez", "Phecda", "Merak", "Dubhe"]
    for i, ((x, y), n) in enumerate(zip(P[:7], names)):
        at = 0.45 * (i / 6)
        out.append(f'<g><circle cx="{f(x)}" cy="{f(y)}" r="3.2" fill="{CREAM}">'
                   f'<animate attributeName="opacity" values="0.25;0.25;1;1;0.25" keyTimes="0;{f(at)};{f(min(0.79, at + 0.04))};0.8;1" dur="14s" repeatCount="indefinite"/></circle>'
                   f'<circle cx="{f(x)}" cy="{f(y)}" r="9" fill="url(#starglow)">'
                   f'<animate attributeName="opacity" values="0;0;0.9;0.9;0" keyTimes="0;{f(at)};{f(min(0.79, at + 0.04))};0.8;1" dur="14s" repeatCount="indefinite"/></circle></g>')
        out.append(text(n.upper(), F_MONO, 8, x, y - 11, CREAM2, wght=500, align="center", tracking=0.28, opacity=0.5))
    out.append(text("OFF THE CLOCK · URSA MAJOR", F_MONO, 9, ox + sw, oy + sh + 36, CREAM2, wght=500, align="right", tracking=0.22, opacity=0.5))
    return "".join(out)


def shooting_star():
    return (f'<g opacity="0"><animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.1;0.7;1" dur="1.1s" '
            f'begin="2.5s;shoot.end+8.5s" id="shoot"/>'
            f'<g transform="translate(520 60) rotate(28)"><line x1="0" y1="0" x2="190" y2="0" stroke="url(#streak)" stroke-width="1.6" stroke-linecap="round"/>'
            f'<circle r="2" fill="#fff"/></g>'
            f'<animateTransform attributeName="transform" type="translate" from="420 0" to="0 220" dur="1.1s" begin="shoot.begin" fill="freeze"/></g>')


def name():
    out = []
    # eyebrow
    out.append(text("BIOMEDICAL ENGINEER · HYDERABAD, IN", F_MONO, 11, 72, 166, CREAM2, wght=500, tracking=0.24, opacity=0.72,
                    extra='><animate attributeName="opacity" from="0" to="0.72" dur="0.9s" begin="1.1s" fill="freeze"/'))
    # BHAVITH: terracotta outline echo behind, cream letters rising out of a clip
    main, total = text_paths("BHAVITH", F_SERIF, 170, 72, 304, wght=700)
    echo, _ = text_paths("BHAVITH", F_SERIF, 170, 72 + 9, 304 + 8, wght=700)
    out.append('<g fill="none" stroke="' + TERRA + '" stroke-width="1.6" opacity="0">'
               + "".join(f'<path d="{d}"/>' for d in echo)
               + '<animate attributeName="opacity" from="0" to="0.6" dur="1s" begin="0.9s" fill="freeze"/></g>')
    out.append(f'<clipPath id="rowclip"><rect x="0" y="130" width="{W}" height="190"/></clipPath>')
    out.append('<g clip-path="url(#rowclip)" fill="' + CREAM + '">')
    for i, d in enumerate(main):
        out.append(f'<path d="{d}" transform="translate(0 200)"><animateTransform attributeName="transform" type="translate" '
                   f'from="0 200" to="0 0" dur="1.1s" begin="{f(0.15 + i * 0.07)}s" fill="freeze" calcMode="spline" keySplines="0.16 1 0.3 1"/></path>')
    out.append("</g>")
    # parna, italic ember with a teal echo, offset right like the site's "me"
    px = 72 + total * 0.52
    pm, _ = text_paths("parna", F_SERIF_I, 132, px, 418, wght=600)
    pe, _ = text_paths("parna", F_SERIF_I, 132, px - 8, 418 + 7, wght=600)
    out.append('<g fill="none" stroke="' + TEAL + '" stroke-width="1.6" opacity="0">'
               + "".join(f'<path d="{d}"/>' for d in pe)
               + '<animate attributeName="opacity" from="0" to="0.7" dur="1s" begin="1.2s" fill="freeze"/></g>')
    out.append(f'<clipPath id="rowclip2"><rect x="0" y="306" width="{W}" height="160"/></clipPath>')
    out.append('<g clip-path="url(#rowclip2)" fill="' + EMBER + '">')
    for i, d in enumerate(pm):
        out.append(f'<path d="{d}" transform="translate(0 170)"><animateTransform attributeName="transform" type="translate" '
                   f'from="0 170" to="0 0" dur="1.1s" begin="{f(0.6 + i * 0.06)}s" fill="freeze" calcMode="spline" keySplines="0.16 1 0.3 1"/></path>')
    out.append("</g>")
    # the hand note, like the site's margin notes
    out.append(text("builds things. anywhere from Lego to BCI drone controllers.", F_HAND, 26, 76, 472, CREAM2, wght=500, opacity=0.85,
                    extra='><animate attributeName="opacity" from="0" to="0.85" dur="0.9s" begin="1.6s" fill="freeze"/'))
    return "".join(out)


# ── the coffee station ──────────────────────────────────────────────────────
def stops_x(k):
    return X0 + k * SPACING


def cup(i):
    """One iced coffee riding the belt. Period PERIOD, offset so cup i is one
    stop behind cup i-1. Local origin: centre of the cup's base on the belt."""
    # staircase translate: dwell at each stop, then slide to the next
    vals, times = [], []
    for k in range(STOPS):
        t0 = k * STEP
        vals += [f"{stops_x(k)} 0", f"{stops_x(k)} 0"]
        times += [t0 / PERIOD, (t0 + DWELL) / PERIOD]
    vals.append(f"{stops_x(STOPS)} 0")
    times.append(1)
    kt = ";".join(f(t) for t in times)
    begin = f(-i * STEP)
    pour0 = (POUR_STOP * STEP + 0.2) / PERIOD
    pour1 = (POUR_STOP * STEP + 1.0) / PERIOD
    straw0 = (STRAW_STOP * STEP + 0.05) / PERIOD
    straw1 = (STRAW_STOP * STEP + 0.35) / PERIOD
    g = [f'<g transform="translate({stops_x(0)} 0)">'
         f'<animateTransform attributeName="transform" type="translate" values="{";".join(vals)}" keyTimes="{kt}" '
         f'calcMode="spline" keySplines="{";".join(["0.4 0 0.2 1"] * (len(vals) - 1))}" dur="{PERIOD}s" begin="{begin}s" repeatCount="indefinite"/>']
    # shadow on the belt
    g.append(f'<ellipse cx="0" cy="2" rx="30" ry="4" fill="#000" opacity="0.35"/>')
    # coffee fill (clipped to the glass), rising while under the spout
    g.append(f'<g clip-path="url(#cupclip)"><rect x="-32" y="0" width="64" height="70" fill="url(#coffee)">'
             f'<animate attributeName="y" values="0;0;-66;-66" keyTimes="0;{f(pour0)};{f(pour1)};1" dur="{PERIOD}s" begin="{begin}s" repeatCount="indefinite"/></rect>'
             f'<rect x="-32" y="0" width="64" height="6" fill="{CREMA}" opacity="0.8">'
             f'<animate attributeName="y" values="0;0;-66;-66" keyTimes="0;{f(pour0)};{f(pour1)};1" dur="{PERIOD}s" begin="{begin}s" repeatCount="indefinite"/></rect>'
             # ice, bobbing in once there's coffee to float in
             f'<g opacity="0"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;{f(pour0 + 0.015)};{f(pour0 + 0.03)};1" dur="{PERIOD}s" begin="{begin}s" repeatCount="indefinite"/>'
             f'<rect x="-18" y="-44" width="14" height="14" rx="3" fill="#fff" opacity="0.55" transform="rotate(-12 -11 -37)"/>'
             f'<rect x="4" y="-50" width="13" height="13" rx="3" fill="#fff" opacity="0.5" transform="rotate(18 10 -43)"/>'
             f'<rect x="-6" y="-30" width="12" height="12" rx="3" fill="#fff" opacity="0.45" transform="rotate(6 0 -24)"/></g></g>')
    # the glass
    g.append(f'<path d="M-28 -78 L-22 0 L22 0 L28 -78 Z" fill="{CREAM}" fill-opacity="0.07" stroke="{CREAM}" stroke-opacity="0.75" stroke-width="2"/>')
    g.append('<path d="M-28 -78 L-22 0 L22 0 L28 -78 Z" fill="url(#glass)"/>')
    g.append(f'<rect x="-32" y="-86" width="64" height="9" rx="3.5" fill="{CREAM}"/>')
    # straw, dropped in at the next stop
    g.append(f'<g opacity="0"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;{f(straw0)};{f(straw0 + 0.004)};1" dur="{PERIOD}s" begin="{begin}s" repeatCount="indefinite"/>'
             f'<rect x="4" y="-134" width="6" height="96" rx="3" fill="{EMBER}" transform="rotate(-8 7 -86)">'
             f'<animate attributeName="y" values="-200;-200;-134;-134" keyTimes="0;{f(straw0)};{f(straw1)};1" dur="{PERIOD}s" begin="{begin}s" repeatCount="indefinite" calcMode="spline" keySplines="0 0 1 1;0.5 0 0.3 1;0 0 1 1"/></rect></g>')
    # dew
    g.append(f'<circle cx="-16" cy="-30" r="1.6" fill="#fff" opacity="0.5"/><circle cx="18" cy="-50" r="1.3" fill="#fff" opacity="0.5"/>')
    g.append("</g>")
    return "".join(g)


def machine():
    sx = stops_x(POUR_STOP)  # spout x
    out = []
    # gantry frame straddling the belt
    out.append(f'<rect x="{sx - 110}" y="{BELT_Y - 210}" width="220" height="120" rx="14" fill="{CREAM}"/>')
    out.append(f'<rect x="{sx - 110}" y="{BELT_Y - 210}" width="220" height="120" rx="14" fill="url(#brushed)"/>')
    out.append(f'<rect x="{sx - 110}" y="{BELT_Y - 210}" width="220" height="18" rx="9" fill="{TERRA}"/>')
    out.append(f'<rect x="{sx - 96}" y="{BELT_Y - 182}" width="192" height="40" rx="6" fill="{INK}"/>')
    # display: NIGHT FUEL · LIVE + a blinking LED
    out.append(text("NIGHT FUEL · LIVE", F_MONO, 10, sx - 84, BELT_Y - 158, CREAM2, wght=500, tracking=0.22, opacity=0.8))
    out.append(f'<circle cx="{sx + 80}" cy="{BELT_Y - 163}" r="4" fill="{EMBER}"><animate attributeName="opacity" values="1;0.2;1" dur="1.2s" repeatCount="indefinite"/></circle>')
    # VU bars that pump while pouring (2s cycle)
    for k in range(9):
        bx = sx - 84 + k * 10
        out.append(f'<rect x="{bx}" y="{BELT_Y - 154}" width="6" height="8" rx="1" fill="{EMBER}" opacity="0.25">'
                   f'<animate attributeName="opacity" values="0.25;0.25;1;1;0.25;0.25" keyTimes="0;{f(0.08 + k * 0.05)};{f(0.1 + k * 0.05)};0.5;0.56;1" dur="{STEP}s" repeatCount="indefinite"/></rect>')
    # gauge with a needle that swings on each pour
    gx, gy = sx + 62, BELT_Y - 116
    out.append(f'<circle cx="{gx}" cy="{gy}" r="16" fill="{CREAM2}" stroke="{INK}" stroke-width="2"/>')
    out.append(f'<path d="M{gx - 11} {gy + 3} A11 11 0 0 1 {gx + 11} {gy + 3}" fill="none" stroke="{TERRA}" stroke-width="2"/>')
    out.append(f'<line x1="{gx}" y1="{gy}" x2="{gx}" y2="{gy - 12}" stroke="{INK}" stroke-width="2" stroke-linecap="round" transform="rotate(-60 {gx} {gy})">'
               f'<animateTransform attributeName="transform" type="rotate" values="-60 {gx} {gy};-60 {gx} {gy};55 {gx} {gy};50 {gx} {gy};-60 {gx} {gy};-60 {gx} {gy}" '
               f'keyTimes="0;0.05;0.2;0.5;0.62;1" dur="{STEP}s" repeatCount="indefinite"/></line>')
    # knobs
    for kx in (sx - 70, sx - 40):
        out.append(f'<circle cx="{kx}" cy="{BELT_Y - 116}" r="9" fill="{TERRA}"/><circle cx="{kx}" cy="{BELT_Y - 116}" r="3" fill="{CREAM}"/>')
    # group head + portafilter; it dips when it pours
    out.append(f'<g><animateTransform attributeName="transform" type="translate" values="0 0;0 6;0 6;0 0;0 0" keyTimes="0;0.08;0.5;0.58;1" dur="{STEP}s" repeatCount="indefinite"/>'
               f'<rect x="{sx - 30}" y="{BELT_Y - 100}" width="60" height="22" rx="4" fill="{INK}"/>'
               f'<rect x="{sx - 44}" y="{BELT_Y - 86}" width="88" height="10" rx="5" fill="#3a2a20"/>'
               f'<rect x="{sx + 40}" y="{BELT_Y - 84}" width="46" height="6" rx="3" fill="{INK}"/>'
               f'<rect x="{sx - 6}" y="{BELT_Y - 78}" width="12" height="10" rx="2" fill="{INK}"/></g>')
    # the pour: a stream that appears during the dwell, with a splash ring
    top = BELT_Y - 68
    out.append(f'<rect x="{sx - 2.5}" y="{top}" width="5" rx="2.5" fill="url(#stream)" height="0">'
               f'<animate attributeName="height" values="0;0;70;70;0;0" keyTimes="0;0.08;0.14;0.5;0.56;1" dur="{STEP}s" repeatCount="indefinite"/></rect>')
    out.append(f'<ellipse cx="{sx}" cy="{BELT_Y - 10}" rx="10" ry="3" fill="none" stroke="{CREMA}" stroke-width="1.5" opacity="0">'
               f'<animate attributeName="opacity" values="0;0;0.8;0.8;0;0" keyTimes="0;0.13;0.16;0.5;0.56;1" dur="{STEP}s" repeatCount="indefinite"/>'
               f'<animate attributeName="rx" values="4;4;6;14;16;4" keyTimes="0;0.13;0.16;0.5;0.56;1" dur="{STEP}s" repeatCount="indefinite"/></ellipse>')
    # legs
    for lx in (sx - 100, sx + 92):
        out.append(f'<rect x="{lx}" y="{BELT_Y - 92}" width="8" height="{92 + 30}" fill="{INK}"/>')
    # straw dispenser at the next stop: a little arm that dips
    ax = stops_x(STRAW_STOP)
    out.append(f'<rect x="{ax - 4}" y="{BELT_Y - 210}" width="8" height="60" fill="{INK}"/>')
    out.append(f'<g><animateTransform attributeName="transform" type="translate" values="0 0;0 0;0 26;0 26;0 0;0 0" keyTimes="0;0.02;0.14;0.3;0.42;1" dur="{STEP}s" begin="{f(-STEP * STRAW_STOP)}s" repeatCount="indefinite"/>'
               f'<rect x="{ax - 22}" y="{BELT_Y - 150}" width="44" height="14" rx="4" fill="{TERRA}"/>'
               f'<rect x="{ax - 3}" y="{BELT_Y - 136}" width="6" height="10" fill="{INK}"/></g>')
    out.append(text("STRAWS", F_MONO, 7, ax, BELT_Y - 156, CREAM2, wght=500, align="center", tracking=0.3, opacity=0.6))
    return "".join(out)


def belt():
    out = []
    # floor + shadow
    out.append(f'<rect x="0" y="{BELT_Y + 26}" width="{W}" height="{H - BELT_Y - 26}" fill="{DEEP}" opacity="0.6"/>')
    out.append(f'<rect x="0" y="{BELT_Y + 26}" width="{W}" height="18" fill="url(#beltshadow)"/>')
    # belt body
    out.append(f'<rect x="-40" y="{BELT_Y}" width="{W + 80}" height="26" rx="13" fill="#1a130e" stroke="#3a2a20" stroke-width="2"/>')
    # the tread: dashes that advance exactly one stop during each move
    dashes = []
    for k in range(STOPS):
        t0 = k * STEP
        dashes.append((t0 / PERIOD, -k * SPACING))
        dashes.append(((t0 + DWELL) / PERIOD, -k * SPACING))
    dashes.append((1, -STOPS * SPACING))
    out.append(f'<line x1="-40" y1="{BELT_Y + 13}" x2="{W + 40}" y2="{BELT_Y + 13}" stroke="{CREAM}" stroke-opacity="0.22" stroke-width="3" stroke-dasharray="26 14">'
               f'<animate attributeName="stroke-dashoffset" values="{";".join(f(d) for _, d in dashes)}" keyTimes="{";".join(f(t) for t, _ in dashes)}" '
               f'calcMode="spline" keySplines="{";".join(["0.4 0 0.2 1"] * (len(dashes) - 1))}" dur="{PERIOD}s" repeatCount="indefinite"/></line>')
    # rollers at each end, spoked, turning with the belt
    for rx in (26, W - 26):
        spokes = "".join(f'<line x1="{rx}" y1="{BELT_Y + 13}" x2="{f(rx + 9 * math.cos(a))}" y2="{f(BELT_Y + 13 + 9 * math.sin(a))}" stroke="{CREAM}" stroke-opacity="0.5" stroke-width="1.5"/>'
                         for a in (0, math.pi / 2, math.pi, 3 * math.pi / 2))
        rot = []
        for k in range(STOPS):
            t0 = k * STEP
            rot.append((t0 / PERIOD, k * 180))
            rot.append(((t0 + DWELL) / PERIOD, k * 180))
        rot.append((1, STOPS * 180))
        out.append(f'<g><circle cx="{rx}" cy="{BELT_Y + 13}" r="12" fill="#2a1f18" stroke="{CREAM}" stroke-opacity="0.4" stroke-width="2"/>{spokes}'
                   f'<animateTransform attributeName="transform" type="rotate" values="{";".join(f"{a} {rx} {BELT_Y + 13}" for _, a in rot)}" '
                   f'keyTimes="{";".join(f(t) for t, _ in rot)}" calcMode="spline" keySplines="{";".join(["0.4 0 0.2 1"] * (len(rot) - 1))}" dur="{PERIOD}s" repeatCount="indefinite"/></g>')
    return "".join(out)


def caption():
    return (text("iced, always. № 4 is on the belt.", F_HAND, 24, W - 72, BELT_Y - 240, CREAM2, wght=500, align="right", opacity=0.85)
            + text("ONE CUP EVERY 2S · NO HUMANS INVOLVED", F_MONO, 9, W - 72, BELT_Y - 222, CREAM2, wght=500, align="right", tracking=0.22, opacity=0.5))


def defs():
    return (
        "<defs>"
        f'<linearGradient id="sky" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="{DEEP}"/><stop offset="0.55" stop-color="{NIGHT}"/><stop offset="1" stop-color="#2a1d2b"/></linearGradient>'
        f'<radialGradient id="dusk" cx="0.5" cy="1.05" r="0.9"><stop offset="0" stop-color="#d86034" stop-opacity="0.55"/><stop offset="0.45" stop-color="#d86034" stop-opacity="0.12"/><stop offset="1" stop-color="#d86034" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="starglow"><stop offset="0" stop-color="{CREAM}" stop-opacity="0.8"/><stop offset="1" stop-color="{EMBER}" stop-opacity="0"/></radialGradient>'
        f'<linearGradient id="line" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="{CREAM}" stop-opacity="0.5"/><stop offset="1" stop-color="{EMBER}" stop-opacity="0.9"/></linearGradient>'
        f'<linearGradient id="streak" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="{CREAM}" stop-opacity="0"/><stop offset="1" stop-color="#ffffff"/></linearGradient>'
        f'<linearGradient id="coffee" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="{CREMA}"/><stop offset="0.3" stop-color="{COFFEE2}"/><stop offset="1" stop-color="{COFFEE}"/></linearGradient>'
        f'<linearGradient id="glass" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0.32"/><stop offset="0.45" stop-color="#fff" stop-opacity="0.03"/><stop offset="1" stop-color="#fff" stop-opacity="0.2"/></linearGradient>'
        f'<linearGradient id="stream" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="{COFFEE}"/><stop offset="1" stop-color="{COFFEE2}"/></linearGradient>'
        f'<linearGradient id="brushed" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0.35"/><stop offset="0.3" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.18"/></linearGradient>'
        f'<linearGradient id="beltshadow" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#000" stop-opacity="0.6"/><stop offset="1" stop-color="#000" stop-opacity="0"/></linearGradient>'
        '<clipPath id="cupclip"><path d="M-27 -77 L-21 -1 L21 -1 L27 -77 Z"/></clipPath>'
        + grain_pattern() +
        "</defs>"
    )


def render():
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Bhavith Parna">',
             defs(), sky(), dipper(), shooting_star(), name(), caption(), belt()]
    # cups behind the machine's legs but in front of the belt body
    parts.append(f'<g transform="translate(0 {BELT_Y})">' + "".join(cup(i) for i in range(STOPS)) + "</g>")
    parts.append(machine())
    parts.append(f'<rect width="{W}" height="{H}" fill="url(#grain)" opacity="0.5"/>')
    parts.append("</svg>")
    return "".join(parts)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "assets", "profile.svg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    svg = render()
    with open(out, "w") as fh:
        fh.write(svg)
    print(f"wrote {out} ({len(svg) // 1024} KB)")
