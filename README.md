# Heart of Spades

A personal love letter webpage: a tap-through story told one moment at a time, with a heart of flowers that grows with every chapter and ends on a live count of the days since it all began.

## Features

- Cover screen ("For Sanjana") — the story starts when she opens it, with a different greeting on special days
- One scene per milestone, advanced by tapping, each signed with a typed line of Python-style code
- Blooming heart on HTML5 Canvas that grows from the tip up both sides and closes at the finale
- The date of each moment shown inside the heart; at the end it becomes a live days/hours/minutes/seconds counter
- Live ages for the marriage and both boys
- Particle bursts for the boys' names, drifting sparkles, shooting stars, floating hearts on tap/hold
- Each chapter colour-grades the ambient glow (scene `data-tint`), with a heart thump on every tap
- Two colour themes: Midnight Rose by default, Champagne Dawn automatically on the anniversary (Jan 26) — blooms follow the theme
- Finale counts the days up from zero; a gold progress line tracks the story under the scenes
- Designed for phones first (portrait, Safari/Chrome); also works in landscape and on desktop

## Editing the story

The words live in `index.html` as `.scene` blocks; the dates are in the small script at the bottom of the same file.

## Tech

Pure vanilla HTML/CSS/JavaScript with jQuery. No build tools or frameworks.

## Stop-motion films

The project includes two 24-second silent 12 fps stop-motion films in `video/`:
- **The House We Made** (`video/heart-of-spades-stop-motion.mp4` & `video/heart-of-spades-poster.png`) — a multi-plane handcrafted paper-diorama film.
- **Sculpted in Clay** (`video/heart-of-spades-clay-stop-motion.mp4`, `video/heart-of-spades-clay-poster.png` & live browser player `video/clay.html`) — a 3D plasticine claymation desk-morph film on an animator's cutting mat.

Their source renderers and regeneration notes are in `video/README.md`.

```
index.html          - Cover, scenes and dates
css/default.css     - All styles
js/functions.js     - Particles, story engine, heart growth, timers
js/garden.js        - Canvas bloom engine (Vector, Petal, Bloom, Garden)
js/jquery.js        - Vendored jQuery
images/             - Favicons, PWA manifest, icons
video/              - Stop-motion film, poster and frame renderer
```
