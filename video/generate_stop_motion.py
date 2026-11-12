#!/usr/bin/env python3
"""Render *The House We Made*, a handcrafted multi-plane paper-diorama stop-motion film.

Built for Sanjana, Aravind, Daivik, and Deeyan.
Uses high-precision SVG scene generation rasterized via rsvg-convert (with deckled
paper displacement filters, clip paths, radial lighting gradients, and multi-plane
drop shadows) plus a NumPy tactile cotton-paper grain and stop-motion boil pass.
No heart glyphs, flower-heart wreaths, or code/typewriter cards are used.
"""

from concurrent.futures import ProcessPoolExecutor
import io
import math
import os
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

try:
    import imageio_ffmpeg
except ImportError as exc:
    raise SystemExit("Install the renderer with: python3 -m pip install --user imageio-ffmpeg") from exc


WIDTH = 1280
HEIGHT = 720
FPS = 12
DURATION = 24
TOTAL_FRAMES = FPS * DURATION
OUT_DIR = Path(__file__).resolve().parent
OUT_FILE = OUT_DIR / "heart-of-spades-stop-motion.mp4"
POSTER_FILE = OUT_DIR / "heart-of-spades-poster.png"
RSVG_BIN = "/opt/homebrew/bin/rsvg-convert"


STAGES = [
    {
        "badge_date": "PROLOGUE",
        "event_tag": "FOR SANJANA",
        "title": "A quiet hillside.",
        "subtitle": "Waiting for the dates that would shape our life.",
        "footer": "ARAVIND & SANJANA · HANDCRAFTED PAPER DIORAMA",
        "prop": "letter",
        "progress": 0.05,
        "sky_phase": 0.0,
        "milestone_idx": -1,
    },
    {
        "badge_date": "20 JAN 2022",
        "event_tag": "THE DAY WE MET",
        "title": "Our paths crossed.",
        "subtitle": "Under the winter lantern, one small door opened.",
        "footer": "MILESTONE I · FIRST MEETING · 20 JANUARY 2022",
        "prop": "lantern",
        "progress": 0.16,
        "sky_phase": 0.16,
        "milestone_idx": 0,
    },
    {
        "badge_date": "27 JAN & 11 FEB ’22",
        "event_tag": "FIRST LOVE & HELD HANDS",
        "title": "A place for two.",
        "subtitle": "Spoken on 27 Jan, hand in hand on 11 Feb.",
        "footer": "MILESTONE II · 27 JAN 2022 & 11 FEB 2022",
        "prop": "keys",
        "progress": 0.34,
        "sky_phase": 0.32,
        "milestone_idx": 1,
    },
    {
        "badge_date": "04 DEC 2022",
        "event_tag": "THE PROPOSAL",
        "title": "We chose forever.",
        "subtitle": "I asked beneath the warm lights, and you said yes.",
        "footer": "MILESTONE III · ENGAGED · 04 DECEMBER 2022",
        "prop": "ring",
        "progress": 0.48,
        "sky_phase": 0.48,
        "milestone_idx": 2,
    },
    {
        "badge_date": "26 JAN 2023",
        "event_tag": "OUR MARRIAGE",
        "title": "We made it home.",
        "subtitle": "Hand in hand, our marriage lit the hearth forever.",
        "footer": "MILESTONE IV · MARRIED · 26 JANUARY 2023",
        "prop": "garland",
        "progress": 0.62,
        "sky_phase": 0.64,
        "milestone_idx": 3,
    },
    {
        "badge_date": "03 AUG 2024",
        "event_tag": "DAIVIK’S BIRTHDAY",
        "title": "Daivik arrived.",
        "subtitle": "Our first miracle lit a brand-new window upstairs.",
        "footer": "MILESTONE V · DAIVIK BORN · 03 AUGUST 2024",
        "prop": "cradle_star",
        "progress": 0.76,
        "sky_phase": 0.78,
        "milestone_idx": 4,
    },
    {
        "badge_date": "09 SEP 2026",
        "event_tag": "DEEYAN’S BIRTHDAY",
        "title": "Deeyan arrived.",
        "subtitle": "Loved long before we met you — then we were four.",
        "footer": "MILESTONE VI · DEEYAN BORN · 09 SEPTEMBER 2026",
        "prop": "paper_boat",
        "progress": 0.90,
        "sky_phase": 0.90,
        "milestone_idx": 5,
    },
    {
        "badge_date": "OUR FAMILY HOME",
        "event_tag": "FOUR GLOWING WINDOWS",
        "title": "Four glowing windows.",
        "subtitle": "",
        "footer": "SANJANA · DAIVIK · DEEYAN · ARAVIND",
        "prop": "crest",
        "progress": 1.00,
        "sky_phase": 0.96,
        "milestone_idx": 6,
        "finale": True,
    },
    {
        "badge_date": "OUR MILESTONES",
        "event_tag": "WRITTEN IN LIGHT",
        "title": "Home is wherever we are.",
        "subtitle": "",
        "footer": "MET 20 JAN 2022 · ENGAGED 04 DEC 2022 · FOREVER",
        "prop": "crest",
        "progress": 1.00,
        "sky_phase": 1.0,
        "milestone_idx": 6,
        "finale": True,
    },
    {
        "badge_date": "ALWAYS & AGAIN",
        "event_tag": "FOR SANJANA",
        "title": "The lights stay on.",
        "subtitle": "",
        "footer": "MET 20 JAN 2022 · ENGAGED 04 DEC 2022 · ARAVIND",
        "prop": "crest",
        "progress": 1.00,
        "sky_phase": 1.0,
        "milestone_idx": 6,
        "finale": True,
    },
]

TIMELINE_MILESTONES = [
    {"date": "20 JAN ’22", "label": "WE MET"},
    {"date": "11 FEB ’22", "label": "FIRST LOVE"},
    {"date": "04 DEC ’22", "label": "ENGAGED"},
    {"date": "26 JAN ’23", "label": "MARRIED"},
    {"date": "03 AUG ’24", "label": "DAIVIK"},
    {"date": "09 SEP ’26", "label": "DEEYAN"},
    {"date": "FOREVER", "label": "OUR HOME"},
]


def clamp(val, lo=0.0, hi=1.0):
    return max(lo, min(hi, val))


