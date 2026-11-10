# Heart of Spades

A personal love letter webpage: a tap-through story told one moment at a time, with a heart of flowers that grows with every chapter and ends on a live count of the days since it all began.

## Features

- Cover screen ("For Sanjana") — the story starts when she opens it, with a different greeting on special days
- One scene per milestone, advanced by tapping, each signed with a typed line of Python-style code
- Blooming heart on HTML5 Canvas that grows from the tip up both sides and closes at the finale
- The date of each moment shown inside the heart; at the end it becomes a live days/hours/minutes/seconds counter
- Live ages for the marriage and both boys
- Particle bursts for the boys' names, drifting sparkles, shooting stars, floating hearts on tap/hold
- Designed for phones first (portrait, Safari/Chrome); also works in landscape and on desktop

## Adding photos (optional)

Drop JPEGs into `images/photos/` and they appear inside the heart on the matching scene. Missing files are simply skipped.

| File | Scene |
| --- | --- |
| `met.jpg` | Jan 20, 2022 — I met you |
| `love.jpg` | Jan 27, 2022 — I love you |
| `hands.jpg` | Feb 11, 2022 — holding hands |
| `us.jpg` | Every day |
| `proposal.jpg` | Dec 4, 2022 |
| `wedding.jpg` | Jan 26, 2023 |
| `daivik.jpg` | Aug 3, 2024 |
| `deeyan.jpg` | Sep 9, 2026 |
| `family.jpg` | Finale |

Square-ish photos with faces in the upper half work best (the heart narrows toward the bottom). Keep each under ~300 KB.

## Editing the story

The words live in `index.html` as `.scene` blocks; the dates are in the small script at the bottom of the same file.

## Tech

Pure vanilla HTML/CSS/JavaScript with jQuery. No build tools or frameworks.

```
index.html          - Cover, scenes and dates
css/default.css     - All styles
js/functions.js     - Particles, story engine, heart growth, timers
js/garden.js        - Canvas bloom engine (Vector, Petal, Bloom, Garden)
js/jquery.js        - Vendored jQuery
images/             - Favicons, PWA manifest, optional photos
```
