#!/usr/bin/env python3
"""Render the profile as one continuous space scene.

Top: the name card. Middle: the last year of GitHub contributions wound into a
spiral galaxy, one star per day, with the calendar's seven weekday rows running
across the arm. A comet traces the year from the core outwards and lights each day
as it passes. Bottom: the limb of a planet, with the year's total written on it.

    python3 tools/gen_space.py [out.svg]        # default: assets/space.svg

Needs a token for the contribution calendar: GH_TOKEN / GITHUB_TOKEN, or a logged-in
`gh` CLI. The GitHub Action runs this daily and publishes to the `output` branch.

Animation is SMIL only (no CSS, no <script>) so it survives GitHub's image proxy.
"""
import base64
import io
import json
import math
import os
import random
import subprocess
import sys
import urllib.request

import numpy as np
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "InstrumentSerif-Italic.ttf")
USER = os.environ.get("GITHUB_REPOSITORY_OWNER", "BhavithParna")
NAME = "Bhavith Parna"

ESPRESSO = "#140D08"
ROAST    = "#22160E"
WALNUT   = "#5C3D26"
CINNAMON = "#8B5A2B"
CARAMEL  = "#C08552"
GOLD     = "#D4A373"
LATTE    = "#DDB892"
SAND     = "#E6CCB2"
CREAM    = "#F5EBE0"
IVORY    = "#FFF8EE"

W, H = 1200, 1260
NAME_Y = 250                       # centre line of the name
GX, GY = 600, 735                  # galaxy centre (screen)
TILT = 0.46                        # y-squash of the galaxy disc
PLANET_R = 1850
PLANET_CY = H - 195 + PLANET_R     # limb crest sits 195px above the bottom
LOOP = 12                          # seconds per comet pass


# ── helpers ──────────────────────────────────────────────────────────────────

def f(x):
    s = f"{x:.1f}"
    return s[:-2] if s.endswith(".0") else s


def smooth_path(pts):
    """Catmull-Rom through pts, emitted as cubic Béziers."""
    n = len(pts)
    get = lambda i: pts[min(max(i, 0), n - 1)]
    d = f"M{f(pts[0][0])} {f(pts[0][1])}"
    for i in range(n - 1):
        p0, p1, p2, p3 = get(i - 1), get(i), get(i + 1), get(i + 2)
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f"C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(p2[0])} {f(p2[1])}"
    return d


def grain_pattern(size=160, alpha=34, seed=7):
    """Tiling film-grain PNG; feTurbulence would be recomputed every frame."""
    rng = np.random.default_rng(seed)
    lum = rng.integers(0, 256, (size, size), dtype=np.uint8)
    a = (rng.random((size, size)) * alpha).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(np.dstack([lum, lum, lum, a]), "RGBA").save(buf, "PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return (f'<pattern id="grain" width="{size}" height="{size}" patternUnits="userSpaceOnUse">'
            f'<image width="{size}" height="{size}" href="data:image/png;base64,{b64}"/></pattern>')


def spin(cx, cy, dur, reverse=False):
    a, b = (360, 0) if reverse else (0, 360)
    return (f'<animateTransform attributeName="transform" type="rotate" from="{a} {cx} {cy}" '
            f'to="{b} {cx} {cy}" dur="{dur}s" repeatCount="indefinite"/>')


def star4(cx, cy, r):
    k = r * 0.18
    return (f"M{f(cx)} {f(cy - r)}Q{f(cx + k)} {f(cy - k)} {f(cx + r)} {f(cy)}"
            f"Q{f(cx + k)} {f(cy + k)} {f(cx)} {f(cy + r)}"
            f"Q{f(cx - k)} {f(cy + k)} {f(cx - r)} {f(cy)}"
            f"Q{f(cx - k)} {f(cy - k)} {f(cx)} {f(cy - r)}Z")