def smoothstep(edge0, edge1, x):
    t = clamp((x - edge0) / max(1e-6, (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def ease_out_back(t, overshoot=1.22):
    t = clamp(t)
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    t1 = t - 1.0
    return 1.0 + (overshoot + 1.0) * (t1 ** 3) + overshoot * (t1 ** 2)


def lerp_color(c1, c2, t):
    t = clamp(t)
    return tuple(int(round(c1[i] + (c2[i] - c1[i]) * t)) for i in range(3))


def hex_color(rgb):
    return "#%02x%02x%02x" % rgb


def xml_escape(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def pop_transform(cx, cy, t, slide_y=26.0, rotate_deg=0.0):
    """Return an SVG transform string that unfolds a paper piece into place."""
    s = ease_out_back(t, 1.20)
    alpha = smoothstep(0.0, 0.22, t)
    dy = (1.0 - s) * slide_y
    rot = (1.0 - s) * rotate_deg
    return (
        f'opacity="{alpha:.3f}" '
        f'transform="translate({cx:.1f},{cy + dy:.1f}) rotate({rot:.2f}) scale({max(0.01, s):.3f}) translate({-cx:.1f},{-cy:.1f})"'
    )


def build_sky_svg(sky_phase, picture):
    """Render an evolving multi-stop twilight sky, setting sun, rising moon, clouds, and dated constellations."""
    day_top = (54, 92, 128)
    day_mid = (142, 158, 156)
    day_bot = (244, 188, 126)

    dusk_top = (28, 48, 82)
    dusk_mid = (106, 88, 116)
    dusk_bot = (232, 138, 94)

    night_top = (12, 21, 39)
    night_mid = (26, 44, 72)
    night_bot = (72, 88, 108)

    if sky_phase < 0.5:
        u = sky_phase / 0.5
        c_top = lerp_color(day_top, dusk_top, u)
        c_mid = lerp_color(day_mid, dusk_mid, u)
        c_bot = lerp_color(day_bot, dusk_bot, u)
    else:
        u = (sky_phase - 0.5) / 0.5
        c_top = lerp_color(dusk_top, night_top, u)
        c_mid = lerp_color(dusk_mid, night_mid, u)
        c_bot = lerp_color(dusk_bot, night_bot, u)

    rng = random.Random(900)
    stars_svg = []
    star_vis = smoothstep(0.22, 0.76, sky_phase)
    for i in range(95):
        sx = rng.uniform(45, 1235)
        sy = rng.uniform(28, 395)
        sr = rng.choice([0.9, 1.1, 1.35, 1.7, 2.1])
        twinkle = 0.65 + 0.35 * math.sin(picture * 0.45 + i * 1.7)
        op = star_vis * twinkle * rng.uniform(0.45, 0.95)
        if op > 0.03:
            stars_svg.append(
                f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{sr:.2f}" fill="#fdf4dc" opacity="{op:.3f}"/>'
            )
            if sr > 1.8 and op > 0.55:
                stars_svg.append(
                    f'<path d="M {sx - 4.5:.1f} {sy:.1f} L {sx + 4.5:.1f} {sy:.1f} M {sx:.1f} {sy - 4.5:.1f} L {sx:.1f} {sy + 4.5:.1f}" '
                    f'stroke="#fdf4dc" stroke-width="0.7" opacity="{op * 0.65:.3f}"/>'
                )

    daivik_vis = smoothstep(0.68, 0.77, sky_phase)
    deeyan_vis = smoothstep(0.81, 0.89, sky_phase)
    constellations = []
    if daivik_vis > 0.01:
        pts1 = [(600, 84), (638, 62), (682, 74), (720, 50), (754, 76)]
        path1 = "M " + " L ".join(f"{x},{y}" for x, y in pts1)
        constellations.append(f'<g opacity="{daivik_vis:.3f}">')
        constellations.append(
            f'<path d="{path1}" fill="none" stroke="#f6d58e" stroke-width="1.2" stroke-dasharray="3,3" opacity="0.80"/>'
        )
        for x, y in pts1:
            constellations.append(f'<circle cx="{x}" cy="{y}" r="3.2" fill="#fff6df" filter="url(#softGlow)"/>')
            constellations.append(f'<circle cx="{x}" cy="{y}" r="1.8" fill="#ffffff"/>')
        constellations.append(
            '<text x="678" y="100" text-anchor="middle" font-family="Georgia, serif" font-weight="bold" '
            'font-size="11.5" fill="#fff2d0" letter-spacing="1.6">DAIVIK</text>'
            '<text x="678" y="114" text-anchor="middle" font-family="Avenir, Helvetica, sans-serif" font-weight="600" '
            'font-size="9.5" fill="#f0c878" letter-spacing="1.4">03 AUG 2024</text>'
        )
        constellations.append("</g>")

    if deeyan_vis > 0.01:
        pts2 = [(832, 74), (870, 50), (914, 60), (950, 40), (984, 66)]
        path2 = "M " + " L ".join(f"{x},{y}" for x, y in pts2)
        constellations.append(f'<g opacity="{deeyan_vis:.3f}">')
        constellations.append(
            f'<path d="{path2}" fill="none" stroke="#f6d58e" stroke-width="1.2" stroke-dasharray="3,3" opacity="0.80"/>'
        )
        for x, y in pts2:
            constellations.append(f'<circle cx="{x}" cy="{y}" r="3.2" fill="#fff6df" filter="url(#softGlow)"/>')
            constellations.append(f'<circle cx="{x}" cy="{y}" r="1.8" fill="#ffffff"/>')
        constellations.append(
            '<text x="908" y="90" text-anchor="middle" font-family="Georgia, serif" font-weight="bold" '
            'font-size="11.5" fill="#fff2d0" letter-spacing="1.6">DEEYAN</text>'
            '<text x="908" y="104" text-anchor="middle" font-family="Avenir, Helvetica, sans-serif" font-weight="600" '
            'font-size="9.5" fill="#f0c878" letter-spacing="1.4">09 SEP 2026</text>'
        )
        constellations.append("</g>")

    sun_vis = 1.0 - smoothstep(0.15, 0.56, sky_phase)
    sun_y = 325 + 125 * smoothstep(0.0, 0.56, sky_phase)
    moon_vis = smoothstep(0.22, 0.58, sky_phase)
    moon_y = 175 - 62 * smoothstep(0.22, 0.88, sky_phase)
    moon_x = 1092
    drift = (picture % 9) * 0.45

    return f"""
    <defs>
      <linearGradient id="skyGrad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="{hex_color(c_top)}"/>
        <stop offset="56%" stop-color="{hex_color(c_mid)}"/>
        <stop offset="100%" stop-color="{hex_color(c_bot)}"/>
      </linearGradient>
      <radialGradient id="horizonGlow" cx="66%" cy="78%" r="55%">
        <stop offset="0%" stop-color="#ffd28a" stop-opacity="{0.48 * (1.0 - 0.55 * sky_phase):.3f}"/>
        <stop offset="55%" stop-color="#e59568" stop-opacity="{0.20 * (1.0 - 0.5 * sky_phase):.3f}"/>
        <stop offset="100%" stop-color="#1b2a42" stop-opacity="0"/>
      </radialGradient>
      <radialGradient id="moonHalo" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="#fff3cf" stop-opacity="0.40"/>
        <stop offset="45%" stop-color="#f7d794" stop-opacity="0.14"/>
        <stop offset="100%" stop-color="#f7d794" stop-opacity="0"/>
      </radialGradient>
      <mask id="crescentMask">
        <rect x="980" y="20" width="220" height="220" fill="black"/>
        <circle cx="{moon_x}" cy="{moon_y:.1f}" r="35" fill="white"/>
        <circle cx="{moon_x - 15}" cy="{moon_y - 8:.1f}" r="30" fill="black"/>
      </mask>
    </defs>
    <rect x="0" y="0" width="{WIDTH}" height="560" fill="url(#skyGrad)"/>
    <rect x="0" y="0" width="{WIDTH}" height="560" fill="url(#horizonGlow)"/>

    <!-- Setting Golden-Hour Paper Sun (Chapters 1-3) -->
    <g opacity="{sun_vis:.3f}" filter="url(#paperShadowSm)">
      <circle cx="835" cy="{sun_y:.1f}" r="88" fill="#ffd98e" opacity="0.24" filter="url(#softGlow)"/>
      <circle cx="835" cy="{sun_y:.1f}" r="42" fill="#fce0a2" stroke="#fff4d6" stroke-width="1.2" opacity="0.88"/>
    </g>

    {''.join(stars_svg)}
    {''.join(constellations)}

    <!-- Rising Paper Crescent Moon (Chapters 3-10) -->
    <g opacity="{moon_vis:.3f}">
      <circle cx="{moon_x}" cy="{moon_y:.1f}" r="110" fill="url(#moonHalo)"/>
      <g filter="url(#paperShadowSm)">
        <circle cx="{moon_x}" cy="{moon_y:.1f}" r="35" fill="#faecc8" mask="url(#crescentMask)"/>
      </g>
    </g>

    <!-- Layered Hand-Torn Paper Clouds -->
    <g filter="url(#decklePaper)" opacity="0.88" transform="translate({drift:.1f}, 0)">
      <path d="M 530 168 Q 555 144 590 152 Q 618 134 652 148 Q 684 142 702 164 Q 722 168 718 182 L 522 182 Q 514 170 530 168 Z"
            fill="#f5e8ce" fill-opacity="{0.34 - 0.14 * sky_phase:.3f}" stroke="#fdf5e6" stroke-opacity="0.28" stroke-width="1.1"/>
      <path d="M 965 212 Q 992 190 1026 198 Q 1056 182 1088 196 Q 1118 192 1134 210 L 955 212 Z"
            fill="#f5e8ce" fill-opacity="{0.28 - 0.10 * sky_phase:.3f}" stroke="#fdf5e6" stroke-opacity="0.24" stroke-width="1.1"/>
    </g>
    """


def build_landscape_svg(progress, sky_phase, picture):
    """Render layered watercolor-paper hills, distant trees, meadow contours, and stone pathway."""
    night_darken = 0.25 * sky_phase
    far_hill = lerp_color((74, 108, 118), (36, 56, 72), night_darken * 2.2)
    mid_hill = lerp_color((90, 124, 110), (44, 68, 68), night_darken * 2.2)
    near_hill = lerp_color((116, 140, 104), (56, 76, 64), night_darken * 2.2)
    meadow_col = lerp_color((138, 150, 98), (68, 82, 62), night_darken * 2.0)

    path_t = smoothstep(0.01, 0.16, progress)
    stones = [
        (235, 596, 26, 10, -7),
        (315, 585, 28, 10, -6),
        (396, 576, 29, 11, -3),
        (478, 573, 30, 11, 0),
        (560, 575, 30, 11, 2),
        (642, 578, 30, 11, 1),
    ]
    stone_svg = []
    for idx, (sx, sy, rx, ry, rot) in enumerate(stones):
        st = clamp((path_t * len(stones)) - idx * 0.72)
        if st > 0.01:
            sc = ease_out_back(st, 1.18)
            stone_svg.append(
                f'<g transform="translate({sx},{sy}) rotate({rot}) scale({sc:.3f})">'
                f'<ellipse cx="2" cy="4" rx="{rx}" ry="{ry}" fill="#1d2625" opacity="0.32"/>'
                f'<ellipse cx="0" cy="0" rx="{rx}" ry="{ry}" fill="#d8c39e" stroke="#8c7355" stroke-width="1.5"/>'
                f'<ellipse cx="-3" cy="-2" rx="{rx * 0.65:.1f}" ry="{ry * 0.55:.1f}" fill="#eadbc0" opacity="0.65"/>'
                f'</g>'
            )

    flower_t = smoothstep(0.10, 0.48, progress)
    wildflowers = []
    fl_positions = [
        (158, 566, "#e06d53"), (198, 578, "#eab454"), (342, 552, "#f4e8c1"),
        (445, 544, "#e06d53"), (528, 552, "#eab454"), (584, 548, "#e06d53"),
        (1118, 556, "#eab454"), (1168, 568, "#e06d53"), (1208, 552, "#f4e8c1"),
    ]
    for idx, (fx, fy, fcol) in enumerate(fl_positions):
        ft = clamp(flower_t * 1.6 - idx * 0.08)
        if ft > 0.01:
            sc = ease_out_back(ft, 1.25)
            sway = math.sin(picture * 0.35 + idx) * 2.0
            wildflowers.append(
                f'<g transform="translate({fx},{fy}) rotate({sway:.1f}) scale({sc:.3f})">'
                f'<path d="M 0 0 Q -5 -12 -9 -20 M 0 0 Q 0 -14 1 -23 M 0 0 Q 6 -12 10 -19" stroke="#537a5a" stroke-width="1.8" fill="none" stroke-linecap="round"/>'
                f'<circle cx="-9" cy="-21" r="3.5" fill="{fcol}"/>'
                f'<circle cx="1" cy="-24" r="4" fill="{fcol}"/>'
                f'<circle cx="10" cy="-20" r="3.2" fill="#faecc8"/>'
                f'</g>'
            )

    return f"""
    <!-- Far Paper Ridge -->
    <g filter="url(#decklePaper)">
      <path d="M -20 475 Q 180 410 410 448 T 860 422 Q 1080 398 1300 445 L 1300 620 L -20 620 Z"
            fill="{hex_color(far_hill)}" stroke="#d9cbb0" stroke-opacity="0.28" stroke-width="1.3"/>
    </g>

    <!-- Mid Paper Hills with Distant Lights -->
    <g filter="url(#decklePaper)">
      <path d="M -20 508 Q 260 452 540 488 T 1040 462 Q 1180 452 1300 482 L 1300 625 L -20 625 Z"
            fill="{hex_color(mid_hill)}" stroke="#e8dcc4" stroke-opacity="0.32" stroke-width="1.4"/>
      <circle cx="515" cy="472" r="2.2" fill="#ffcf75" opacity="{0.25 + 0.65 * sky_phase:.2f}"/>
      <circle cx="528" cy="475" r="1.8" fill="#ffcf75" opacity="{0.25 + 0.65 * sky_phase:.2f}"/>
      <circle cx="1165" cy="466" r="2.2" fill="#ffcf75" opacity="{0.25 + 0.65 * sky_phase:.2f}"/>
    </g>

    <!-- Near Terraced Hill & Stitched Embroidery Contour -->
    <g filter="url(#decklePaper)">
      <path d="M -20 542 Q 220 494 520 526 T 980 512 Q 1150 508 1300 532 L 1300 640 L -20 640 Z"
            fill="{hex_color(near_hill)}" stroke="#f2e5cc" stroke-opacity="0.35" stroke-width="1.5"/>
      <path d="M 10 550 Q 220 504 520 534 T 980 520 Q 1150 516 1280 540"
            fill="none" stroke="#e9dabf" stroke-opacity="0.38" stroke-width="1.2" stroke-dasharray="6,5"/>
    </g>

    <!-- Foreground Meadow Sweep -->
    <g filter="url(#decklePaper)">
      <path d="M -20 568 Q 340 538 690 556 T 1300 558 L 1300 650 L -20 650 Z"
            fill="{hex_color(meadow_col)}" stroke="#f4e8cf" stroke-opacity="0.32" stroke-width="1.5"/>
    </g>

    <!-- Winding Paper Ribbon & Stepping Stones Path -->
    <g opacity="{smoothstep(0.01, 0.14, progress):.3f}">
      <path d="M 190 604 Q 360 568 530 574 T 780 578"
            fill="none" stroke="#7d6347" stroke-width="32" stroke-linecap="round" opacity="0.34"/>
      <path d="M 190 602 Q 360 566 530 572 T 780 576"
            fill="none" stroke="#c7a97e" stroke-width="24" stroke-linecap="round" opacity="0.78"/>
      <path d="M 190 602 Q 360 566 530 572 T 780 576"
            fill="none" stroke="#f2e4c8" stroke-width="1.3" stroke-dasharray="5,6" opacity="0.55"/>
    </g>
    {''.join(stone_svg)}
    {''.join(wildflowers)}
    """


def build_left_garden_svg(progress, sky_phase, picture):
    """Render the blossoming jacaranda/cherry tree, wrought-iron lamppost with '20 JAN 2022' sign, and string lights."""
    sway = math.sin(picture * 0.25) * 1.4
    tree_growth = smoothstep(0.02, 0.65, progress)

    blossom_coords = [
        (172, 378, "#f39c86", 7), (198, 346, "#fbead2", 8), (235, 330, "#ea7359", 9),
        (272, 340, "#f6b76b", 8), (308, 362, "#fbead2", 7), (154, 412, "#ea7359", 7),
        (214, 388, "#f6b76b", 8), (256, 372, "#fbead2", 9), (292, 395, "#f39c86", 8),
        (186, 426, "#fbead2", 7), (242, 415, "#ea7359", 8), (324, 388, "#f6b76b", 7),
        (225, 308, "#f39c86", 8), (266, 315, "#fbead2", 7),
    ]
    blossoms = []
    for idx, (bx, by, bcol, br) in enumerate(blossom_coords):
        bt = clamp(tree_growth * 1.55 - idx * 0.065)
        if bt > 0.02:
            sc = ease_out_back(bt, 1.3)
            blossoms.append(f'<g transform="translate({bx},{by}) scale({sc * 0.95:.3f})">')
            for pet in range(5):
                ang = pet * 72 + (idx * 17)
                blossoms.append(
                    f'<ellipse cx="0" cy="{-br * 0.58:.1f}" rx="{br * 0.46:.1f}" ry="{br * 0.62:.1f}" '
                    f'fill="{bcol}" stroke="#7a3e32" stroke-opacity="0.28" stroke-width="0.6" transform="rotate({ang})"/>'
                )
            blossoms.append(f'<circle cx="0" cy="0" r="{br * 0.24:.1f}" fill="#f7d070"/>')
            blossoms.append("</g>")

    lamp_glow = 0.35 + 0.65 * smoothstep(0.08, 0.55, sky_phase)
    sign_t = smoothstep(0.08, 0.15, progress)

    festoon_t = smoothstep(0.35, 0.46, progress)
    festoon_svg = []
    if festoon_t > 0.01:
        festoon_svg.append(f'<g opacity="{festoon_t:.3f}">')
        festoon_svg.append(
            '<path d="M 305 385 Q 350 412 395 402 Q 515 438 632 352" fill="none" stroke="#2c3e4c" stroke-width="1.6"/>'
        )
        bulb_pts = [
            (326, 396), (352, 403), (376, 404),
            (422, 410), (456, 414), (492, 413), (528, 406), (562, 394), (595, 378), (620, 362),
        ]
        for b_idx, (lx, ly) in enumerate(bulb_pts):
            flicker = 0.82 + 0.18 * math.sin(picture * 0.6 + b_idx * 1.1)
            bcol = "#ffd87a" if b_idx % 2 == 0 else "#ffae68"
            festoon_svg.append(
                f'<circle cx="{lx}" cy="{ly + 4}" r="11" fill="{bcol}" opacity="{0.34 * flicker:.3f}" filter="url(#softGlow)"/>'
                f'<path d="M {lx - 3} {ly + 1} L {lx + 3} {ly + 1} L {lx + 5} {ly + 8} L {lx - 5} {ly + 8} Z" '
                f'fill="{bcol}" opacity="{0.88 * flicker:.3f}"/>'
                f'<circle cx="{lx}" cy="{ly + 4}" r="3.2" fill="#fff9e2" opacity="{0.95 * flicker:.3f}"/>'
            )
        festoon_svg.append("</g>")

    return f"""
    <!-- Left Courtyard Blossoming Paper Tree -->
    <g filter="url(#paperShadow)" transform="translate(238,558) rotate({sway * 0.45:.2f}) translate(-238,-558)">
      <ellipse cx="238" cy="562" rx="78" ry="14" fill="#172426" opacity="0.38"/>
      <path d="M 222 560 C 224 510 230 465 226 420 C 212 392 185 375 168 364
               M 236 560 C 238 505 236 455 242 412 C 262 385 288 368 312 356
               M 234 445 C 234 405 235 368 236 335"
            fill="none" stroke="#5c4033" stroke-width="14" stroke-linecap="round"/>
      <path d="M 228 560 C 231 495 233 440 235 342
               M 232 426 C 210 398 188 380 168 364
               M 236 418 C 260 390 285 372 312 356"
            fill="none" stroke="#7d5846" stroke-width="6" stroke-linecap="round"/>

      <g transform="translate(238,372) rotate({sway:.2f}) translate(-238,-372)">
        <ellipse cx="188" cy="392" rx="54" ry="38" fill="#466d5b" stroke="#2c483c" stroke-width="1.5"/>
        <ellipse cx="286" cy="388" rx="56" ry="40" fill="#466d5b" stroke="#2c483c" stroke-width="1.5"/>
        <ellipse cx="236" cy="348" rx="68" ry="46" fill="#56826c" stroke="#355748" stroke-width="1.5"/>
        <ellipse cx="208" cy="376" rx="52" ry="36" fill="#68967c" stroke="#426955" stroke-width="1.2"/>
        <ellipse cx="268" cy="372" rx="52" ry="36" fill="#608d74" stroke="#426955" stroke-width="1.2"/>
        <ellipse cx="238" cy="332" rx="50" ry="34" fill="#76a488" stroke="#4c755f" stroke-width="1.2"/>
        {''.join(blossoms)}
      </g>
    </g>

    <!-- Vintage Wrought-Iron & Paper Garden Lamppost + Cozy Garden Bench -->
    <g>
      <ellipse cx="395" cy="566" rx="72" ry="16" fill="#f7c86a" opacity="{0.28 * lamp_glow:.3f}" filter="url(#softGlow)"/>
      <g filter="url(#paperShadowSm)" transform="translate(310, 542)">
        <rect x="-26" y="0" width="52" height="6" rx="1.5" fill="#9c6244" stroke="#3b2418" stroke-width="1.2"/>
        <rect x="-24" y="-11" width="48" height="8" rx="1.5" fill="#b37452" stroke="#3b2418" stroke-width="1.2"/>
        <line x1="-20" y1="6" x2="-22" y2="16" stroke="#283845" stroke-width="2.5" stroke-linecap="round"/>
        <line x1="20" y1="6" x2="22" y2="16" stroke="#283845" stroke-width="2.5" stroke-linecap="round"/>
      </g>
      <circle cx="395" cy="402" r="54" fill="url(#lampRadial)" opacity="{lamp_glow:.3f}"/>
      <path d="M 387 562 L 403 562 L 399 542 L 391 542 Z" fill="#283845" stroke="#162029" stroke-width="1.2"/>
      <line x1="395" y1="544" x2="395" y2="416" stroke="#283845" stroke-width="4.5"/>
      <line x1="386" y1="432" x2="404" y2="432" stroke="#283845" stroke-width="3" stroke-linecap="round"/>
      <!-- Hanging Date Signpost on Lamppost ('20 JAN 2022') -->
      <g opacity="{sign_t:.3f}" filter="url(#paperShadowSm)">
        <line x1="395" y1="444" x2="458" y2="444" stroke="#283845" stroke-width="2.2" stroke-linecap="round"/>
        <rect x="401" y="447" width="54" height="15" rx="2" fill="#f7ebd2" stroke="#8c6239" stroke-width="1.2"/>
        <text x="428" y="457.5" text-anchor="middle" font-family="Avenir, Helvetica, sans-serif" font-weight="700" font-size="7.5" fill="#253849" letter-spacing="0.4">20 JAN ’22</text>
      </g>
      <polygon points="384,416 406,416 410,394 380,394" fill="#fff0bf" stroke="#283845" stroke-width="2.2"/>
      <line x1="395" y1="416" x2="395" y2="394" stroke="#283845" stroke-width="1.4"/>
      <polygon points="377,394 413,394 395,380" fill="#1e2d3a" stroke="#162029" stroke-width="1.5"/>
      <circle cx="395" cy="378" r="2.5" fill="#d9a74a"/>
    </g>

    {''.join(festoon_svg)}
    """


def build_window_unit(x, y, w, h, lit_amount, has_flowerbox=True, interior_kind="curtains", picture=0):
    """Build a multi-layered architectural window where interior glow sits BEHIND curtains and muntin bars."""
    lit = clamp(lit_amount)
    dark_glass = (52, 82, 102)
    warm_glass = (252, 206, 104)
    glass_col = hex_color(lerp_color(dark_glass, warm_glass, lit))
    inner_glow_col = hex_color(lerp_color((72, 110, 128), (255, 240, 184), lit))

    grad_id = f"winGrad_{x}_{y}"
    clip_id = f"winClip_{x}_{y}"

    interior_svg = []
    if interior_kind == "mobile" and lit > 0.15:
        sway = math.sin(picture * 0.4) * 3.0
        mx = x + w * 0.5
        my = y + 6
        interior_svg.append(
            f'<g transform="translate({mx:.1f},{my:.1f}) rotate({sway:.2f}) translate({-mx:.1f},{-my:.1f})" opacity="{smoothstep(0.15, 0.6, lit):.3f}">'
            f'<line x1="{mx:.1f}" y1="{y}" x2="{mx:.1f}" y2="{y + 15}" stroke="#5c3d2e" stroke-width="1.4"/>'
            f'<path d="M {mx - 16:.1f} {y + 17} Q {mx:.1f} {y + 11} {mx + 16:.1f} {y + 17}" fill="none" stroke="#5c3d2e" stroke-width="1.5"/>'
            f'<line x1="{mx - 13:.1f}" y1="{y + 16}" x2="{mx - 13:.1f}" y2="{y + 29}" stroke="#5c3d2e" stroke-width="1"/>'
            f'<line x1="{mx:.1f}" y1="{y + 14}" x2="{mx:.1f}" y2="{y + 33}" stroke="#5c3d2e" stroke-width="1"/>'
            f'<line x1="{mx + 13:.1f}" y1="{y + 16}" x2="{mx + 13:.1f}" y2="{y + 28}" stroke="#5c3d2e" stroke-width="1"/>'
            f'<circle cx="{mx - 13:.1f}" cy="{y + 31}" r="3.8" fill="#ce5b49"/>'
            f'<polygon points="{mx:.1f},{y + 29} {mx + 4.0:.1f},{y + 37} {mx - 4.0:.1f},{y + 37}" fill="#2d537b"/>'
            f'<circle cx="{mx + 13:.1f}" cy="{y + 30}" r="3.6" fill="#5b8472"/>'
            f'</g>'
        )
    elif interior_kind == "boat" and lit > 0.15:
        rock = math.sin(picture * 0.38 + 1.2) * 3.5
        bx = x + w * 0.5
        by = y + h * 0.66
        interior_svg.append(
            f'<g transform="translate({bx:.1f},{by:.1f}) rotate({rock:.2f}) translate({-bx:.1f},{-by:.1f})" opacity="{smoothstep(0.15, 0.6, lit):.3f}">'
            f'<polygon points="{bx - 14:.1f},{by} {bx + 14:.1f},{by} {bx + 10:.1f},{by + 7} {bx - 10:.1f},{by + 7}" fill="#2d537b"/>'
            f'<polygon points="{bx:.1f},{by - 14} {bx:.1f},{by - 1} {bx + 10:.1f},{by - 1}" fill="#ce5b49"/>'
            f'<polygon points="{bx - 1:.1f},{by - 11} {bx - 1:.1f},{by - 1} {bx - 9:.1f},{by - 1}" fill="#5b8472"/>'
            f'</g>'
        )

    curtain_col = "#c95b48" if interior_kind == "curtains" else "#d98a4e"
    curtains_svg = (
        f'<path d="M {x} {y} L {x + w * 0.28:.1f} {y} Q {x + w * 0.22:.1f} {y + h * 0.55:.1f} {x} {y + h * 0.78:.1f} Z" fill="{curtain_col}" opacity="0.88"/>'
        f'<path d="M {x + w} {y} L {x + w * 0.72:.1f} {y} Q {x + w * 0.78:.1f} {y + h * 0.55:.1f} {x + w} {y + h * 0.78:.1f} Z" fill="{curtain_col}" opacity="0.88"/>'
    )

    flowerbox_svg = ""
    if has_flowerbox:
        fb_y = y + h + 2
        flowerbox_svg = f"""
        <rect x="{x - 6}" y="{y + h - 2}" width="{w + 12}" height="6" rx="1.5" fill="#e6d6b5" stroke="#2c3e50" stroke-width="1.5"/>
        <polygon points="{x - 3},{fb_y + 2} {x + w + 3},{fb_y + 2} {x + w - 1},{fb_y + 15} {x + 1},{fb_y + 15}"
                 fill="#9c6244" stroke="#422a1d" stroke-width="1.5"/>
        <ellipse cx="{x + w * 0.22:.1f}" cy="{fb_y + 1}" rx="10" ry="6" fill="#4f7c5e"/>
        <ellipse cx="{x + w * 0.50:.1f}" cy="{fb_y}" rx="12" ry="7" fill="#63926f"/>
        <ellipse cx="{x + w * 0.78:.1f}" cy="{fb_y + 1}" rx="10" ry="6" fill="#4f7c5e"/>
        <circle cx="{x + w * 0.24:.1f}" cy="{fb_y}" r="3.8" fill="#e26b54"/>
        <circle cx="{x + w * 0.46:.1f}" cy="{fb_y - 2}" r="4.2" fill="#f3c15a"/>
        <circle cx="{x + w * 0.62:.1f}" cy="{fb_y + 1}" r="3.6" fill="#faecc8"/>
        <circle cx="{x + w * 0.80:.1f}" cy="{fb_y - 1}" r="3.8" fill="#e26b54"/>
        """

    return f"""
    <defs>
      <radialGradient id="{grad_id}" cx="50%" cy="55%" r="65%">
        <stop offset="0%" stop-color="{inner_glow_col}"/>
        <stop offset="100%" stop-color="{glass_col}"/>
      </radialGradient>
      <clipPath id="{clip_id}">
        <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3"/>
      </clipPath>
    </defs>
    <rect x="{x - 14}" y="{y - 14}" width="{w + 28}" height="{h + 28}" rx="14"
          fill="#ffcf6e" opacity="{lit * 0.36:.3f}" filter="url(#softGlow)"/>

    <rect x="{x - 14}" y="{y + 2}" width="12" height="{h - 4}" rx="2" fill="#3a6368" stroke="#223843" stroke-width="1.5"/>
    <rect x="{x + w + 2}" y="{y + 2}" width="12" height="{h - 4}" rx="2" fill="#3a6368" stroke="#223843" stroke-width="1.5"/>

    <g clip-path="url(#{clip_id})">
      <rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#{grad_id})"/>
      {''.join(interior_svg)}
      {curtains_svg}
      <polygon points="{x + 6},{y + h} {x + 22},{y} {x + 32},{y} {x + 16},{y + h}" fill="#ffffff" opacity="0.14"/>
    </g>

    <line x1="{x + w / 2:.1f}" y1="{y}" x2="{x + w / 2:.1f}" y2="{y + h}" stroke="#f7ebd2" stroke-width="3.0"/>
    <line x1="{x}" y1="{y + h / 2:.1f}" x2="{x + w}" y2="{y + h / 2:.1f}" stroke="#f7ebd2" stroke-width="3.0"/>
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="none" stroke="#243748" stroke-width="3.0"/>
    <rect x="{x - 3}" y="{y - 5}" width="{w + 6}" height="5" rx="1" fill="#e6d6b5" stroke="#243748" stroke-width="1.4"/>
    {flowerbox_svg}
    """


def build_house_svg(progress, sky_phase, picture):
    """Build the multi-story artisan paper villa with 4 glowing windows, marriage date stone, and nursery dormers."""
    parts = []

    ground_house_t = smoothstep(0.18, 0.32, progress)
    if ground_house_t > 0.01:
        clapboards = []
        for cy in range(352, 534, 16):
            clapboards.append(
                f'<line x1="632" y1="{cy}" x2="1048" y2="{cy}" stroke="#d6c5a3" stroke-width="1.2" opacity="0.7"/>'
            )
        stone_joints = []
        for sx in range(650, 1040, 48):
            stone_joints.append(
                f'<line x1="{sx}" y1="534" x2="{sx}" y2="568" stroke="#5a4032" stroke-width="1.4" opacity="0.55"/>'
            )

        ground_lit = smoothstep(0.35, 0.46, progress)
        left_win = build_window_unit(664, 384, 72, 78, ground_lit, has_flowerbox=True, interior_kind="curtains", picture=picture)
        right_win = build_window_unit(944, 384, 72, 78, ground_lit, has_flowerbox=True, interior_kind="curtains", picture=picture)
        door_glow = smoothstep(0.84, 0.96, progress)
        marriage_plaque_op = smoothstep(0.50, 0.60, progress)

        parts.append(f"""
        <g {pop_transform(840, 550, ground_house_t, slide_y=32)} filter="url(#paperShadow)">
          <ellipse cx="895" cy="572" rx="205" ry="18" fill="#121d24" opacity="0.42"/>
          <rect x="630" y="336" width="420" height="200" fill="url(#wallPaperGrad)" stroke="#253849" stroke-width="2.6"/>
          {''.join(clapboards)}
          <rect x="630" y="336" width="16" height="200" fill="#e5d4b3" stroke="#253849" stroke-width="1.8"/>
          <rect x="1034" y="336" width="16" height="200" fill="#e5d4b3" stroke="#253849" stroke-width="1.8"/>
          <rect x="630" y="336" width="420" height="10" fill="#253849" opacity="0.18"/>
          <rect x="618" y="534" width="444" height="34" rx="3" fill="#b88458" stroke="#3b2b22" stroke-width="2.2"/>
          <line x1="618" y1="548" x2="1062" y2="548" stroke="#5a4032" stroke-width="1.4" opacity="0.65"/>
          {''.join(stone_joints)}

          {left_win}
          {right_win}

          <g filter="url(#paperShadowSm)">
            <polygon points="790,536 890,536 930,582 750,582" fill="#ffcf6e" opacity="{0.38 * ground_lit:.3f}" filter="url(#softGlow)"/>
            <rect x="796" y="408" width="88" height="128" rx="4" fill="#e6d6b5" stroke="#243748" stroke-width="2.4"/>
            <path d="M 804 434 A 36 26 0 0 1 876 434 Z"
                  fill="{hex_color(lerp_color((64, 98, 116), (255, 214, 112), ground_lit))}" stroke="#243748" stroke-width="2.2"/>
            <line x1="840" y1="408" x2="840" y2="434" stroke="#f7ebd2" stroke-width="2"/>
            <line x1="816" y1="416" x2="840" y2="434" stroke="#f7ebd2" stroke-width="1.6"/>
            <line x1="864" y1="416" x2="840" y2="434" stroke="#f7ebd2" stroke-width="1.6"/>
            <rect x="804" y="436" width="72" height="98" fill="#2d4c63" stroke="#1c3142" stroke-width="2.2"/>
            <rect x="812" y="444" width="24" height="36" rx="2" fill="#243f54" stroke="#f3e4c6" stroke-opacity="0.35" stroke-width="1"/>
            <rect x="844" y="444" width="24" height="36" rx="2" fill="#243f54" stroke="#f3e4c6" stroke-opacity="0.35" stroke-width="1"/>
            <rect x="812" y="488" width="24" height="36" rx="2" fill="#243f54" stroke="#f3e4c6" stroke-opacity="0.35" stroke-width="1"/>
            <rect x="844" y="488" width="24" height="36" rx="2" fill="#243f54" stroke="#f3e4c6" stroke-opacity="0.35" stroke-width="1"/>
            <circle cx="866" cy="486" r="3.8" fill="#eab354" stroke="#3b2816" stroke-width="1"/>
            <rect x="804" y="436" width="72" height="98" fill="#ffcf6e" opacity="{door_glow * 0.25:.3f}"/>

            <!-- Marriage Keystone Date Plaque above Front Door ('EST · 26 JAN 2023') -->
            <g opacity="{marriage_plaque_op:.3f}">
              <rect x="788" y="383" width="104" height="19" rx="3" fill="#2c1d17" stroke="#d4a048" stroke-width="1.4"/>
              <text x="840" y="395.5" text-anchor="middle" font-family="Avenir, Helvetica, sans-serif" font-weight="700" font-size="8.5" fill="#f7e4bc" letter-spacing="1.0">EST · 26 JAN 2023</text>
            </g>
          </g>

          <g filter="url(#paperShadowSm)">
            <rect x="774" y="536" width="132" height="11" rx="2" fill="#d9c6a3" stroke="#3b2b22" stroke-width="1.8"/>
            <rect x="764" y="547" width="152" height="11" rx="2" fill="#cbb58e" stroke="#3b2b22" stroke-width="1.8"/>
            <rect x="754" y="558" width="172" height="12" rx="2" fill="#bca379" stroke="#3b2b22" stroke-width="1.8"/>
          </g>
        </g>
        """)

    roof_t = smoothstep(0.20, 0.33, progress)
    chimney_t = smoothstep(0.49, 0.59, progress)
    if roof_t > 0.01:
        shingle_rows = []
        for ry in range(186, 342, 18):
            shingle_rows.append(
                f'<line x1="585" y1="{ry}" x2="1095" y2="{ry}" stroke="#1b3552" stroke-width="2.0" opacity="0.65"/>'
                f'<line x1="585" y1="{ry - 1}" x2="1095" y2="{ry - 1}" stroke="#7aa2c4" stroke-width="1.0" opacity="0.32"/>'
            )
            offset = 17 if ((ry // 18) % 2 == 0) else 0
            for rx in range(590 + offset, 1090, 34):
                shingle_rows.append(
                    f'<path d="M {rx} {ry - 18} L {rx} {ry - 4} Q {rx + 17} {ry + 4} {rx + 34} {ry - 4}" '
                    f'fill="none" stroke="#172e47" stroke-width="1.2" opacity="0.5"/>'
                )

        smoke_vis = smoothstep(0.52, 0.62, progress)
        smoke_svg = []
        if smoke_vis > 0.01:
            for s_idx in range(4):
                phase = ((picture * 0.12) + s_idx * 0.25) % 1.0
                sy = 148 - phase * 92
                sx = 998 + math.sin(phase * 5.0 + s_idx) * 13 + phase * 18
                sr = 10 + phase * 15
                sop = smoke_vis * math.sin(phase * math.pi) * 0.48
                smoke_svg.append(
                    f'<ellipse cx="{sx:.1f}" cy="{sy:.1f}" rx="{sr * 1.15:.1f}" ry="{sr * 0.85:.1f}" '
                    f'fill="#f2e6cf" opacity="{sop:.3f}" filter="url(#softGlow)"/>'
                )

        chimney_svg = ""
        if chimney_t > 0.01:
            chimney_svg = f"""
            <g {pop_transform(997, 260, chimney_t, slide_y=24)}>
              <rect x="974" y="158" width="46" height="122" fill="#c85a48" stroke="#362420" stroke-width="2.2"/>
              <rect x="968" y="150" width="58" height="10" rx="2" fill="#e0745e" stroke="#362420" stroke-width="2.0"/>
              <line x1="974" y1="180" x2="1020" y2="180" stroke="#87382b" stroke-width="1.4"/>
              <line x1="974" y1="202" x2="1020" y2="202" stroke="#87382b" stroke-width="1.4"/>
              <line x1="974" y1="224" x2="1020" y2="224" stroke="#87382b" stroke-width="1.4"/>
            </g>
            """

        parts.append(f"""
        {''.join(smoke_svg)}
        <g {pop_transform(840, 340, roof_t, slide_y=-24)} filter="url(#paperShadow)">
          {chimney_svg}
          <defs>
            <clipPath id="roofClip">
              <polygon points="588,342 840,160 1092,342"/>
            </clipPath>
            <linearGradient id="roofGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#386491"/>
              <stop offset="55%" stop-color="#294c72"/>
              <stop offset="100%" stop-color="#1e3957"/>
            </linearGradient>
          </defs>
          <g clip-path="url(#roofClip)">
            <polygon points="588,342 840,160 1092,342" fill="url(#roofGrad)"/>
            {''.join(shingle_rows)}
          </g>
          <polygon points="588,342 840,160 1092,342" fill="none" stroke="#1b3149" stroke-width="3.5" stroke-linejoin="round"/>
          <polyline points="594,342 840,165 1086,342" fill="none" stroke="#f3e5c8" stroke-width="2.0" opacity="0.82"/>
          <circle cx="840" cy="158" r="5" fill="#e2a84b" stroke="#253849" stroke-width="1.5"/>
        </g>
        """)

    wedding_t = smoothstep(0.49, 0.59, progress)
    if wedding_t > 0.01:
        bunting_flags = []
        flag_colors = ["#ce5b49", "#e6a947", "#5b8c71", "#f4e6c6"]
        for i in range(13):
            fx = 642 + i * 30
            sag = math.sin((i / 12.0) * math.pi) * 14
            fy = 344 + sag
            fcol = flag_colors[i % len(flag_colors)]
            bunting_flags.append(
                f'<polygon points="{fx},{fy} {fx + 22},{fy} {fx + 11},{fy + 21}" '
                f'fill="{fcol}" stroke="#2b3a42" stroke-width="1.0"/>'
            )
        parts.append(f"""
        <g {pop_transform(840, 355, wedding_t, slide_y=-14)}>
          <path d="M 636 344 Q 840 372 1044 344" fill="none" stroke="#8c3b2b" stroke-width="2.0"/>
          {''.join(bunting_flags)}
          <circle cx="904" cy="436" r="28" fill="url(#lampRadial)" opacity="0.85"/>
          <line x1="892" y1="432" x2="904" y2="432" stroke="#243748" stroke-width="2.5"/>
          <polygon points="897,432 911,432 909,448 899,448" fill="#ffe89e" stroke="#243748" stroke-width="1.8"/>
        </g>
        """)

    pergola_t = smoothstep(0.51, 0.61, progress)
    if pergola_t > 0.01:
        sway = math.sin(picture * 0.32) * 2.0
        parts.append(f"""
        <g {pop_transform(1105, 560, pergola_t, slide_y=26)} filter="url(#paperShadowSm)">
          <rect x="1058" y="548" width="108" height="20" rx="2" fill="#a8774e" stroke="#3b2b22" stroke-width="1.8"/>
          <rect x="1066" y="408" width="8" height="140" fill="#7c5038" stroke="#382216" stroke-width="1.5"/>
          <rect x="1138" y="408" width="8" height="140" fill="#7c5038" stroke="#382216" stroke-width="1.5"/>
          <rect x="1046" y="402" width="112" height="8" rx="2" fill="#946246" stroke="#382216" stroke-width="1.6"/>
          <rect x="1054" y="395" width="98" height="6" rx="1.5" fill="#ab7556" stroke="#382216" stroke-width="1.3"/>
          <path d="M 1138 540 Q 1128 495 1142 455 Q 1132 420 1105 404 Q 1078 400 1064 418"
                fill="none" stroke="#4b785c" stroke-width="4" stroke-linecap="round"/>
          <circle cx="1138" cy="468" r="4.5" fill="#e06b54"/>
          <circle cx="1128" cy="432" r="4.8" fill="#f3c15a"/>
          <circle cx="1104" cy="405" r="5.0" fill="#e06b54"/>
          <circle cx="1078" cy="408" r="4.5" fill="#faecc8"/>
          <g transform="translate(1104,410) rotate({sway:.2f}) translate(-1104,-410)">
            <line x1="1104" y1="410" x2="1104" y2="432" stroke="#283845" stroke-width="1.6"/>
            <circle cx="1104" cy="440" r="24" fill="url(#lampRadial)" opacity="0.85"/>
            <polygon points="1097,432 1111,432 1109,448 1099,448" fill="#ffe89e" stroke="#243748" stroke-width="1.6"/>
          </g>
          <polygon points="1168,524 1198,524 1193,568 1173,568" fill="#b86944" stroke="#4a2a1b" stroke-width="1.8"/>
          <rect x="1165" y="518" width="36" height="8" rx="2" fill="#ce7952" stroke="#4a2a1b" stroke-width="1.5"/>
          <ellipse cx="1183" cy="484" rx="25" ry="30" fill="#48755d" stroke="#294737" stroke-width="1.6"/>
          <ellipse cx="1172" cy="494" rx="19" ry="21" fill="#5b8c71" stroke="#294737" stroke-width="1.4"/>
          <ellipse cx="1194" cy="492" rx="17" ry="21" fill="#528067" stroke="#294737" stroke-width="1.4"/>
          <circle cx="1176" cy="476" r="3.6" fill="#f0b654"/>
          <circle cx="1192" cy="488" r="3.6" fill="#f0b654"/>
        </g>
        """)

    # Left Roof Dormer — Window #3: Daivik's Nursery (03 Aug 2024)
    daivik_t = smoothstep(0.64, 0.74, progress)
    if daivik_t > 0.01:
        daivik_win = build_window_unit(741, 262, 50, 52, daivik_t, has_flowerbox=False, interior_kind="mobile", picture=picture)
        parts.append(f"""
        <g {pop_transform(766, 316, daivik_t, slide_y=20)} filter="url(#paperShadowSm)">
          <rect x="730" y="254" width="72" height="70" fill="#f7ebd2" stroke="#243748" stroke-width="2.2"/>
          <polygon points="722,256 766,220 810,256" fill="#c85a48" stroke="#243748" stroke-width="2.2" stroke-linejoin="round"/>
          <polyline points="727,256 766,225 805,256" fill="none" stroke="#f7ebd2" stroke-width="1.5"/>
          {daivik_win}
          <rect x="727" y="317" width="78" height="14" rx="2" fill="#2c1d17" stroke="#d4a048" stroke-width="1.1"/>
          <text x="766" y="326.8" text-anchor="middle" font-family="Avenir, Helvetica, sans-serif" font-weight="700" font-size="7.2" fill="#f7e4bc" letter-spacing="0.6">03 AUG 2024</text>
        </g>
        """)

    # Right Roof Dormer — Window #4: Deeyan's Nursery (09 Sep 2026)
    deeyan_t = smoothstep(0.78, 0.88, progress)
    if deeyan_t > 0.01:
        deeyan_win = build_window_unit(889, 262, 50, 52, deeyan_t, has_flowerbox=False, interior_kind="boat", picture=picture)
        parts.append(f"""
        <g {pop_transform(914, 316, deeyan_t, slide_y=20)} filter="url(#paperShadowSm)">
          <rect x="878" y="254" width="72" height="70" fill="#f7ebd2" stroke="#243748" stroke-width="2.2"/>
          <polygon points="870,256 914,220 958,256" fill="#c85a48" stroke="#243748" stroke-width="2.2" stroke-linejoin="round"/>
          <polyline points="875,256 914,225 953,256" fill="none" stroke="#f7ebd2" stroke-width="1.5"/>
          {deeyan_win}
          <rect x="875" y="317" width="78" height="14" rx="2" fill="#2c1d17" stroke="#d4a048" stroke-width="1.1"/>
          <text x="914" y="326.8" text-anchor="middle" font-family="Avenir, Helvetica, sans-serif" font-weight="700" font-size="7.2" fill="#f7e4bc" letter-spacing="0.6">09 SEP 2026</text>
        </g>
        """)

    return "\n".join(parts)


def build_characters_svg(progress, stage_index, picture):
    """Render graceful storybook paper-cutout silhouettes."""
    char_vis = smoothstep(0.08, 0.14, progress)
    if char_vis <= 0.01:
        return ""

    bob = math.sin(picture * 0.4) * 1.2
    move_to_porch = smoothstep(0.32, 0.56, progress)
    base_x = 445 + move_to_porch * 367
    base_y = 570 - move_to_porch * 6 + bob

    has_daivik = progress >= 0.68
    has_deeyan = progress >= 0.82

    svg = [f'<g opacity="{char_vis:.3f}" transform="translate({base_x:.1f},{base_y:.1f})" filter="url(#paperShadowSm)">']
    svg.append('<ellipse cx="26" cy="4" rx="54" ry="9" fill="#121c24" opacity="0.42"/>')

    # Aravind
    svg.append("""
      <g transform="translate(0,0)">
        <path d="M -5 -22 L -6 2 L -2 2 L 0 -22 Z" fill="#1d2f40"/>
        <path d="M 3 -22 L 4 2 L 8 2 L 7 -22 Z" fill="#1d2f40"/>
        <path d="M -10 -54 C -11 -42 -9 -26 -8 -20 L 10 -20 C 11 -26 12 -42 10 -54 C 6 -58 -6 -58 -10 -54 Z"
              fill="#264663" stroke="#f7dfb0" stroke-width="1.1"/>
        <path d="M 8 -50 Q 16 -40 21 -34" fill="none" stroke="#264663" stroke-width="4.5" stroke-linecap="round"/>
        <circle cx="0" cy="-65" r="7.8" fill="#f5dfb8" stroke="#243748" stroke-width="1.3"/>
        <path d="M -8 -66 C -8 -74 6 -75 8 -67 C 5 -69 -4 -69 -8 -66 Z" fill="#1c2833"/>
      </g>
    """)

    # Sanjana
    sanjana_x = 34 if not has_daivik else 48
    svg.append(f"""
      <g transform="translate({sanjana_x},0)">
        <path d="M -8 -48 C -11 -32 -15 -12 -17 2 L 17 2 C 14 -12 10 -32 8 -48 C 4 -53 -4 -53 -8 -48 Z"
              fill="#c85646" stroke="#f9e3b4" stroke-width="1.2"/>
        <path d="M -15 -3 Q 0 0 15 -3" fill="none" stroke="#f4c76b" stroke-width="1.8"/>
        <path d="M -7 -45 Q -13 -37 -17 -33" fill="none" stroke="#c85646" stroke-width="4" stroke-linecap="round"/>
        <circle cx="0" cy="-59" r="7.4" fill="#f5dfb8" stroke="#243748" stroke-width="1.3"/>
        <path d="M -7 -60 C -7 -69 8 -69 8 -58 C 10 -52 9 -44 6 -42 C 6 -50 4 -57 -7 -60 Z" fill="#1c2833"/>
      </g>
    """)

    # Daivik
    if has_daivik:
        d_sc = ease_out_back(smoothstep(0.66, 0.74, progress), 1.25)
        svg.append(f"""
          <g transform="translate(24,2) scale({d_sc:.3f})">
            <path d="M -4 -14 L -4 0 L -1 0 L 0 -14 Z" fill="#1d2f40"/>
            <path d="M 1 -14 L 2 0 L 5 0 L 4 -14 Z" fill="#1d2f40"/>
            <path d="M -7 -32 C -7 -24 -6 -16 -5 -12 L 6 -12 C 7 -16 7 -24 6 -32 Z"
                  fill="#56826c" stroke="#f9e3b4" stroke-width="1.0"/>
            <path d="M -6 -29 L -12 -34 M 6 -29 L 12 -33" stroke="#56826c" stroke-width="3" stroke-linecap="round"/>
            <circle cx="0" cy="-39" r="5.6" fill="#f5dfb8" stroke="#243748" stroke-width="1.2"/>
            <path d="M -5 -41 C -4 -46 4 -46 5 -40 Z" fill="#1c2833"/>
          </g>
        """)

    # Deeyan
    if has_deeyan:
        dy_sc = ease_out_back(smoothstep(0.80, 0.88, progress), 1.25)
        svg.append(f"""
          <g transform="translate({sanjana_x + 22},3) scale({dy_sc:.3f})">
            <path d="M -3 -11 L -3 0 L 3 0 L 3 -11 Z" fill="#1d2f40"/>
            <path d="M -6 -26 C -6 -19 -5 -12 -4 -9 L 5 -9 C 6 -12 6 -19 5 -26 Z"
                  fill="#e2a547" stroke="#fff0c9" stroke-width="1.0"/>
            <path d="M -5 -23 L -11 -28" stroke="#e2a547" stroke-width="2.8" stroke-linecap="round"/>
            <circle cx="0" cy="-32" r="4.8" fill="#f5dfb8" stroke="#243748" stroke-width="1.1"/>
            <path d="M -4 -33 C -3 -38 3 -38 4 -33 Z" fill="#1c2833"/>
          </g>
        """)

    svg.append("</g>")
    return "\n".join(svg)


def build_letterpress_placard_svg(stage, stage_index, within):
    """Render a museum-grade letterpress story card with prominent event dates & milestone ledger."""
    card_in = ease_out_back(clamp(within / 0.18), 1.08)
    dy = (1.0 - card_in) * -8.0

    badge_date = xml_escape(stage["badge_date"])
    event_tag = xml_escape(stage["event_tag"])
    title_text = xml_escape(stage["title"])
    sub_text = xml_escape(stage["subtitle"])
    footer_text = xml_escape(stage["footer"])

    is_finale = stage.get("finale", False)
    if is_finale:
        body_block = f"""
        <text x="96" y="114" font-family="Georgia, serif" font-size="30" font-weight="bold" fill="#1e3042">
          {title_text}
        </text>
        <!-- Three Milestone Date Badges for Marriage, Daivik, and Deeyan -->
        <g transform="translate(96, 127)">
          <rect x="0" y="0" width="114" height="32" rx="4" fill="#efe0be" stroke="#b88e48" stroke-width="1.1"/>
          <text x="57" y="13" text-anchor="middle" font-family="Avenir, Helvetica, sans-serif" font-size="8.0" font-weight="700" fill="#8c3b2b" letter-spacing="0.9">MARRIED</text>
          <text x="57" y="25" text-anchor="middle" font-family="Georgia, serif" font-size="11.0" font-weight="bold" fill="#1e3042">26 Jan 2023</text>

          <rect x="122" y="0" width="114" height="32" rx="4" fill="#efe0be" stroke="#b88e48" stroke-width="1.1"/>
          <text x="179" y="13" text-anchor="middle" font-family="Avenir, Helvetica, sans-serif" font-size="8.0" font-weight="700" fill="#2d537b" letter-spacing="0.9">DAIVIK BORN</text>
          <text x="179" y="25" text-anchor="middle" font-family="Georgia, serif" font-size="11.0" font-weight="bold" fill="#1e3042">03 Aug 2024</text>

          <rect x="244" y="0" width="114" height="32" rx="4" fill="#efe0be" stroke="#b88e48" stroke-width="1.1"/>
          <text x="301" y="13" text-anchor="middle" font-family="Avenir, Helvetica, sans-serif" font-size="8.0" font-weight="700" fill="#466d5b" letter-spacing="0.9">DEEYAN BORN</text>
          <text x="301" y="25" text-anchor="middle" font-family="Georgia, serif" font-size="11.0" font-weight="bold" fill="#1e3042">09 Sep 2026</text>
        </g>
        """
    else:
        body_block = f"""
        <text x="96" y="118" font-family="Georgia, serif" font-size="32" font-weight="bold" fill="#1e3042">
          {title_text}
        </text>
        <text x="96" y="148" font-family="Georgia, serif" font-style="italic" font-size="15.5" fill="#465359">
          {sub_text}
        </text>
        """

    return f"""
    <g transform="translate(0,{dy:.2f})" filter="url(#paperShadow)">
      <rect x="52" y="34" width="458" height="184" rx="7" fill="url(#cardPaperGrad)" stroke="#c8b38a" stroke-width="1.8"/>
      <rect x="61" y="43" width="440" height="166" rx="4" fill="none" stroke="#c49a52" stroke-opacity="0.55" stroke-width="1.1"/>
      <line x1="78" y1="58" x2="78" y2="196" stroke="#c85a48" stroke-width="2.8" stroke-linecap="round"/>

      <circle cx="67" cy="49" r="2.6" fill="#d4a048" stroke="#6e4e1e" stroke-width="0.8"/>
      <circle cx="495" cy="49" r="2.6" fill="#d4a048" stroke="#6e4e1e" stroke-width="0.8"/>
      <circle cx="67" cy="203" r="2.6" fill="#d4a048" stroke="#6e4e1e" stroke-width="0.8"/>
      <circle cx="495" cy="203" r="2.6" fill="#d4a048" stroke="#6e4e1e" stroke-width="0.8"/>

      <!-- Prominent Embossed Date Stamp Pill at Top of Card -->
      <rect x="94" y="54" width="144" height="22" rx="4" fill="#c85a48"/>
      <text x="166" y="68.5" text-anchor="middle" font-family="Avenir, Helvetica, sans-serif" font-size="10.0" font-weight="700" letter-spacing="1.0" fill="#fff8ea">
        {badge_date}
      </text>
      <text x="248" y="68.5" font-family="Avenir, Helvetica, sans-serif" font-size="9.5" font-weight="700" letter-spacing="1.0" fill="#2d537b">
        {event_tag}
      </text>

      <!-- Chapter Number Medallion -->
      <circle cx="472" cy="68" r="15" fill="#f2e2be" stroke="#c49a52" stroke-width="1.4"/>
      <text x="472" y="72.5" text-anchor="middle" font-family="Avenir, Helvetica, sans-serif" font-size="11.0" font-weight="700" fill="#9c6b2e">
        {stage_index + 1:02d}
      </text>

      {body_block}

      <line x1="96" y1="171" x2="462" y2="171" stroke="#d4bc94" stroke-width="1"/>
      <text x="96" y="190" font-family="Avenir, Helvetica, sans-serif" font-size="10.0" font-weight="600" letter-spacing="1.3" fill="#8c6239">
        {footer_text}
      </text>
    </g>
    """


def build_stage_apron_and_keepsake_svg(stage, stage_index, progress, within):
    """Render the walnut theater stage apron, chapter keepsake emblem, and dated milestone timeline."""
    prop = stage["prop"]
    prop_in = ease_out_back(clamp(within / 0.25), 1.25)

    keep_svg = []
    if prop == "letter":
        keep_svg.append("""
          <rect x="-26" y="-16" width="52" height="32" rx="3" fill="#faefd8" stroke="#2c3e50" stroke-width="1.6"/>
          <polyline points="-25,-15 0,4 25,-15" fill="none" stroke="#c85a48" stroke-width="1.8"/>
          <circle cx="0" cy="3" r="5.5" fill="#c85a48" stroke="#7d2e22" stroke-width="1"/>
        """)
    elif prop == "lantern":
        keep_svg.append("""
          <circle cx="0" cy="0" r="20" fill="#ffd97d" opacity="0.35"/>
          <polygon points="-9,-11 9,-11 12,11 -12,11" fill="#ffe8a3" stroke="#243748" stroke-width="1.8"/>
          <polygon points="-13,-11 13,-11 0,-20" fill="#243748"/>
          <rect x="-11" y="11" width="22" height="4.5" rx="1" fill="#243748"/>
        """)
    elif prop == "keys":
        keep_svg.append("""
          <circle cx="-11" cy="0" r="9" fill="none" stroke="#e2a547" stroke-width="3.2"/>
          <circle cx="-11" cy="0" r="3.5" fill="none" stroke="#9c6b26" stroke-width="1.2"/>
          <line x1="-2" y1="0" x2="22" y2="0" stroke="#e2a547" stroke-width="3.2" stroke-linecap="round"/>
          <line x1="13" y1="0" x2="13" y2="8" stroke="#e2a547" stroke-width="2.8" stroke-linecap="round"/>
          <line x1="19" y1="0" x2="19" y2="6" stroke="#e2a547" stroke-width="2.8" stroke-linecap="round"/>
        """)
    elif prop == "ring":
        keep_svg.append("""
          <circle cx="0" cy="5" r="12" fill="none" stroke="#e8b24f" stroke-width="3.2"/>
          <polygon points="0,-16 -8,-7 0,-3 8,-7" fill="#d8f3ff" stroke="#2d537b" stroke-width="1.4"/>
          <line x1="0" y1="-21" x2="0" y2="-17" stroke="#fff6d6" stroke-width="1.5"/>
          <line x1="-11" y1="-15" x2="-8" y2="-12" stroke="#fff6d6" stroke-width="1.5"/>
          <line x1="11" y1="-15" x2="8" y2="-12" stroke="#fff6d6" stroke-width="1.5"/>
        """)
    elif prop == "garland":
        keep_svg.append("""
          <path d="M -22 -7 Q 0 16 22 -7" fill="none" stroke="#5b8c71" stroke-width="2.8"/>
          <circle cx="-16" cy="-3" r="5" fill="#c85a48"/>
          <circle cx="-8" cy="3" r="5.5" fill="#e6a947"/>
          <circle cx="0" cy="5.5" r="6" fill="#c85a48"/>
          <circle cx="8" cy="3" r="5.5" fill="#e6a947"/>
          <circle cx="16" cy="-3" r="5" fill="#c85a48"/>
        """)
    elif prop == "cradle_star":
        keep_svg.append("""
          <polygon points="0,-16 4,-4 16,-4 6,3 10,15 0,7 -10,15 -6,3 -16,-4 -4,-4"
                   fill="#f2c15a" stroke="#8c5e1a" stroke-width="1.3" stroke-linejoin="round"/>
          <circle cx="0" cy="0" r="3.5" fill="#fff7df"/>
        """)
    elif prop == "paper_boat":
        keep_svg.append("""
          <polygon points="-22,4 22,4 14,14 -14,14" fill="#2d537b" stroke="#f7ebd2" stroke-width="1.2"/>
          <polygon points="0,-15 0,3 15,3" fill="#c85a48"/>
          <polygon points="-2,-11 -2,3 -14,3" fill="#e6a947"/>
        """)
    else:
        keep_svg.append("""
          <polygon points="-18,1 0,-15 18,1" fill="#2d537b" stroke="#f7ebd2" stroke-width="1.2"/>
          <rect x="-13" y="1" width="26" height="15" fill="#f7ebd2" stroke="#2d537b" stroke-width="1.4"/>
          <rect x="-9" y="3" width="5.5" height="4.5" fill="#f2b84b"/>
          <rect x="3.5" y="3" width="5.5" height="4.5" fill="#f2b84b"/>
          <rect x="-9" y="9.5" width="5.5" height="4.5" fill="#f2b84b"/>
          <rect x="3.5" y="9.5" width="5.5" height="4.5" fill="#f2b84b"/>
        """)

    # Dated Milestone Timeline Rail (x = 300..876, cleanly separated from left title and right plaque)
    active_m_idx = stage["milestone_idx"]
    m_count = len(TIMELINE_MILESTONES)
    rail_x0 = 304
    rail_step = 94
    rail_x1 = rail_x0 + (m_count - 1) * rail_step
    line_end = rail_x0 + max(0, active_m_idx) * rail_step if active_m_idx >= 0 else rail_x0

    milestone_nodes = []
    for idx, item in enumerate(TIMELINE_MILESTONES):
        px = rail_x0 + idx * rail_step
        reached = idx <= active_m_idx
        current = idx == active_m_idx
        r = 5.4 if current else (4.2 if reached else 3.2)
        dot_fill = "#f5c864" if reached else "#544036"
        dot_stroke = "#fff6dc" if current else "#2d1f18"
        date_col = "#f7e3ba" if reached else "#856c58"
        label_col = "#e5b567" if reached else "#6e5848"

        milestone_nodes.append(
            f'<g>'
            f'<circle cx="{px}" cy="656" r="{r}" fill="{dot_fill}" stroke="{dot_stroke}" stroke-width="1.3"/>'
            f'<text x="{px}" y="676" text-anchor="middle" font-family="Avenir, Helvetica, sans-serif" '
            f'font-size="9.2" font-weight="700" fill="{date_col}" letter-spacing="0.4">{item["date"]}</text>'
            f'<text x="{px}" y="690" text-anchor="middle" font-family="Avenir, Helvetica, sans-serif" '
            f'font-size="7.8" font-weight="600" fill="{label_col}" letter-spacing="0.8">{item["label"]}</text>'
            f'</g>'
        )

    return f"""
    <g filter="url(#paperShadow)">
      <rect x="0" y="624" width="{WIDTH}" height="96" fill="#3a271f"/>
      <rect x="0" y="624" width="{WIDTH}" height="7" fill="#634334"/>
      <line x1="0" y1="631" x2="{WIDTH}" y2="631" stroke="#c89d5c" stroke-opacity="0.45" stroke-width="1.2"/>

      <path d="M 40 652 Q 340 646 680 654 T 1240 650" fill="none" stroke="#281a14" stroke-width="1.6" opacity="0.55"/>
      <path d="M 90 692 Q 480 686 860 694 T 1210 688" fill="none" stroke="#281a14" stroke-width="1.6" opacity="0.55"/>

      <!-- Left Keepsake Coaster & Title -->
      <g transform="translate(64, 672)">
        <ellipse cx="2" cy="4" rx="36" ry="23" fill="#1b110d" opacity="0.45"/>
        <ellipse cx="0" cy="0" rx="34" ry="21" fill="#f3e5c8" stroke="#b89254" stroke-width="1.6"/>
        <ellipse cx="0" cy="0" rx="29" ry="17" fill="none" stroke="#c85a48" stroke-opacity="0.45" stroke-width="1" stroke-dasharray="3,3"/>
        <g transform="scale({max(0.01, prop_in):.3f})">
          {''.join(keep_svg)}
        </g>
      </g>
      <text x="110" y="667" font-family="Georgia, serif" font-style="italic" font-size="13.5" fill="#e8d6b5">
        “The House We Made”
      </text>
      <text x="110" y="684" font-family="Avenir, Helvetica, sans-serif" font-size="8.5" font-weight="600" letter-spacing="1.0" fill="#b89d7a">
        MILESTONE TIMELINE
      </text>

      <!-- Dated Brass Milestone Timeline Rail -->
      <line x1="{rail_x0}" y1="656" x2="{rail_x1}" y2="656" stroke="#241712" stroke-width="3.2" stroke-linecap="round"/>
      <line x1="{rail_x0}" y1="656" x2="{line_end}" y2="656" stroke="#d9a652" stroke-width="2.6" stroke-linecap="round"/>
      {''.join(milestone_nodes)}

      <!-- Right Engraved Family Dates Register Plaque -->
      <rect x="928" y="644" width="320" height="54" rx="4" fill="#2c1d17" stroke="#9e7840" stroke-width="1.3"/>
      <circle cx="940" cy="671" r="2.2" fill="#d4a048"/>
      <circle cx="1236" cy="671" r="2.2" fill="#d4a048"/>
      <text x="1088" y="661" text-anchor="middle" font-family="Georgia, serif" font-size="10.8" font-weight="bold" fill="#f3e2be" letter-spacing="0.5">
        ARAVIND &amp; SANJANA · MARRIED 26 JAN 2023
      </text>
      <line x1="956" y1="668" x2="1220" y2="668" stroke="#6e512c" stroke-width="0.8"/>
      <text x="1088" y="681" text-anchor="middle" font-family="Avenir, Helvetica, sans-serif" font-size="9.0" font-weight="700" fill="#e6be74" letter-spacing="0.7">
        DAIVIK · 03 AUG 2024    |    DEEYAN · 09 SEP 2026
      </text>
      <text x="1088" y="692.5" text-anchor="middle" font-family="Avenir, Helvetica, sans-serif" font-size="7.8" font-weight="500" fill="#b89d7a" letter-spacing="0.9">
        FIRST MET 20 JAN 2022  ·  ENGAGED 04 DEC 2022
      </text>
    </g>
    """


def build_fireflies_svg(progress, sky_phase, picture):
    """Add warm drifting fireflies / floating paper lanterns across the twilight garden."""
    vis = smoothstep(0.32, 0.75, sky_phase)
    if vis <= 0.01:
        return ""
    rng = random.Random(420)
    dots = []
    for i in range(18):
        bx = rng.uniform(140, 1180)
        by = rng.uniform(310, 560)
        dx = math.sin(picture * 0.22 + i * 1.9) * 14
        dy = math.cos(picture * 0.18 + i * 1.3) * 10
        pulse = 0.45 + 0.55 * math.sin(picture * 0.5 + i * 2.1)
        op = vis * pulse * 0.85
        dots.append(
            f'<circle cx="{bx + dx:.1f}" cy="{by + dy:.1f}" r="6.5" fill="#ffd978" opacity="{op * 0.38:.3f}" filter="url(#softGlow)"/>'
            f'<circle cx="{bx + dx:.1f}" cy="{by + dy:.1f}" r="2.0" fill="#fff9df" opacity="{op:.3f}"/>'
        )
    return "\n".join(dots)


def build_frame_svg(frame):
    """Assemble the complete multi-plane SVG for a single stop-motion frame."""
    picture = frame // 2
    stage_float = min(len(STAGES) - 0.0001, (frame / float(FPS)) / 2.4)
    stage_index = min(len(STAGES) - 1, int(stage_float))
    stage = STAGES[stage_index]
    within = stage_float - stage_index

    prev_stage = STAGES[max(0, stage_index - 1)]
    # Complete each chapter's pop-up assembly in the first 40% of the chapter so the new elements hold proudly
    t_interp = smoothstep(0.0, 0.40, within)
    sky_phase = (
        prev_stage["sky_phase"] + (stage["sky_phase"] - prev_stage["sky_phase"]) * t_interp
        if stage_index > 0
        else stage["sky_phase"] * t_interp
    )
    start_prog = prev_stage["progress"] if stage_index > 0 else 0.0
    progress = start_prog + (stage["progress"] - start_prog) * t_interp
    progress = clamp(progress, 0.0, 1.0)
    progress = round(progress * 32.0) / 32.0

    rng = random.Random(7000 + picture)
    jx = rng.uniform(-0.45, 0.45)
    jy = rng.uniform(-0.45, 0.45)

    sky_svg = build_sky_svg(sky_phase, picture)
    landscape_svg = build_landscape_svg(progress, sky_phase, picture)
    left_garden_svg = build_left_garden_svg(progress, sky_phase, picture)
    house_svg = build_house_svg(progress, sky_phase, picture)
    chars_svg = build_characters_svg(progress, stage_index, picture)
    fireflies_svg = build_fireflies_svg(progress, sky_phase, picture)
    placard_svg = build_letterpress_placard_svg(stage, stage_index, within)
    apron_svg = build_stage_apron_and_keepsake_svg(stage, stage_index, progress, within)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
      <defs>
        <filter id="paperShadow" x="-8%" y="-8%" width="118%" height="122%">
          <feDropShadow dx="2" dy="5" stdDeviation="3.8" flood-color="#0b131b" flood-opacity="0.42"/>
        </filter>
        <filter id="paperShadowSm" x="-10%" y="-10%" width="124%" height="124%">
          <feDropShadow dx="1.5" dy="3" stdDeviation="2.2" flood-color="#0b131b" flood-opacity="0.38"/>
        </filter>
        <filter id="decklePaper" x="-5%" y="-8%" width="110%" height="120%">
          <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="3" seed="5" result="noise"/>
          <feDisplacementMap in="SourceGraphic" in2="noise" scale="1.8" xChannelSelector="R" yChannelSelector="G" result="deckled"/>
          <feDropShadow in="deckled" dx="2" dy="4" stdDeviation="3.2" flood-color="#0b131b" flood-opacity="0.38"/>
        </filter>
        <filter id="softGlow" x="-35%" y="-35%" width="170%" height="170%">
          <feGaussianBlur stdDeviation="5.5"/>
        </filter>
        <linearGradient id="wallPaperGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#fbf1dc"/>
          <stop offset="100%" stop-color="#eedcc0"/>
        </linearGradient>
        <linearGradient id="cardPaperGrad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#faf2df"/>
          <stop offset="100%" stop-color="#efe1c2"/>
        </linearGradient>
        <radialGradient id="lampRadial" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#ffe799" stop-opacity="0.82"/>
          <stop offset="50%" stop-color="#f7b955" stop-opacity="0.32"/>
          <stop offset="100%" stop-color="#f7b955" stop-opacity="0"/>
        </radialGradient>
        <radialGradient id="vignetteGrad" cx="50%" cy="48%" r="68%">
          <stop offset="62%" stop-color="#000000" stop-opacity="0"/>
          <stop offset="100%" stop-color="#091019" stop-opacity="0.46"/>
        </radialGradient>
      </defs>

      <g transform="translate({jx:.2f},{jy:.2f})">
        {sky_svg}
        {landscape_svg}
        {left_garden_svg}
        {house_svg}
        {chars_svg}
        {fireflies_svg}
        {placard_svg}
      </g>

      {apron_svg}

      <!-- Proscenium Inner Border & Cinema Lens Vignette -->
      <rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" fill="url(#vignetteGrad)" pointer-events="none"/>
      <rect x="8" y="8" width="{WIDTH - 16}" height="{HEIGHT - 16}" rx="6"
            fill="none" stroke="#c89d5c" stroke-opacity="0.28" stroke-width="1.5"/>
    </svg>"""


def apply_paper_texture_and_flicker(pil_img, picture):
    """Add tactile cotton-paper fiber texture and stop-motion exposure micro-flicker."""
    arr = np.asarray(pil_img, dtype=np.float32)
    rng = np.random.default_rng(12000 + picture)

    flicker = 1.0 + rng.uniform(-0.011, 0.011)
    arr = arr * flicker

    fine_grain = rng.normal(0.0, 2.1, size=(HEIGHT, WIDTH, 1)).astype(np.float32)
    coarse_grain = rng.normal(0.0, 1.3, size=(HEIGHT // 2, WIDTH // 2, 1)).astype(np.float32)
    coarse_grain = np.repeat(np.repeat(coarse_grain, 2, axis=0), 2, axis=1)
    arr = np.clip(arr + fine_grain + coarse_grain, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def render_picture(picture):
    """Render one unique stop-motion picture (used for 2 frames at 12 fps)."""
    frame = picture * 2
    svg_bytes = build_frame_svg(frame).encode("utf-8")
    res = subprocess.run(
        [RSVG_BIN, "-f", "png"],
        input=svg_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    img = Image.open(io.BytesIO(res.stdout)).convert("RGB")
    return apply_paper_texture_and_flicker(img, picture)


def render_frame(frame):
    """Public helper to render a single frame index (0..TOTAL_FRAMES-1)."""
    return render_picture(frame // 2)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg, "-y", "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgb24",
        "-s", "%dx%d" % (WIDTH, HEIGHT), "-r", str(FPS), "-i", "-", "-an",
        "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(OUT_FILE),
    ]

    unique_pictures = TOTAL_FRAMES // 2
    workers = min(8, os.cpu_count() or 4)
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    with ProcessPoolExecutor(max_workers=workers) as pool:
        for pic_idx, img in enumerate(pool.map(render_picture, range(unique_pictures), chunksize=4)):
            raw = img.tobytes()
            process.stdin.write(raw)
            process.stdin.write(raw)
            if pic_idx == unique_pictures - 6:
                img.save(POSTER_FILE, optimize=True)
            if (pic_idx * 2) % 24 == 0:
                print("rendered %d/%d frames" % (pic_idx * 2, TOTAL_FRAMES), file=sys.stderr)

    process.stdin.close()
    stderr = process.stderr.read().decode("utf-8", errors="replace")
    result = process.wait()
    if result:
        print(stderr, file=sys.stderr)
        raise SystemExit(result)
    print("wrote %s" % OUT_FILE)
    print("wrote %s" % POSTER_FILE)


if __name__ == "__main__":
    main()
