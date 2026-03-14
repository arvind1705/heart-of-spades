# AGENTS.md — Coding Agent Guidelines for Heart of Spades

## Project Overview

Static vanilla HTML/CSS/JavaScript Valentine's Day webpage. No build tools, no
package manager, no frameworks (except vendored jQuery 1.4.2). All JS runs as
global scripts loaded via `<script>` tags — load order matters.

## Build / Serve / Test

There is **no build step, no test suite, no linter, and no CI pipeline**.

```bash
# Serve locally (any static server works)
python3 -m http.server 8000
# or
npx serve .

# There are no test or lint commands to run.
```

To verify changes: open `index.html` in a browser and confirm:
1. Sparkle particles render on the background canvas
2. Typewriter types out the code panel content at ~30ms/char
3. Daivik name triggers a particle burst + glow effect
4. Heart bloom animation starts after typewriter finishes
5. Timer displays and updates every 500ms
6. Floating hearts appear on click/touch

Test on mobile widths (375px, 520px) using browser DevTools device emulation.

## File Structure & Dependencies

```
index.html           Main page + inline init script (sets start date, floating hearts)
css/default.css      All styles and responsive breakpoints
js/jquery.js         Vendored jQuery 1.4.2 — DO NOT MODIFY
js/garden.js         Canvas bloom engine (Vector, Petal, Bloom, Garden constructors)
js/functions.js      App logic: particles, typewriter, heart animation, timer
digital.ttf          Custom font for timer digits
images/              Favicons, PWA manifest, icons
```

**Script load order** (defined in `<head>`): `jquery.js` → `garden.js` → `functions.js`.
The inline `<script>` at the bottom of `<body>` in `index.html` runs after all
three are loaded and handles page-specific initialization.

**Dependency direction**: `functions.js` depends on `garden.js` (instantiates
`Garden`, uses `Garden.options`) and jQuery. `garden.js` is self-contained.

## JavaScript Code Style

### Language Level
- **ES5 only**. Use `var`, not `let`/`const`. No arrow functions, no template
  literals, no destructuring, no `class` syntax, no modules.

### Variables & Naming
- **camelCase** for variables and functions: `particleCanvas`, `createParticle`,
  `computeHeartMetrics`
- **PascalCase** for constructor functions: `Vector`, `Petal`, `Bloom`, `Garden`
- **`$` prefix** for jQuery-wrapped elements: `$garden`, `$loveHeart`, `$words`
- Single-letter variables are acceptable in math-heavy code (heart curve,
  vector math, loop counters)
- Globals are used extensively — this is intentional, not an oversight

### Functions
- Use **function declarations** (`function foo() {}`) for named functions
- Use **function expressions** for prototype methods and callbacks
- Use **IIFE** for jQuery plugin definitions
- No arrow functions

### Formatting
- **Tabs** for indentation in `.js` files
- **4 spaces** for indentation in `.css` and `.html` files
- **Semicolons**: always, at end of every statement
- **Braces**: opening brace on same line (`function foo() {`)
- **Quotes**: double quotes for jQuery selectors and DOM strings (`"#loveHeart"`,
  `"block"`); single quotes for other string literals (`'circle'`, `'hsla(...)'`)

### jQuery Usage
- DOM selection: `$("selector")` with double-quoted selectors
- DOM ready: `$(function () { ... })`
- Animations: `.animate()`, `.fadeOut()`, `.css()`
- Dimensions: `.width()`, `.height()`, `.position()`
- Native DOM APIs are used alongside jQuery when appropriate
  (`document.getElementById`, `requestAnimationFrame`, `classList`, `canvas.getContext`)

### OOP Pattern
- **Prototype-based** — constructor functions + `Foo.prototype = { ... }`
- Static methods/properties attached directly to constructor: `Garden.random`,
  `Garden.options`, `Garden.romanticPalette`
- No ES6 `class` syntax

### Error Handling
- Minimal. Guard clauses (`if (!x) return`) for null canvas elements.
- Canvas support check in the inline script (`if (!document.createElement("canvas").getContext)`).
- No `try/catch` blocks. This is a decorative page, not a production app.

### Mobile Awareness
- `isMobile` boolean (width <= 768 or touch support) controls performance knobs
- Particle counts, `shadowBlur` values, and burst sizes are halved on mobile
- Always use `isMobile` ternaries for GPU-heavy values (shadow, particle count)

## CSS Code Style

### Formatting
- **4 spaces** for indentation
- Section headers: `/* --- Section Name --- */`
- File header: multi-line `/* === ... === */` block comment

### Naming
- **IDs**: camelCase (`#mainDiv`, `#loveHeart`, `#elapseClock`)
- **Classes**: kebab-case (`.daivik-name`, `.time-label`) or single words
  (`.comments`, `.prose`, `.cursor`)
- **Not BEM** — flat class names, scoped under parent IDs when needed
  (`#code .comments`, `#elapseClock .digit`)

### Architecture
- Single CSS file (`default.css`) — no preprocessor, no CSS modules
- Global reset at top, then components by DOM order, responsive at bottom
- Four responsive breakpoints: `1200px`, `640px`, `520px`, `375px`
- Uses modern CSS: `aspect-ratio`, `backdrop-filter`, flexbox, `env()` safe
  areas, `@supports` for iOS detection, CSS custom properties
- Google Fonts loaded via `<link>` in HTML, not `@import` in CSS

## HTML Style

- HTML5 doctype, `lang="en"`
- **4 spaces** indentation
- Self-closing tags with space before slash: `<br />`, `<meta ... />`
- Double quotes for all attributes
- External scripts in `<head>` (no `defer`/`async`); inline script at end of `<body>`

## Git Conventions

- **Branch**: `main` (only branch)
- **Remote**: `git@github.com:arvind1705/heart-of-spades.git`
- **Commit messages**: imperative mood, capitalized first word. No conventional
  commits prefix. Examples: "Add initial README", "Enhance romantic theme"
- **No `.gitignore`** currently exists
- **No pre-commit hooks** or automated checks

## Key Gotchas

1. **Do not modify `js/jquery.js`** — it is a vendored dependency
2. **Script load order matters** — jQuery must load before garden.js, which must
   load before functions.js
3. **All JS is global** — no module system. Variable/function name collisions are
   a real risk
4. **Canvas dimensions** are set programmatically in `sizeCanvas()` from the
   CSS-laid-out `#loveHeart` container. Never hardcode pixel dimensions.
5. **Heart curve scale factors** (`heartScaleX`, `heartScaleY`) are computed
   proportionally from canvas size. The reference design is 620x580.
6. **`adjustWordsPosition()`** uses proportional ratios — do not use hardcoded
   pixel offsets
7. **iOS Safari**: `background-attachment: fixed` is broken — handled by
   `@supports (-webkit-touch-callout: none)` fallback
8. **Performance**: `shadowBlur` on canvas is GPU-expensive. Always gate behind
   `isMobile` checks and keep values low
