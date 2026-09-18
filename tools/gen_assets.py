#!/usr/bin/env python3
"""Generate the animated SVG assets for the profile README.

Everything is SMIL + CSS-free SVG so GitHub renders it through camo without
stripping the animation. Run:  python3 tools/gen_assets.py
"""
import random

GREEN      = "#00FF41"   # phosphor
GREEN_DIM  = "#0B7A2E"
GREEN_MID  = "#19C04A"
CYAN       = "#7CFFC4"
BG         = "#050806"
W          = 1200

random.seed(86)          # deterministic output


def rain_columns(width, height, count, char_h=17, seed_offset=0):
    """Falling code columns, each its own glyph run and fall speed."""
    rnd = random.Random(86 + seed_offset)
    out = []
    step = width / count
    for i in range(count):
        x     = round(i * step + rnd.uniform(-4, 4), 1)
        rows  = int(height / char_h) + 8
        chars = "".join(rnd.choice("01") for _ in range(rows))
        dur   = round(rnd.uniform(5.5, 13.0), 2)
        begin = round(-rnd.uniform(0, dur), 2)
        op    = round(rnd.uniform(0.10, 0.30), 2)
        span  = "".join(
            f'<tspan x="{x}" dy="{char_h}">{c}</tspan>' for c in chars
        )
        travel = rows * char_h
        out.append(
            f'<g opacity="{op}">'
            f'<text font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
            f'font-size="{char_h - 3}" fill="url(#colFade)" y="{-travel}">{span}'
            f'<animateTransform attributeName="transform" type="translate" '
            f'from="0 0" to="0 {travel}" dur="{dur}s" begin="{begin}s" '
            f'repeatCount="indefinite"/></text></g>'
        )
    return "\n    ".join(out)


def defs(height):
    return f'''  <defs>
    <linearGradient id="colFade" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{GREEN}" stop-opacity="0"/>
      <stop offset="55%" stop-color="{GREEN_DIM}" stop-opacity="0.55"/>
      <stop offset="88%" stop-color="{GREEN}" stop-opacity="1"/>
      <stop offset="100%" stop-color="{CYAN}" stop-opacity="1"/>
    </linearGradient>
    <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="2.4" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">
      <rect width="4" height="2" fill="#000" opacity="0.16"/>
    </pattern>
    <clipPath id="screen"><rect x="0" y="0" width="{W}" height="{height}" rx="12"/></clipPath>
  </defs>'''


