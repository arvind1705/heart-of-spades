# Heart of Spades — Stop-Motion Film

`heart-of-spades-stop-motion.mp4` is a 24-second, 12 fps (animated on twos), silent handcrafted paper-diorama stop-motion film built around the milestones of Aravind, Sanjana, Daivik, and Deeyan.

It is called **The House We Made**. Across seven depth planes of deckle-edged watercolor paper and walnut wood, a hillside sanctuary comes to life chapter by chapter:

1. **Prologue & First Meeting (20 Jan 2022)** — Golden-hour hills, a blossoming tree, a wrought-iron garden lantern with a `20 JAN ’22` signpost, and two paper-cutout silhouettes meeting along a winding stepping-stone path.
2. **First Love & The Promise (27 Jan & 11 Feb 2022 · 04 Dec 2022)** — The timber-and-stucco cottage unfolds with shuttered windows, flower boxes, arched fanlight door, and warm festoon string lights glowing across the twilight garden.
3. **Our Marriage (26 Jan 2023)** — Festive wedding bunting, an `EST · 26 JAN 2023` brass lintel plaque above the front door, a brick hearth chimney with curling paper-puff smoke, and an east-garden rose pergola.
4. **Daivik (03 Aug 2024) & Deeyan (09 Sep 2026)** — Symmetrical upstairs nursery dormers unfold on the roof (one with a swaying star mobile and `03 AUG 2024` sill plaque, one with a rocking paper boat and `09 SEP 2026` sill plaque), while named constellations (`DAIVIK · 03 AUG 2024` and `DEEYAN · 09 SEP 2026`) illuminate in the starlit night sky above.
5. **Finale & Milestone Register** — Four glowing windows, warm golden doorway light spilling down the steps, drifting fireflies, all four family silhouettes standing together at the threshold of home, a dated 7-node brass milestone timeline rail across the walnut stage apron, and an engraved family register plaque (`MARRIED 26 JAN 2023 · DAIVIK 03 AUG 2024 · DEEYAN 09 SEP 2026`).

The film is 1280×720 H.264 with a muted start by design. The poster frame (`heart-of-spades-poster.png`) captures the completed starlit finale.

## Regenerating

From the repository root:

```bash
# 1. Paper-Diorama Stop-Motion Film ("The House We Made")
python3 video/generate_stop_motion.py

# 2. 3D Plasticine Claymation Film ("Sculpted in Clay")
python3 video/generate_clay_stop_motion.py
```

The paper-diorama renderer (`generate_stop_motion.py`) builds multi-plane SVG scenes with `<clipPath>`, `<feTurbulence>` / `<feDisplacementMap>` deckled-paper edges, radial lighting gradients, and multi-pass drop shadows, rasterizes via `rsvg-convert` in parallel across CPU cores, and applies a NumPy cotton-paper grain and stop-motion exposure-flicker pass before encoding with `imageio-ffmpeg`.

---

## Variation 2 — Plasticine Claymation Film (`heart-of-spades-clay-stop-motion.mp4`)

`heart-of-spades-clay-stop-motion.mp4` (with poster `heart-of-spades-clay-poster.png` and browser player `video/clay.html`) is a 24-second, 12 fps (animated on twos) **3D plasticine claymation film** set on a green self-healing animator’s cutting mat and walnut workbench:

1. **Physical Medium & 3D SDF Clay Engine (`generate_clay_stop_motion.py`)** — A coarse-to-fine 3D signed-distance-field (`smin`) raymarcher renders hand-sculpted plasticine capsules, rounded slabs, triangular roof prisms, and tori with waxy subsurface scattering (SSS), 3D swirling marble veins where terracotta, slate-blue, and ochre-gold clays knead together, sculptor thumb facets, and organic fingerprint grain that boils on twos (`12 fps`), casting soft area-light shadows onto the cutting mat.
2. **Real Clay Morph Progression & Seamless Loop**:
   - **Shot 01 (`20 Jan 2022 · First Met`)**: A central marbled lump of clay splits and rolls across the cutting mat into two rounded clay figures (**Aravind & Sanjana**) beside a coiled iron-clay lamppost (`20 JAN ’22`) and four pressed ivory-clay stepping stones.
   - **Shot 02 (`27 Jan & 11 Feb 2022 · First Love & Held Hands`)**: Their clay arms reach out and marble together as a wax-sealed clay love letter presses onto the mat.
   - **Shot 03 (`04 Dec 2022 · The Proposal`)**: A thick golden-ochre clay ring coils upward on a terracotta cushion, crowned by a faceted ivory-clay diamond.
   - **Shot 04 (`26 Jan 2023 · Our Marriage`)**: The ring morphs into the sculpted **Clay Cottage** with a pitched slate-blue roof, terracotta chimney puffing white clay smoke balls, marigold-and-terracotta wedding garland beads, and an `EST · 26 JAN 2023` lintel plaque.
   - **Shot 05 (`03 Aug 2024 · Daivik’s Birthday`)**: **Daivik** pinches out of the clay between his parents as the left upstairs nursery dormer (`03 AUG 2024`) and a copper-wire stop-motion star armature (`DAIVIK · 03 AUG 2024`) rise from the roof.
   - **Shot 06 (`09 Sep 2026 · Deeyan’s Birthday`)**: **Deeyan** pinches out beside Sanjana as the right upstairs nursery dormer (`09 SEP 2026`) and a second copper-wire star armature (`DEEYAN · 09 SEP 2026`) complete the house.
   - **Shot 07 & 08 (`Always & Again · Loop`)**: Holds on the full 4-person plasticine family sculpture (`heart-of-spades-clay-poster.png`) before kneading back into the single marbled lump of clay to loop seamlessly.
3. **Interactive Browser Player (`video/clay.html`)** — Letterboxed 16:9 player that starts muted and loops on load, pauses/resumes on `Space` or click, and reveals a hover scrub bar with milestone tick markers.
