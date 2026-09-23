# Setup

This is the GitHub **profile README** repo: it only shows up if the repo is named exactly
`BhavithParna` and is **public**. Only `README.md` and `assets/` appear on the profile.

## The look

Espresso / caramel / latte / cream, all generated:

```bash
python3 tools/gen_assets.py     # rewrites every SVG in assets/
```

| file | what it is |
|---|---|
| `hero.svg` | the name, stroke-drawn then filled with a moving shimmer, over drifting colour fields, orbit rings, rising dust and film grain |
| `silk.svg` | 44 threads twisting into a ribbon (path morphing) |
| `mandala.svg` | counter-rotating petal rings with a breathing core |
| `globe.svg` | a spinning dot sphere with a moon that ducks behind it |
| `liquid.svg` | morphing caramel blobs |
| `ripple.svg` | a dot matrix with two interfering wavefronts |
| `dunes.svg` | parallax dunes, striped setting sun, blowing sand |
| `divider.svg` | the gold thread between sections |

Palette constants sit at the top of the generator. The name is baked into outlines from
`tools/fonts/InstrumentSerif-Italic.ttf` (OFL), because an `<img>` SVG can't load web fonts.
Needs `fontTools`, `Pillow`, `numpy`.

The contribution snake at the bottom is built by `.github/workflows/snake.yml` into the
`output` branch, in the same palette (a light and a dark version). Add a `GH_PAT` secret
(classic token, `repo` scope) if you want it to count private contributions.

## Rules for editing the SVGs

- **SMIL only** (`<animate>`, `<animateTransform>`, `<animateMotion>`). No CSS, no `<script>`.
  That's what keeps the motion alive through GitHub's image proxy.
- No `feTurbulence` or big blur filters on anything animated. Chrome re-renders the whole image
  every frame. Grain is a small embedded PNG tile instead.
- Headless screenshots need `svg.pauseAnimations(); svg.setCurrentTime(t)` on an inline SVG,
  plus a short wait before capture, or you'll see frame 0.