def boot_svg():
    H = 380
    lines = [
        (0.0,  "&gt; booting bhavith.sys ...",         GREEN, 15),
        (0.8,  "[  OK  ]  coffee.daemon      online",  GREEN_MID, 14),
        (1.4,  "[ FAIL ]  sleep.service      timeout", GREEN_MID, 14),
        (2.0,  "[  OK  ]  curiosity          online",  GREEN_MID, 14),
        (2.6,  "[  OK  ]  bad.ideas          online",  GREEN_MID, 14),
    ]
    CYCLE = 14.0
    body = []
    y = 74
    for t, txt, col, size in lines:
        k1 = t / CYCLE
        k2 = (t + 0.25) / CYCLE
        body.append(
            f'<text x="56" y="{y}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
            f'font-size="{size}" fill="{col}" letter-spacing="1" opacity="0">{txt}'
            f'<animate attributeName="opacity" dur="{CYCLE}s" repeatCount="indefinite" '
            f'values="0;0;1;1;0;0" keyTimes="0;{k1:.4f};{k2:.4f};0.92;0.97;1"/></text>'
        )
        y += 26

    # the name — big, glowing, with a chromatic ghost
    nk1, nk2 = 3.4 / CYCLE, 3.75 / CYCLE
    name_anim = (f'<animate attributeName="opacity" dur="{CYCLE}s" repeatCount="indefinite" '
                 f'values="0;0;1;1" keyTimes="0;{nk1:.4f};{nk2:.4f};1"/>')
    body.append(
        f'<text x="54" y="272" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
        f'font-size="54" font-weight="700" letter-spacing="5" fill="{CYAN}" opacity="0" '
        f'filter="url(#glow)">BHAVITH PARNA{name_anim}</text>'
    )
    body.append(
        f'<text x="56" y="270" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
        f'font-size="54" font-weight="700" letter-spacing="5" fill="{GREEN}" opacity="0" '
        f'filter="url(#glow)">BHAVITH PARNA{name_anim}</text>'
    )
    sk1, sk2 = 4.1 / CYCLE, 4.4 / CYCLE
    body.append(
        f'<text x="58" y="306" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
        f'font-size="15" letter-spacing="3" fill="{GREEN_MID}" opacity="0">'
        f'&gt; downhill mode: engaged'
        f'<animate attributeName="opacity" dur="{CYCLE}s" repeatCount="indefinite" '
        f'values="0;0;1;1" keyTimes="0;{sk1:.4f};{sk2:.4f};1"/></text>'
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Booting bhavith.sys — Bhavith Parna, signal to intent to machine">
{defs(H)}
  <rect width="{W}" height="{H}" rx="12" fill="{BG}"/>
  <g clip-path="url(#screen)">
    {rain_columns(W, H, 30)}
  </g>
  <g clip-path="url(#screen)">
    <rect x="0" y="34" width="680" height="316" fill="{BG}" opacity="0.82"/>
    {chr(10).join("    " + b for b in body)}

    <!-- cursor -->
    <rect x="58" y="330" width="14" height="22" fill="{GREEN}" filter="url(#glow)">
      <animate attributeName="opacity" values="1;1;0;0" dur="1.06s" repeatCount="indefinite"/>
    </rect>

    <!-- CRT scan bar sweeping down -->
    <rect x="0" y="0" width="{W}" height="64" fill="{GREEN}" opacity="0.045">
      <animate attributeName="y" from="-64" to="{H}" dur="4.2s" repeatCount="indefinite"/>
    </rect>

    <!-- tracking glitch: a band that tears across every few seconds -->
    <rect x="0" y="150" width="{W}" height="9" fill="{CYAN}" opacity="0">
      <animate attributeName="opacity" values="0;0;0.5;0;0.28;0;0" keyTimes="0;0.62;0.635;0.65;0.665;0.69;1" dur="{14.0}s" repeatCount="indefinite"/>
      <animate attributeName="y" values="150;150;96;300;212;212;212" keyTimes="0;0.62;0.635;0.65;0.665;0.69;1" dur="{14.0}s" repeatCount="indefinite"/>
    </rect>
  </g>
  <rect width="{W}" height="{H}" rx="12" fill="url(#scan)"/>
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" fill="none" stroke="{GREEN_DIM}" stroke-opacity="0.5"/>
</svg>'''


def divider_svg():
    H = 22
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="">
  <defs>
    <linearGradient id="dg" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{GREEN}" stop-opacity="0"/>
      <stop offset="20%" stop-color="{GREEN}" stop-opacity="0.75"/>
      <stop offset="80%" stop-color="{GREEN}" stop-opacity="0.75"/>
      <stop offset="100%" stop-color="{GREEN}" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <line x1="0" y1="11" x2="{W}" y2="11" stroke="{GREEN_DIM}" stroke-width="1.2" stroke-opacity="0.55"/>
  <line x1="0" y1="11" x2="{W}" y2="11" stroke="url(#dg)" stroke-width="2" stroke-dasharray="14 26">
    <animate attributeName="stroke-dashoffset" from="0" to="-40" dur="1.05s" repeatCount="indefinite"/>
  </line>
</svg>'''


CAR = [
    r"                 ______________",
    r"            ____/              \____",
    r"       ____/                        \____",
    r"      |                                   |",
    r"      |____( )______________________( )___|",
]


def ae86_svg():
    """ASCII AE86 on a moving road, because the terminal needed a car in it."""
    H = 230
    rows = "".join(
        f'<tspan x="60" dy="{0 if i == 0 else 26}" xml:space="preserve">{ln}</tspan>'
        for i, ln in enumerate(CAR)
    )
    speed = []
    for i, (y, ln, dur, op) in enumerate(
        [(52, 150, 1.5, 0.5), (78, 210, 1.1, 0.7), (118, 120, 1.8, 0.4),
         (146, 190, 1.3, 0.6), (170, 140, 1.6, 0.45)]
    ):
        speed.append(
            f'<line x1="{W}" y1="{y}" x2="{W + ln}" y2="{y}" stroke="{GREEN}" '
            f'stroke-opacity="{op}" stroke-width="2">'
            f'<animateTransform attributeName="transform" type="translate" '
            f'from="0 0" to="{-(W + ln + 120)} 0" dur="{dur}s" begin="{-i * 0.37:.2f}s" '
            f'repeatCount="indefinite"/></line>'
        )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="An ASCII AE86 driving">
{defs(H)}
  <rect width="{W}" height="{H}" rx="12" fill="{BG}"/>
  <g clip-path="url(#screen)">
    {rain_columns(W, H, 22, seed_offset=7)}
    {chr(10).join("    " + s for s in speed)}
    <g>
      <animateTransform attributeName="transform" type="translate" values="0 0;0 -2.5;0 0;0 2;0 0"
                        dur="1.9s" repeatCount="indefinite"/>
      <text y="60" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="20"
            fill="{GREEN}" filter="url(#glow)" letter-spacing="1">{rows}</text>
    </g>
    <line x1="0" y1="196" x2="{W}" y2="196" stroke="{GREEN_DIM}" stroke-width="2" stroke-opacity="0.6"/>
    <line x1="0" y1="196" x2="{W}" y2="196" stroke="{GREEN}" stroke-width="3" stroke-dasharray="34 46">
      <animate attributeName="stroke-dashoffset" from="0" to="-80" dur="0.55s" repeatCount="indefinite"/>
    </line>
  </g>
  <rect width="{W}" height="{H}" rx="12" fill="url(#scan)"/>
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" fill="none" stroke="{GREEN_DIM}" stroke-opacity="0.5"/>
</svg>'''


if __name__ == "__main__":
    import pathlib
    root = pathlib.Path(__file__).resolve().parent.parent / "assets"
    (root / "boot.svg").write_text(boot_svg())
    (root / "divider.svg").write_text(divider_svg())
    (root / "ae86.svg").write_text(ae86_svg())
    print("wrote boot.svg, divider.svg, ae86.svg")
