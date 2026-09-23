# Setup

This is the GitHub **profile README** repo: it only shows up if the repo is named exactly
`BhavithParna` and is **public**. Only `README.md` and `assets/` appear on the profile.

## The look

The whole profile is one image, `space.svg`, rendered by `tools/gen_space.py`:

- **Top:** the name, stroke-drawn then filled with a moving shimmer, over drifting warm light,
  orbit rings and rising dust.
- **Middle:** the last year of contributions as a spiral galaxy. One star per day. Weeks run
  along the arm from the core (a year ago) to the tip (today), and the seven weekday rows
  run across it, so it's the contribution calendar wound into a spiral. Brighter, bigger
  stars mean busier days. A comet rides the arm every 12 s and lights each day as it passes.
  Today pulses at the tip.
- **Bottom:** a planet's horizon, with the year's total written on it.

`.github/workflows/space.yml` re-renders it every 12 hours and on every push, and publishes
it to the `output` branch, which the README points at. Add a `GH_PAT` secret (classic
token, `repo` scope) so the galaxy counts private contributions too:

```bash
gh secret set GH_PAT --repo BhavithParna/BhavithParna
```

Local preview (uses your `gh` login for the data; writes the gitignored `assets/space.svg`):

```bash
python3 tools/gen_space.py
```

Palette constants and layout numbers sit at the top of the script. The lettering is baked
into outlines from `tools/fonts/InstrumentSerif-Italic.ttf` (OFL), because an `<img>` SVG
can't load web fonts. Needs `fontTools`, `Pillow`, `numpy`.

## Rules for editing the SVG

- **SMIL only** (`<animate>`, `<animateTransform>`, `<animateMotion>`). No CSS, no `<script>`.
  That's what keeps the motion alive through GitHub's image proxy.
- No `feTurbulence` or blur filters on anything that moves. Chrome re-renders the whole
  image every frame. Grain is a small embedded PNG tile, and the nebula is overlapping
  radial gradients.
- The galaxy is drawn flat, then squashed by `scale(1 TILT)` for perspective, so anything
  inside it renders `TILT` times shorter. Size stars up to compensate.
- Headless screenshots need `svg.pauseAnimations(); svg.setCurrentTime(t)` on an inline SVG,
  plus a short wait before capture, or you'll see frame 0.
