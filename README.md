# Heart of Spades

A personal love letter webpage featuring a typewriter-animated pseudo-code narrative alongside a blooming heart canvas animation with a live elapsed-time counter.

## Features

- Typewriter effect that types out a love story in Python-style pseudo-code, gradually shifting to romantic prose for later milestones
- Blooming heart animation rendered on HTML5 Canvas with a romantic colour palette
- Live elapsed-time counter from the relationship start date
- Floating sparkle particle system with warm gold tones
- Special particle burst effect for key moments
- Floating hearts on click/touch interaction
- Dark romantic theme with glassmorphic UI elements
- Mobile-optimised with responsive scaling, reduced GPU effects, and safe area support

## Tech

Pure vanilla HTML/CSS/JavaScript with jQuery. No build tools or frameworks.

## Structure

```
index.html          - Main page and inline interaction scripts
css/default.css     - All styles, responsive breakpoints
js/functions.js     - App logic: particles, typewriter, heart animation, timer
js/garden.js        - Canvas bloom engine (Vector, Petal, Bloom, Garden)
js/jquery.js        - Vendored jQuery
digital.ttf         - Custom font for timer digits
images/             - Favicons and PWA manifest
```