def glyphs(text, size, cx, baseline):
    """Outline each character of text, run centred on cx. Returns [path_d]."""
    font = TTFont(FONT)
    gs, cmap = font.getGlyphSet(), font.getBestCmap()
    s = size / font["head"].unitsPerEm
    names = [cmap.get(ord(c), cmap[ord("-")]) for c in text]
    adv = [font["hmtx"][g][0] * s for g in names]
    x = cx - sum(adv) / 2
    out = []
    for g, a in zip(names, adv):
        pen = SVGPathPen(gs, ntos=f)
        gs[g].draw(TransformPen(pen, (s, 0, 0, -s, x, baseline)))
        if pen.getCommands():
            out.append(pen.getCommands())
        x += a
    return out


# ── data ─────────────────────────────────────────────────────────────────────

QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{date contributionCount contributionLevel weekday}}}}}}"""


def calendar():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
            headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"})
        data = json.load(urllib.request.urlopen(req))
    else:
        data = json.loads(subprocess.check_output(
            ["gh", "api", "graphql", "-f", f"query={QUERY}", "-f", f"login={USER}"]))
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


# ── scene ────────────────────────────────────────────────────────────────────

def arm_point(t, offset=0.0, phase=0.0):
    """Point on the spiral arm in the galaxy plane. t in [0,1] is time through the
    year; r and theta both grow with sqrt(t), which keeps weeks evenly spaced."""
    s = math.sqrt(t)
    r = 46 + 450 * s + offset
    th = -1.2 + 8.6 * s + phase
    return r * math.cos(th), r * math.sin(th)


def level_of(day):
    return ["NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE",
            "FOURTH_QUARTILE"].index(day["contributionLevel"])


def build(cal):
    rnd = random.Random(11)
    weeks = cal["weeks"]
    nw = len(weeks)
    p = []

    # defs
    blobs = [(CARAMEL, 0.55, 340), (CINNAMON, 0.6, 380), (GOLD, 0.32, 260),
             (WALNUT, 0.7, 420), ("#C9957A", 0.28, 300), (LATTE, 0.18, 240)]
    p.append(f'''<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{ESPRESSO}"/><stop offset="0.3" stop-color="{ROAST}"/>
    <stop offset="0.7" stop-color="#1A100A"/><stop offset="1" stop-color="{ESPRESSO}"/>
  </linearGradient>''')
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
    <stop offset="0.62" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.45"/>
  </radialGradient>
  <radialGradient id="dot"><stop offset="0" stop-color="{IVORY}"/><stop offset="0.35" stop-color="{LATTE}" stop-opacity="0.8"/>
    <stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>
  <radialGradient id="halo"><stop offset="0" stop-color="{IVORY}" stop-opacity="0.9"/>
    <stop offset="0.25" stop-color="{LATTE}" stop-opacity="0.35"/><stop offset="1" stop-color="{CARAMEL}" stop-opacity="0"/></radialGradient>
  <radialGradient id="core"><stop offset="0" stop-color="{IVORY}" stop-opacity="0.95"/>
    <stop offset="0.18" stop-color="{LATTE}" stop-opacity="0.6"/><stop offset="0.5" stop-color="{CARAMEL}" stop-opacity="0.18"/>
    <stop offset="1" stop-color="{CINNAMON}" stop-opacity="0"/></radialGradient>
  <radialGradient id="neb"><stop offset="0" stop-color="{CARAMEL}" stop-opacity="0.32"/>
    <stop offset="0.5" stop-color="{CINNAMON}" stop-opacity="0.12"/><stop offset="1" stop-color="{CINNAMON}" stop-opacity="0"/></radialGradient>
  <radialGradient id="disc"><stop offset="0" stop-color="{CARAMEL}" stop-opacity="0.22"/>
    <stop offset="0.7" stop-color="{CINNAMON}" stop-opacity="0.07"/><stop offset="1" stop-color="{CINNAMON}" stop-opacity="0"/></radialGradient>
  <radialGradient id="atmo" gradientUnits="userSpaceOnUse" cx="{GX}" cy="{PLANET_CY}" r="{PLANET_R + 70}">
    <stop offset="{PLANET_R / (PLANET_R + 70):.4f}" stop-color="{CARAMEL}" stop-opacity="0.55"/>
    <stop offset="{(PLANET_R + 14) / (PLANET_R + 70):.4f}" stop-color="{CARAMEL}" stop-opacity="0.22"/>
    <stop offset="1" stop-color="{CARAMEL}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="ground" gradientUnits="userSpaceOnUse" cx="{GX}" cy="{PLANET_CY - PLANET_R}" r="700">
    <stop offset="0" stop-color="#3A2616"/><stop offset="1" stop-color="#110A06"/>
  </radialGradient>
  <radialGradient id="flare"><stop offset="0" stop-color="{IVORY}" stop-opacity="0.9"/>
    <stop offset="0.3" stop-color="{LATTE}" stop-opacity="0.4"/><stop offset="1" stop-color="{CARAMEL}" stop-opacity="0"/></radialGradient>
  <filter id="soft" x="-20%" y="-40%" width="140%" height="180%"><feGaussianBlur stdDeviation="10"/></filter>
  {grain_pattern()}
  <clipPath id="card"><rect width="{W}" height="{H}" rx="20"/></clipPath>
  <clipPath id="planet"><circle cx="{GX}" cy="{PLANET_CY}" r="{PLANET_R}"/></clipPath>
</defs>
<rect width="{W}" height="{H}" rx="20" fill="url(#bg)"/>
<g clip-path="url(#card)">''')

    # colour fields: the warm ones stay around the name, two dim ones cradle the galaxy
    for i, (_, _, r) in enumerate(blobs):
        lo, hi = (40, 560) if i < 4 else (620, 1000)
        pts = [(rnd.uniform(80, W - 80), rnd.uniform(lo, hi)) for _ in range(4)]
        pts.append(pts[0])
        vals = ";".join(f"{f(x)} {f(y)}" for x, y in pts)
        p.append(f'  <circle r="{r}" fill="url(#b{i})"><animateTransform attributeName="transform" '
                 f'type="translate" values="{vals}" dur="{rnd.uniform(18, 30):.1f}s" calcMode="spline" '
                 f'keySplines="{";".join(["0.45 0 0.55 1"] * 4)}" repeatCount="indefinite"/></circle>')

    # fixed background stars
    for _ in range(170):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H - 200)
        r = rnd.choice([0.5, 0.7, 0.7, 0.9, 1.2])
        if rnd.random() < 0.35:
            dur = rnd.uniform(2.5, 6)
            anim = (f'<animate attributeName="opacity" values="0.15;0.9;0.15" dur="{dur:.1f}s" '
                    f'begin="{-rnd.uniform(0, dur):.1f}s" repeatCount="indefinite"/>')
            p.append(f'  <circle cx="{f(x)}" cy="{f(y)}" r="{r}" fill="{CREAM}">{anim}</circle>')
        else:
            p.append(f'  <circle cx="{f(x)}" cy="{f(y)}" r="{r}" fill="{SAND}" opacity="{rnd.uniform(0.15, 0.5):.2f}"/>')

    # rings and orbit around the name
    cx = W / 2
    for k, r in enumerate(range(150, 420, 34)):
        dash = ["", ' stroke-dasharray="2 10"', ' stroke-dasharray="40 14 4 14"', ' stroke-dasharray="1 5"'][k % 4]
        op = 0.05 + 0.07 * (k % 3 == 0)
        p.append(f'  <circle cx="{cx}" cy="{NAME_Y}" r="{r}" fill="none" stroke="{SAND}" stroke-opacity="{op:.2f}" '
                 f'stroke-width="1"{dash}>{spin(cx, NAME_Y, 90 + k * 17, reverse=k % 2)}</circle>')
    orbit = f"M{cx - 470} {NAME_Y}A470 110 0 1 1 {cx + 470} {NAME_Y}A470 110 0 1 1 {cx - 470} {NAME_Y}"
    p.append(f'''  <g transform="rotate(-9 {cx} {NAME_Y})">
    <path d="{orbit}" fill="none" stroke="{LATTE}" stroke-opacity="0.22" stroke-width="1"/>
    <circle r="16" fill="url(#dot)"><animateMotion dur="14s" repeatCount="indefinite" path="{orbit}"/></circle>
    <circle r="9" fill="url(#dot)" opacity="0.7"><animateMotion dur="14s" begin="-7s" repeatCount="indefinite" path="{orbit}"/></circle>
  </g>''')

    # ── the galaxy ──
    p.append(f'  <ellipse cx="{GX}" cy="{GY}" rx="560" ry="{560 * TILT:.0f}" fill="url(#disc)"/>')
    p.append(f'  <g transform="translate({GX} {GY}) scale(1 {TILT})"><g>')
    p.append(f'    {spin(0, 0, 240)}')

    # nebula: soft overlapping glows along both arms
    for arm in (0, math.pi):
        for k in range(70):
            t = (k + rnd.random()) / 70
            x, y = arm_point(t, rnd.gauss(0, 14), arm)
            p.append(f'    <circle cx="{f(x)}" cy="{f(y)}" r="{f(34 + 70 * t * rnd.uniform(0.6, 1.2))}" '
                     f'fill="url(#neb)" opacity="{rnd.uniform(0.35, 0.7):.2f}"/>')
    # a second, data-free arm and loose disc dust, for the galaxy's shape
    for _ in range(700):
        t = rnd.random() ** 1.3
        x, y = arm_point(t, rnd.gauss(0, 10 + 26 * t), math.pi + rnd.gauss(0, 0.08))
        p.append(f'    <circle cx="{f(x)}" cy="{f(y)}" r="{rnd.choice([1.2, 1.6, 2, 2.6])}" '
                 f'fill="{rnd.choice([SAND, LATTE, GOLD, CREAM])}" opacity="{rnd.uniform(0.3, 0.85):.2f}"/>')
    for _ in range(360):
        a, rr = rnd.uniform(0, 2 * math.pi), 40 + 480 * rnd.random() ** 0.7
        p.append(f'    <circle cx="{f(rr * math.cos(a))}" cy="{f(rr * math.sin(a))}" r="{rnd.choice([1, 1.4, 1.8])}" '
                 f'fill="{SAND}" opacity="{rnd.uniform(0.15, 0.45):.2f}"/>')

    # the year: one star per day, weeks along the arm, weekdays across it
    today = None
    centre = []
    for w, week in enumerate(weeks):
        t = w / (nw - 1)
        centre.append(arm_point(t))
        band = 8 + 14 * t
        for day in week["contributionDays"]:
            lv = level_of(day)
            x, y = arm_point(t, (day["weekday"] - 3) * band, (day["weekday"] - 3) * 0.004)
            today = (x, y, lv)
            if lv == 0:
                p.append(f'    <circle cx="{f(x)}" cy="{f(y)}" r="2.3" fill="{SAND}" opacity="0.32"/>')
                continue
            rb = [0, 3, 4.2, 5.4, 6.8][lv]
            col = [None, CARAMEL, GOLD, LATTE, IVORY][lv]
            k0 = 0.02 + 0.6 * t                  # when the comet reaches this week
            k1, k2 = k0 + 0.02, min(k0 + 0.14, 0.99)
            kt = f"0;{k0:.3f};{k1:.3f};{k2:.3f};1"
            if lv >= 2:
                hr = rb * 4.2
                p.append(f'    <circle cx="{f(x)}" cy="{f(y)}" r="{f(hr)}" fill="url(#halo)" opacity="0.55">'
                         f'<animate attributeName="r" values="{f(hr)};{f(hr)};{f(hr * 2.2)};{f(hr)};{f(hr)}" '
                         f'keyTimes="{kt}" dur="{LOOP}s" repeatCount="indefinite"/></circle>')
            p.append(f'    <circle cx="{f(x)}" cy="{f(y)}" r="{rb}" fill="{col}">'
                     f'<animate attributeName="r" values="{rb};{rb};{f(rb * 1.9)};{rb};{rb}" keyTimes="{kt}" '
                     f'dur="{LOOP}s" repeatCount="indefinite"/></circle>')

    # today: a beacon at the tip of the arm
    tx, ty, _ = today
    for k in range(3):
        p.append(f'    <circle cx="{f(tx)}" cy="{f(ty)}" r="4" fill="none" stroke="{CREAM}" stroke-width="1.4">'
                 f'<animate attributeName="r" from="6" to="60" dur="3.6s" begin="{-1.2 * k}s" repeatCount="indefinite"/>'
                 f'<animate attributeName="stroke-opacity" from="0.8" to="0" dur="3.6s" begin="{-1.2 * k}s" repeatCount="indefinite"/></circle>')
    p.append(f'    <circle cx="{f(tx)}" cy="{f(ty)}" r="5.5" fill="{IVORY}"/>')

    # the comet: rides the arm from the oldest week to today, then rests
    track = smooth_path(centre)
    move = f'keyPoints="0;1;1" keyTimes="0;0.62;1" calcMode="linear" dur="{LOOP}s" repeatCount="indefinite"'
    fade = f'values="0;1;1;0;0" keyTimes="0;0.04;0.6;0.66;1" dur="{LOOP}s" repeatCount="indefinite"'
    p.append(f'    <path d="{track}" fill="none" stroke="{LATTE}" stroke-opacity="0.12" stroke-width="1.2"/>')
    for r, lag in [(44, 0), (20, 0), (12, 0.12), (7, 0.24)]:
        p.append(f'    <circle r="{r}" fill="url(#halo)" opacity="0"><animateMotion path="{track}" '
                 f'begin="{-lag:.2f}s" {move}/><animate attributeName="opacity" begin="{-lag:.2f}s" {fade}/></circle>')
    p.append('  </g></g>')

    # the core sits in screen space so it stays round-ish
    p.append(f'''  <ellipse cx="{GX}" cy="{GY}" rx="190" ry="96" fill="url(#core)">
    <animate attributeName="rx" values="180;205;180" dur="6s" repeatCount="indefinite"/>
    <animate attributeName="ry" values="90;104;90" dur="6s" repeatCount="indefinite"/>
  </ellipse>
  <path d="{star4(GX, GY, 16)}" fill="{IVORY}">{spin(GX, GY, 14)}</path>''')

    # rising dust over the whole scene
    for _ in range(110):
        x = rnd.uniform(0, W)
        dur = rnd.uniform(14, 34)
        op = rnd.uniform(0.3, 0.9)
        p.append(f'  <circle cx="{f(x)}" cy="{H - 190}" r="{rnd.choice([0.8, 1, 1.2, 1.6, 2.2])}" '
                 f'fill="{rnd.choice([CREAM, SAND, LATTE, GOLD])}">'
                 f'<animateTransform attributeName="transform" type="translate" from="0 0" '
                 f'to="{f(rnd.uniform(-60, 60))} {-H + 150}" dur="{dur:.1f}s" begin="{-rnd.uniform(0, dur):.1f}s" repeatCount="indefinite"/>'
                 f'<animate attributeName="opacity" values="0;{op:.2f};{op * 0.4:.2f};{op:.2f};0" dur="{dur:.1f}s" '
                 f'begin="{-rnd.uniform(0, dur):.1f}s" repeatCount="indefinite"/></circle>')

    # sparkles
    for x, y, r, b in [(212, 118, 11, 0), (1010, 96, 8, 1.3), (960, 404, 12, 2.1), (240, 392, 7, 3.2),
                       (120, 250, 5, 0.7), (1085, 250, 6, 2.6), (600, 64, 7, 1.9),
                       (140, 620, 8, 1.1), (1080, 980, 9, 2.8), (1050, 640, 6, 0.4), (170, 960, 7, 3.6)]:
        p.append(f'  <path d="{star4(x, y, r)}" fill="{IVORY}" opacity="0">'
                 f'<animate attributeName="opacity" values="0;1;0" dur="3.6s" begin="{b + 1.5}s" repeatCount="indefinite"/>'
                 f'{spin(x, y, 7)}</path>')

    # ── the name ──
    gl = glyphs(NAME, 158, cx, NAME_Y + 46)
    p.append(f'  <path d="{"".join(gl)}" fill="{GOLD}" opacity="0" filter="url(#soft)">'
             f'<animate attributeName="opacity" values="0;0.55;0.3;0.55" keyTimes="0;0.2;0.6;1" dur="6s" begin="2.4s" '
             f'repeatCount="indefinite"/></path>')
    for i, d in enumerate(gl):
        b = 0.25 + i * 0.13
        p.append(f'  <path d="{d}" pathLength="1" fill="url(#shine)" fill-opacity="0" stroke="{SAND}" '
                 f'stroke-width="1.4" stroke-dasharray="1" stroke-dashoffset="1">'
                 f'<animate attributeName="stroke-dashoffset" from="1" to="0" dur="1.8s" begin="{b:.2f}s" '
                 f'calcMode="spline" keySplines="0.6 0 0.3 1" keyTimes="0;1" fill="freeze"/>'
                 f'<animate attributeName="fill-opacity" from="0" to="1" dur="1.1s" begin="{b + 1.3:.2f}s" fill="freeze"/>'
                 f'<animate attributeName="stroke-opacity" from="1" to="0.25" dur="1.1s" begin="{b + 1.5:.2f}s" fill="freeze"/>'
                 f'</path>')
    ry = NAME_Y + 96
    p.append(f'''  <line x1="{cx}" y1="{ry}" x2="{cx}" y2="{ry}" stroke="url(#rule)" stroke-width="1.4">
    <animate attributeName="x1" to="{cx - 300}" dur="1.4s" begin="2.6s" calcMode="spline" keySplines="0.2 0 0.2 1" keyTimes="0;1" fill="freeze"/>
    <animate attributeName="x2" to="{cx + 300}" dur="1.4s" begin="2.6s" calcMode="spline" keySplines="0.2 0 0.2 1" keyTimes="0;1" fill="freeze"/>
  </line>
  <g opacity="0"><animate attributeName="opacity" to="1" dur="0.8s" begin="3.4s" fill="freeze"/>
    <path d="{star4(cx, ry, 9)}" fill="{CREAM}">{spin(cx, ry, 12)}</path>
    <circle cx="{cx - 310}" cy="{ry}" r="2.4" fill="{LATTE}"/><circle cx="{cx + 310}" cy="{ry}" r="2.4" fill="{LATTE}"/>
  </g>''')

    # ── the planet ──
    top = PLANET_CY - PLANET_R
    p.append(f'''  <circle cx="{GX}" cy="{PLANET_CY}" r="{PLANET_R + 70}" fill="url(#atmo)">
    <animate attributeName="r" values="{PLANET_R + 62};{PLANET_R + 80};{PLANET_R + 62}" dur="8s" repeatCount="indefinite"/>
  </circle>
  <circle cx="{GX}" cy="{PLANET_CY}" r="{PLANET_R}" fill="url(#ground)"/>
  <g clip-path="url(#planet)" fill="none" stroke="{GOLD}">''')
    for k, dy in enumerate([34, 80, 140]):
        p.append(f'    <ellipse cx="{GX}" cy="{top + dy + 900}" rx="{1500 - k * 80}" ry="900" stroke-opacity="{0.12 - k * 0.03:.2f}"/>')
    p.append(f'''  </g>
  <circle cx="{GX}" cy="{PLANET_CY}" r="{PLANET_R}" fill="none" stroke="{SAND}" stroke-opacity="0.55" stroke-width="1.2"/>
  <ellipse cx="{GX}" cy="{top}" rx="340" ry="26" fill="url(#flare)">
    <animate attributeName="rx" values="300;380;300" dur="8s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0.75;1;0.75" dur="8s" repeatCount="indefinite"/>
  </ellipse>
  <ellipse cx="{GX}" cy="{top}" rx="60" ry="3" fill="{IVORY}"/>''')

    # the year's total, written on the ground
    total = cal["totalContributions"]
    label = f"{total:,} contributions in the last year · one star for every day"
    p.append(f'  <path d="{"".join(glyphs(label, 28, cx, H - 88))}" fill="{SAND}" opacity="0.8"/>')

    p.append(f'''  <rect width="{W}" height="{H}" fill="url(#vig)"/>
  <rect width="{W}" height="{H}" fill="url(#grain)"/>
</g>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="19.5" fill="none" stroke="{GOLD}" stroke-opacity="0.22"/>''')

    body = "\n".join(p)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
            f'role="img" aria-label="{NAME}: {total} contributions in the last year, drawn as a galaxy">\n{body}\n</svg>\n')


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "assets", "space.svg")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    body = build(calendar())
    with open(out, "w") as fh:
        fh.write(body)
    print(f"{out}  {len(body) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
