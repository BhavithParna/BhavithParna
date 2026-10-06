# Setup

This is the GitHub **profile README** repo: it only shows up if the repo is named exactly
`BhavithParna` and is **public**. Only `README.md` and `assets/` appear on the profile.

## The look

The whole profile is one animated image, `assets/profile.svg`, rendered by
`tools/gen_profile.py` and committed. It borrows the portfolio's About page: the night sky
(navy → deep night, an ember dusk at the horizon, film grain), the Big Dipper drawing itself
in the corner, a shooting star every ~10 s, the name set like the site's wordmark (Playfair
bold with a terracotta outline echo, italic ember "parna"), and along the bottom an
automated iced-coffee station — a stepping conveyor, an espresso head that pours into each
cup as it stops underneath, a straw dropped in at the next stop, cups rolling off the end.
One cup every 2 s, eight stops, a 16 s loop.

Re-render after editing (needs `fontTools`, `Pillow`, `numpy`):

```bash
python3 tools/gen_profile.py && git add assets/profile.svg && git commit -m "re-render"
```

Palette, timing (`STOPS`, `STEP`, `DWELL`, `POUR_STOP`, `STRAW_STOP`) and layout numbers sit
at the top of the script. Fonts in `tools/fonts/` are the OFL faces the site uses (Playfair
Display, JetBrains Mono, Caveat, Anton); the lettering is baked to outlines because an
`<img>` SVG can't load web fonts.

## Rules for editing the SVG

- **SMIL only** (`<animate>`, `<animateTransform>`). No CSS, no `<script>`. That's what keeps
  the motion alive through GitHub's image proxy.
- No filters on anything that moves. Grain is a small embedded PNG tile; glows are radial
  gradients.
- Every moving part shares the 2 s step phase, so a new element only needs `dur="2s"` (or
  the 16 s cup period with `begin="-2s × index"`) to stay in sync with the belt.
- Headless previews: inline the SVG, then `svg.pauseAnimations(); svg.setCurrentTime(t)` and
  wait a beat before capturing, or you'll see frame 0.
