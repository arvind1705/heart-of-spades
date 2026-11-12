#!/usr/bin/env python3
"""Heart of Spades - "Sculpted in clay", a plasticine stop-motion film made by code.

Rules of the medium (every picture obeys them):
  * Everything in frame is a physical thing on an animator's desk: plasticine, a green
    cutting mat, a folded paper tent card. No drawn overlays, no vector labels.
  * Clay is never created from nothing. Big masses roll in from the spare pile and are
    squashed, pinched or pressed into shape; small details are placed one per picture
    (replacement animation), and at the end everything is kneaded back.
  * Animated on twos (12 pictures a second). A piece that was touched changes its thumb
    dents and fingerprints from picture to picture; a piece that was not touched does not.
  * One warm desk lamp (area light, soft shadows), a cool room fill, shallow depth of field.

Pipeline: every picture the clay is a smooth-min union of primitives baked into a 3D
signed-distance grid on the GPU (PyTorch / Metal), displaced by a thumb-dent field, then
path-style sampled (lens, lamp and pixel jitter per sample) and encoded with ffmpeg.

Usage:
  python3 video/generate_clay_stop_motion.py                 # full film + poster
  python3 video/generate_clay_stop_motion.py --still 19.5 --scale 0.5 --spp 8 --out a.png
  python3 video/generate_clay_stop_motion.py --sheet 0,2,5,8,11,14,17,20 --out sheet.png
"""

import argparse
import math
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import gaussian_filter
import torch
import torch.nn.functional as F

WIDTH, HEIGHT = 1920, 1080
FPS = 12                      # delivery frame rate; every picture is held for two frames
DURATION = 24.0
PICTURES = int(DURATION * FPS / 2)   # 144 unique pictures
PIC_DT = DURATION / PICTURES

OUT_DIR = Path(__file__).resolve().parent
OUT_FILE = OUT_DIR / "heart-of-spades-clay-stop-motion.mp4"
POSTER_FILE = OUT_DIR / "heart-of-spades-clay-poster.png"
POSTER_TIME = 19.5

DEV = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
INF = 1.0e6


def srgb(r, g, b):
    return ((r / 255.0) ** 2.2, (g / 255.0) ** 2.2, (b / 255.0) ** 2.2)


# --- Clay palette (linear albedo) ---
TERRA = srgb(204, 88, 70)      # Sanjana
SLATE = srgb(58, 94, 142)      # Aravind
IVORY = srgb(236, 222, 190)    # house walls
SKIN = srgb(238, 196, 158)
BRASS = srgb(226, 176, 62)     # ring, sash
SAGE = srgb(104, 152, 116)     # Daivik
MARIGOLD = srgb(236, 142, 44)  # Deeyan
HAIR = srgb(44, 36, 40)
EARTH = srgb(150, 100, 70)
RED = srgb(200, 38, 50)        # the heart
AMBER = srgb(252, 190, 78)     # lit window
HONEY = srgb(150, 112, 66)     # unlit window
SMOKE = srgb(236, 233, 226)
WHITE = srgb(244, 243, 238)
DOOR = srgb(124, 60, 52)

# --- Camera (a long lens low over the desk) ---
CAM_POS = np.array([0.05, 1.95, 4.90])
CAM_TGT = np.array([0.05, 0.50, 0.00])
FOCAL = 2.75                   # in units of picture height
FOCUS_AT = np.array([0.30, 0.30, 0.42])
APERTURE = 0.017               # lens radius in world units

# --- Lights ---
KEY_POS = np.array([-2.5, 3.4, 3.0])
KEY_AIM = np.array([0.15, 0.2, 0.1])
KEY_RADIUS = 0.34
KEY_COL = (1.00, 0.86, 0.70)
KEY_POWER = 78.0
RIM_DIR = np.array([0.56, 0.52, -0.65])
RIM_COL = (0.42, 0.56, 0.82)
SKY_COL = (0.150, 0.185, 0.250)
BOUNCE_COL = (0.060, 0.120, 0.085)

# --- Clay volume (signed-distance grid) ---
VOX = 0.005
GMIN = np.array([-1.65, -0.03, -1.05])
NX, NY, NZ = 640, 304, 416
GMAX = GMIN + np.array([NX, NY, NZ]) * VOX
COARSE = 4
BAND = 0.035                   # exact-distance band baked around the surface
BAND_OK = 0.019
TILE = 128

MAT_X0, MAT_X1, MAT_Z0, MAT_Z1 = -2.45, 2.45, -1.95, 1.40
WALL_Z = -4.6


# =====================================================================================
#  Small helpers
# =====================================================================================

def ss(a, b, t):
    if b <= a:
        return 1.0 if t >= a else 0.0
    u = min(1.0, max(0.0, (t - a) / (b - a)))
    return u * u * (3.0 - 2.0 * u)


def kf(t, keys):
    """Eased keyframes: keys = [(time, value), ...], value a float or a tuple."""
    if t <= keys[0][0]:
        return np.asarray(keys[0][1], dtype=float)
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t < t1:
            w = ss(t0, t1, t)
            return (1.0 - w) * np.asarray(v0, dtype=float) + w * np.asarray(v1, dtype=float)
    return np.asarray(keys[-1][1], dtype=float)


def lerp(a, b, w):
    return np.asarray(a, dtype=float) * (1.0 - w) + np.asarray(b, dtype=float) * w


def hop(t, spans):
    """Clay hops: spans = [(t0, t1, height), ...]. Returns (lift, squash)."""
    for t0, t1, h in spans:
        if t0 <= t < t1:
            f = (t - t0) / (t1 - t0)
            lift = h * 4.0 * f * (1.0 - f)
            return lift, (-0.10 if 0.2 < f < 0.8 else 0.12)
        if t1 <= t < t1 + PIC_DT * 0.99:
            return 0.0, 0.16          # the landing squash, held for one picture
    return 0.0, 0.0


def on(t, t_on, t_off):
    return t_on - 1e-6 <= t < t_off - 1e-6


# =====================================================================================
#  Primitives
# =====================================================================================

def box(P, name, c, h, r, col, k=0.016, tx=0.0, tz=0.0, yaw=0.0, roll=0.0, glow=0.0, mix=0.25):
    P.append({"n": name, "t": "box", "c": tuple(float(v) for v in c), "h": tuple(float(v) for v in h),
              "r": float(r), "col": col, "k": float(k), "tx": float(tx), "tz": float(tz),
              "yaw": float(yaw), "roll": float(roll), "glow": float(glow), "mix": float(mix)})


def ball(P, name, c, r, col, k=0.016, glow=0.0, mix=0.25):
    box(P, name, c, (0.0, 0.0, 0.0), r, col, k=k, glow=glow, mix=mix)


def cap(P, name, a, b, r, col, k=0.016, glow=0.0, mix=0.25):
    P.append({"n": name, "t": "cap", "a": tuple(float(v) for v in a), "b": tuple(float(v) for v in b),
              "r": float(r), "col": col, "k": float(k), "glow": float(glow), "mix": float(mix)})


def tor(P, name, c, R, rb, an, col, k=0.016, glow=0.0, mix=0.25):
    """A coil bent into a ring standing in the xy plane; `an` is the half arc measured from the bottom."""
    P.append({"n": name, "t": "tor", "c": tuple(float(v) for v in c), "R": float(R), "r": float(rb),
              "an": float(an), "col": col, "k": float(k), "glow": float(glow), "mix": float(mix)})


def prim_vec(pr):
    if pr["t"] == "cap":
        return np.array(pr["a"] + pr["b"] + (pr["r"],))
    if pr["t"] == "tor":
        return np.array(pr["c"] + (pr["R"], pr["r"], pr["an"] * 0.1))
    return np.array(pr["c"] + pr["h"] + (pr["r"], pr["tx"] * 0.1, pr["tz"] * 0.1, pr["yaw"] * 0.2, pr["roll"] * 0.2))


# =====================================================================================
#  Choreography
# =====================================================================================

HOUSE_X, HOUSE_Z = 0.62, -0.22
WALL_FRONT = HOUSE_Z + 0.26 + 0.035
GABLE_FRONT = HOUSE_Z + 0.31 + 0.035
LUMP = (0.0, 0.55)

PILE_WALLS = (-1.22, 0.36, -0.58)
PILE_ROOF = (-0.66, 0.30, -0.66)
PILE_BASE = (-0.95, 0.17, -0.18)
PILE_CHIM = (-0.28, 0.10, -0.52)
PILE_DAIVIK = (-0.45, 0.124, -0.30)
PILE_DEEYAN = (-0.42, 0.100, -0.02)
GOLD_REST = (-0.48, 0.085, 0.90)
RING_C = (0.64, 0.68)
RING_R, RING_TUBE = 0.15, 0.034

CARD_TIMES = [(0.0, 0), (1.3334, 1), (3.0, 2), (6.0, 3), (9.0, 4), (12.0, 5), (15.0, 6), (18.0, 0)]
CARD_TEXT = [
    ("for Sanjana", "Always & again", "our story, sculpted in clay"),
    ("scene 1", "20 Jan 2022", "the day we met"),
    ("scene 2", "27 Jan · 11 Feb 2022", "first love, first held hands"),
    ("scene 3", "04 Dec 2022", "the proposal"),
    ("scene 4", "26 Jan 2023", "our wedding day"),
    ("scene 5", "03 Aug 2024", "Daivik arrives"),
    ("scene 6", "09 Sep 2026", "Deeyan arrives"),
]


def figure(P, sc, name, x, z, s, f, col, style, yaw=0.0, lift=0.0, sq=0.0, k=0.016, mix=0.25,
           hand_l=None, hand_r=None, hair=True, eyes=True):
    """A clay figure that is pinched up out of a ball (f = 0 ball, f = 1 figure)."""
    cy, sy = math.cos(yaw), math.sin(yaw)

    def W(ox, oy, oz):
        return (x + ox * cy + oz * sy, oy + lift, z - ox * sy + oz * cy)

    rb = 0.20 * s
    wide = 1.0 + 0.6 * sq
    tall = 1.0 - sq
    sari = style == "s"
    bh = (0.088 * s, 0.135 * s, 0.070 * s) if sari else (0.074 * s, 0.135 * s, 0.060 * s)
    taper = 0.62 if sari else 0.46
    body_h = lerp((0, 0, 0), bh, f) * np.array([wide, tall, wide])
    body_r = lerp(rb, 0.074 * s, f)
    body_y = lerp(rb, 0.209 * s, f) * tall
    box(P, name + ".body", W(0, body_y, 0), body_h, body_r * (1.0 + 0.3 * sq), col, k=k, tx=taper * f,
        tz=taper * f, yaw=yaw, mix=mix)
    if f < 0.04:
        return
    head_y = lerp(rb, 0.525 * s, f) * tall
    head_r = lerp(0.07 * s, 0.108 * s, f)
    head_c = W(0, head_y, 0.012 * s * f)
    ball(P, name + ".head", head_c, head_r, SKIN, k=lerp(0.03, 0.010, f), mix=0.1)

    # arms: sleeves in body clay, hands in skin clay
    for side, hand in ((-1.0, hand_l), (1.0, hand_r)):
        sh = W(side * 0.092 * s, 0.375 * s * tall, 0.0)
        hd = W(side * 0.150 * s, 0.215 * s * tall, 0.035 * s) if hand is None else tuple(hand)
        core = W(0, body_y, 0)
        a = lerp(core, sh, f)
        b = lerp(core, hd, f)
        tag = ".armL" if side < 0 else ".armR"
        cap(P, name + tag, a, b, 0.030 * s * (0.5 + 0.5 * f), col, k=0.014, mix=mix)
        ball(P, name + tag + ".hand", b, 0.034 * s * (0.4 + 0.6 * f), SKIN, k=0.008, mix=0.1)

    if sari and f > 0.5:
        cap(P, name + ".sash", W(-0.072 * s, 0.365 * s * tall, 0.062 * s), W(0.082 * s, 0.13 * s * tall, 0.098 * s),
            0.021 * s * f, BRASS, k=0.008, mix=0.15)
    if style == "a" and f > 0.98:
        for i, by in enumerate((0.30, 0.22)):
            ball(P, name + ".btn%d" % i, W(0, by * s, (0.118 if i == 0 else 0.128) * s), 0.014 * s, IVORY, k=0.003)

    if hair and f > 0.98:
        hx, hy, hz = head_c[0] - x, head_c[1] - lift, 0.012 * s

        def H(ox, oy, oz):
            return W(ox, head_y + oy, hz + oz)

        if style == "b":
            ball(P, name + ".hair", H(0, 0.040 * s, -0.040 * s), 0.100 * s, HAIR, k=0.004, mix=0.05)
            ball(P, name + ".curl", H(0.01 * s, 0.108 * s, 0.035 * s), 0.024 * s, HAIR, k=0.006, mix=0.05)
        else:
            ball(P, name + ".hair", H(0, 0.026 * s, -0.030 * s), 0.113 * s, HAIR, k=0.004, mix=0.05)
        if style == "a":
            cap(P, name + ".quiff", H(-0.05 * s, 0.092 * s, 0.045 * s), H(0.045 * s, 0.100 * s, 0.050 * s),
                0.034 * s, HAIR, k=0.012, mix=0.05)
        if style == "k":
            ball(P, name + ".tuft", H(0.0, 0.112 * s, 0.05 * s), 0.036 * s, HAIR, k=0.01, mix=0.05)
        if sari:
            ball(P, name + ".bun", H(0, 0.118 * s, -0.070 * s), 0.056 * s, HAIR, k=0.008, mix=0.05)
            for sd in (-1.0, 1.0):
                cap(P, name + ".lock%d" % (sd > 0), H(sd * 0.094 * s, 0.01 * s, -0.022 * s),
                    H(sd * 0.090 * s, -0.150 * s, -0.012 * s), 0.036 * s, HAIR, k=0.008, mix=0.05)
            ball(P, name + ".flower", H(0.085 * s, 0.085 * s, 0.03 * s), 0.026 * s, WHITE, k=0.004)
    if eyes and f > 0.98:
        fwd = (sy, 0.0, cy)
        right = (cy, 0.0, -sy)
        for sd in (-1.0, 1.0):
            e = [head_c[i] + head_r * (0.32 * sd * right[i] + 0.925 * fwd[i]) for i in range(3)]
            e[1] += head_r * 0.10
            sc["eyes"].append((e[0], e[1], e[2], head_r * 0.125))
        sc["faces"].append((head_c, head_r, yaw, style))


def heart(P, name, c, sz, m, k=0.016, mix=0.25):
    """A ball (m = 0) pinched into a heart (m = 1)."""
    r = lerp(sz * 0.82, sz * 0.47, m)
    tip = (c[0], c[1] - 0.80 * sz * m, c[2])
    for sd in (-1.0, 1.0):
        cap(P, name + (".l" if sd < 0 else ".r"), tip, (c[0] + sd * 0.46 * sz * m, c[1] + 0.34 * sz * m, c[2]),
            r, RED, k=k if m < 0.9 else 0.02, mix=mix)


def build_scene(t):
    """Everything on the mat at time t (seconds, 0..24)."""
    t = t % DURATION
    P = []
    sc = {"prims": P, "eyes": [], "faces": [], "lamps": []}
    for t0, idx in CARD_TIMES:
        if t >= t0 - 1e-6:
            sc["card"] = idx

    # how kneaded-together the starting lump is (1 at the loop point)
    knead = max(1.0 - ss(0.5, 1.3, t), ss(22.9, 23.7, t))
    kk = lerp(0.016, 0.11, knead)
    mixk = lerp(0.25, 1.0, knead)

    # ---------------- Aravind and Sanjana ----------------
    a_form = float(kf(t, [(1.5, 0), (2.3, 1), (22.0, 1), (22.7, 0)]))
    s_form = float(kf(t, [(1.67, 0), (2.5, 1), (22.17, 1), (22.83, 0)]))
    ax = float(kf(t, [(0.5, -0.075), (1.4, -0.30), (3.2, -0.30), (4.2, -0.165), (11.33, -0.165), (12.17, 0.36),
                      (12.5, 0.36), (13.0, 0.27), (22.7, 0.27), (23.6, -0.075)]))
    sx = float(kf(t, [(0.5, 0.075), (1.4, 0.25), (3.2, 0.25), (4.2, 0.150), (11.33, 0.150), (12.17, 0.70),
                      (12.5, 0.70), (13.0, 0.80), (22.83, 0.80), (23.6, 0.075)]))
    az = float(kf(t, [(0.0, 0.55), (22.7, 0.55), (23.6, 0.55)]))
    sz_ = float(kf(t, [(0.5, 0.585), (1.4, 0.55), (22.83, 0.55), (23.6, 0.585)]))
    a_yaw = float(kf(t, [(2.5, 0.0), (2.83, 0.42), (7.0, 0.42), (7.5, 0.62), (9.0, 0.62), (9.5, 0.25), (12.2, 0.12),
                         (21.5, 0.12), (22.0, 0.0)]))
    s_yaw = float(kf(t, [(2.5, 0.0), (2.83, -0.42), (7.0, -0.42), (7.5, 0.50), (9.0, 0.50), (9.5, -0.12),
                         (21.5, -0.12), (22.0, 0.0)]))
    walk = [(3.2, 3.7, 0.07), (3.7, 4.2, 0.07), (11.33, 11.83, 0.08), (11.83, 12.17, 0.06)]
    a_lift, a_sq = hop(t, walk + [(2.83, 3.17, 0.05), (8.33, 8.83, 0.12), (12.5, 13.0, 0.05), (18.5, 19.0, 0.13)])
    s_lift, s_sq = hop(t, walk + [(8.5, 9.0, 0.14), (12.5, 13.0, 0.05), (19.0, 19.5, 0.13)])

    # joined inner hands: reach (4.2-4.8), lift the heart (4.8-5.3), let go (10.9-11.3)
    join = float(kf(t, [(4.2, 0), (4.83, 1), (10.9, 1), (11.3, 0)]))
    raise_ = float(kf(t, [(4.83, 0), (5.33, 1), (10.5, 1), (11.0, 0)]))
    mid = 0.5 * (ax + sx)
    hands_y = lerp(0.27, 0.665, raise_) + 0.5 * (a_lift + s_lift)
    hands = (mid, hands_y, 0.60 - 0.02 * raise_)
    a_rest_r = (ax + 0.150 * math.cos(a_yaw) + 0.035 * math.sin(a_yaw), 0.215 + a_lift, az + 0.035)
    s_rest_l = (sx - 0.150 * math.cos(s_yaw) + 0.035 * math.sin(s_yaw), 0.215 + s_lift, sz_ + 0.035)
    a_hand_r = tuple(lerp(a_rest_r, (hands[0] - 0.022, hands[1], hands[2]), join)) if join > 0 else None
    s_hand_l = tuple(lerp(s_rest_l, (hands[0] + 0.022, hands[1], hands[2]), join)) if join > 0 else None
    # finale: Aravind waves on twos
    a_hand_l = None
    if on(t, 19.67, 20.67):
        flip = int(round(t / PIC_DT)) % 2
        a_hand_l = (ax - 0.20 - 0.04 * flip, 0.60 + 0.04 * flip, az + 0.02)

    figure(P, sc, "A", ax, az, 1.0, a_form, SLATE, "a", yaw=a_yaw, lift=a_lift, sq=a_sq, k=kk, mix=mixk,
           hand_l=a_hand_l, hand_r=a_hand_r, hair=on(t, 2.5, 21.83), eyes=on(t, 2.67, 21.67))
    figure(P, sc, "S", sx, sz_, 0.97, s_form, TERRA, "s", yaw=s_yaw, lift=s_lift, sq=s_sq, k=kk, mix=mixk,
           hand_l=s_hand_l, hand_r=None, hair=on(t, 2.67, 22.0), eyes=on(t, 2.83, 21.83))

    # ---------------- the heart ----------------
    h_open = float(kf(t, [(5.17, 0), (5.67, 1), (21.83, 1), (22.33, 0)]))
    gable_h = (HOUSE_X, 0.895, GABLE_FRONT + 0.045)
    h_pos = kf(t, [(0.5, (0.06, 0.16, 0.66)), (1.4, (sx, 0.19, sz_)), (4.67, (sx, 0.20, sz_)),
                   (4.83, (0.5 * (-0.165 + 0.150), 0.27, 0.60)), (5.33, (-0.0075, 0.775, 0.58)),
                   (10.5, (-0.0075, 0.775, 0.58)), (10.75, (0.33, 1.05, 0.42)), (11.0, gable_h),
                   (21.5, gable_h), (21.75, (0.32, 0.80, 0.50)), (22.0, (0.10, 0.075, 0.70)),
                   (22.9, (0.10, 0.075, 0.70)), (23.6, (0.06, 0.16, 0.66))])
    if on(t, 1.4, 4.67):
        h_pos = np.array([sx, 0.19, sz_])
    h_size = float(kf(t, [(4.67, 0.062), (5.17, 0.088), (22.0, 0.088), (23.6, 0.062)]))
    heart(P, "heart", h_pos, h_size, h_open, k=max(kk, 0.02) if (t < 4.67 or t > 22.9) else 0.016, mix=mixk)

    # ---------------- the ring ----------------
    ring_an = float(kf(t, [(7.17, 0.0), (8.17, math.pi), (21.83, math.pi), (22.5, 0.0)]))
    ring_tube = float(kf(t, [(7.17, 0.085), (7.83, RING_TUBE), (22.0, RING_TUBE), (22.5, 0.085)]))
    gable_r = (HOUSE_X, 0.895, GABLE_FRONT + 0.022)
    floor_y = RING_R + ring_tube
    r_back = (0.32, 0.75)
    ring_c = kf(t, [(0.5, (-0.01, 0.30 - RING_R, 0.62)), (1.4, (GOLD_REST[0], 0.085 - RING_R, GOLD_REST[2])),
                    (6.33, (GOLD_REST[0], 0.085 - RING_R, GOLD_REST[2])), (7.17, (RING_C[0], 0.085 - RING_R, RING_C[1])),
                    (8.17, (RING_C[0], floor_y, RING_C[1])), (11.0, (RING_C[0], floor_y, RING_C[1])),
                    (11.25, (0.66, 1.05, 0.45)), (11.5, gable_r), (21.33, gable_r), (21.58, (0.45, 1.0, 0.5)),
                    (21.83, (r_back[0], floor_y, r_back[1])), (22.5, (r_back[0], 0.085 - RING_R, r_back[1])),
                    (22.9, (r_back[0], 0.085 - RING_R, r_back[1])), (23.6, (-0.01, 0.30 - RING_R, 0.62))])
    if ring_an < 0.02:
        ball(P, "ring", (ring_c[0], ring_c[1] + RING_R, ring_c[2]), ring_tube, BRASS, k=max(kk, 0.02), mix=mixk)
    else:
        tor(P, "ring", ring_c, RING_R, ring_tube, ring_an, BRASS, k=0.012)
    if on(t, 8.33, 21.33):
        dia_sq = 0.3 if t < 8.5 else 0.0
        box(P, "diamond", (ring_c[0], ring_c[1] + RING_R + RING_TUBE + 0.030 - 0.01 * dia_sq, ring_c[2]),
            (0.028 * (1 + dia_sq), 0.028 * (1 - dia_sq), 0.024), 0.012, WHITE, k=0.004, roll=math.pi / 4, glow=0.10)

    # ---------------- the house ----------------
    hx, hz = HOUSE_X, HOUSE_Z
    # base slab
    m = float(kf(t, [(9.67, 0), (10.0, 1), (22.33, 1), (22.67, 0)]))
    pos = kf(t, [(9.0, PILE_BASE), (9.67, (hx, 0.17, hz)), (22.67, (hx, 0.17, hz)), (23.33, PILE_BASE)])
    box(P, "base", (pos[0], lerp(pos[1], 0.050, m), pos[2]), lerp((0, 0, 0), (0.70, 0.028, 0.37), m),
        lerp(0.17, 0.024, m), EARTH)
    # walls
    m = float(kf(t, [(10.0, 0), (10.5, 1), (22.0, 1), (22.4, 0)]))
    pos = kf(t, [(9.17, PILE_WALLS), (9.83, (hx - 0.55, 0.36, hz - 0.1)), (10.0, (hx, 0.42, hz)),
                 (22.4, (hx, 0.42, hz)), (22.57, (hx - 0.55, 0.36, hz - 0.1)), (23.25, PILE_WALLS)])
    box(P, "walls", (pos[0], lerp(pos[1], 0.375, m), pos[2]), lerp((0, 0, 0), (0.56, 0.26, 0.26), m),
        lerp(0.36, 0.035, m), IVORY, k=0.02)
    # roof
    m = float(kf(t, [(10.67, 0), (11.0, 1), (21.67, 1), (22.0, 0)]))
    pos = kf(t, [(9.67, PILE_ROOF), (10.33, (hx - 0.85, 0.30, hz - 0.15)), (10.67, (hx, 0.98, hz)),
                 (22.0, (hx, 0.98, hz)), (22.25, (hx - 0.85, 0.30, hz - 0.15)), (22.9, PILE_ROOF)])
    box(P, "roof", (pos[0], lerp(pos[1], 0.925, m), pos[2]), lerp((0, 0, 0), (0.70, 0.24, 0.31), m),
        lerp(0.30, 0.035, m), SLATE, k=0.012, tx=m)
    # chimney
    m = float(kf(t, [(11.0, 0), (11.33, 1), (21.33, 1), (21.67, 0)]))
    chim = (hx + 0.40, 1.12, hz - 0.06)
    pos = kf(t, [(10.33, PILE_CHIM), (10.75, (hx - 0.2, 0.10, hz + 0.45)), (11.0, chim),
                 (21.67, chim), (21.92, (hx - 0.2, 0.10, hz + 0.45)), (22.5, PILE_CHIM)])
    box(P, "chimney", pos, lerp((0, 0, 0), (0.068, 0.17, 0.068), m), lerp(0.10, 0.02, m), TERRA, k=0.012)

    built = on(t, 10.5, 22.0)
    D = PIC_DT

    def placed(order_on, order_off):
        return on(t, 10.5 + order_on * D, 21.0 + order_off * D)

    wf = WALL_FRONT
    if placed(1, 5):
        box(P, "door", (hx, 0.29, wf + 0.012), (0.105, 0.185, 0.02), 0.016, DOOR, k=0.006)
        ball(P, "knob", (hx + 0.065, 0.28, wf + 0.05), 0.017, BRASS, k=0.003)
        box(P, "step", (hx, 0.035, wf + 0.13), (0.19, 0.016, 0.07), 0.018, IVORY, k=0.008)
    lit_fan = on(t, 11.5, 21.0)
    if placed(2, 5):
        cap(P, "fanlight", (hx - 0.05, 0.535, wf + 0.012), (hx + 0.05, 0.535, wf + 0.012), 0.050,
            AMBER if lit_fan else HONEY, k=0.006, glow=1.0 if lit_fan else 0.0)
    lit = {-1.0: on(t, 14.17, 21.0), 1.0: on(t, 17.17, 21.0)}
    for i, sd in enumerate((-1.0, 1.0)):
        wx = hx + sd * 0.355
        tag = "L" if sd < 0 else "R"
        if placed(3 + i, 4):
            box(P, "win" + tag, (wx, 0.415, wf + 0.008), (0.100, 0.105, 0.018), 0.014,
                AMBER if lit[sd] else HONEY, k=0.006, glow=1.0 if lit[sd] else 0.0)
            cap(P, "munV" + tag, (wx, 0.32, wf + 0.03), (wx, 0.51, wf + 0.03), 0.011, IVORY, k=0.003)
            cap(P, "munH" + tag, (wx - 0.095, 0.415, wf + 0.03), (wx + 0.095, 0.415, wf + 0.03), 0.011, IVORY, k=0.003)
            if lit[sd]:
                sc["lamps"].append((wx, 0.415, wf + 0.10, 0.030))
        if placed(5 + i, 3):
            for s2 in (-1.0, 1.0):
                box(P, "shut%s%d" % (tag, s2 > 0), (wx + s2 * 0.150, 0.415, wf + 0.012), (0.030, 0.118, 0.014),
                    0.010, SAGE, k=0.005)
        if placed(7 + i, 2):
            box(P, "fbox" + tag, (wx, 0.262, wf + 0.035), (0.125, 0.026, 0.030), 0.014, TERRA, k=0.006)
        if placed(9 + i, 1):
            for j, fx in enumerate((-0.085, 0.0, 0.085)):
                ball(P, "fl%s%d" % (tag, j), (wx + fx, 0.315 + 0.008 * (j % 2), wf + 0.04), 0.027,
                     (RED, WHITE, MARIGOLD)[(j + i) % 3], k=0.004)
    if lit_fan:
        sc["lamps"].append((hx, 0.52, wf + 0.10, 0.016))
    # wedding garland under the eaves: one bead per picture
    for g in range(9):
        if on(t, 11.0 + (g + 1) * D * 0.5, 21.0 + (8 - g) * D * 0.25):
            gt = g / 8.0 * 2.0 - 1.0
            ball(P, "bead%d" % g, (hx + gt * 0.50, 0.632 - 0.035 * (1 - gt * gt), wf + 0.022), 0.029,
                 MARIGOLD if g % 2 == 0 else RED, k=0.004)
    if on(t, 11.33 + D, 21.33):
        box(P, "chimcap", (chim[0], 1.305, chim[2]), (0.088, 0.018, 0.088), 0.012, EARTH, k=0.006)
    # smoke: three clay puffs replaced every picture
    if on(t, 11.67, 21.0):
        pic = int(round(t / PIC_DT))
        for i in range(3):
            ph = ((pic * 0.11 + i / 3.0) % 1.0)
            sy_ = 1.365 + ph * 0.115
            sx_ = chim[0] + 0.022 * math.sin(pic * 0.9 + i * 2.1) + ph * 0.05
            ball(P, "smoke%d" % i, (sx_, sy_, chim[2] + 0.01), 0.030 + 0.022 * math.sin(ph * math.pi), SMOKE, k=0.03)
    del built

    # ---------------- Daivik ----------------
    d_home = (0.535, 0.74)
    d_form = float(kf(t, [(13.0, 0), (13.67, 1), (21.17, 1), (21.83, 0)]))
    d_pos = kf(t, [(12.17, (PILE_DAIVIK[0], PILE_DAIVIK[2])), (12.5, (-0.30, 0.42)), (12.75, (0.0, 0.90)),
                   (13.0, d_home), (21.83, d_home), (22.1, (0.0, 0.90)), (22.35, (-0.30, 0.42)),
                   (22.7, (PILE_DAIVIK[0], PILE_DAIVIK[2]))])
    d_lift, d_sq = hop(t, [(14.33, 14.83, 0.13), (18.75, 19.25, 0.15)])
    figure(P, sc, "D", d_pos[0], d_pos[1], 0.62, d_form, SAGE, "k", yaw=0.05, lift=d_lift, sq=d_sq,
           hair=on(t, 13.83, 21.0), eyes=on(t, 14.0, 21.17))

    # ---------------- Deeyan ----------------
    y_home = (1.05, 0.70)
    y_form = float(kf(t, [(16.0, 0), (16.67, 1), (21.33, 1), (22.0, 0)]))
    y_pos = kf(t, [(15.17, (PILE_DEEYAN[0], PILE_DEEYAN[2])), (15.4, (-0.30, 0.50)), (15.6, (0.20, 0.93)),
                   (15.8, (0.82, 0.93)), (16.0, y_home), (22.0, y_home), (22.2, (0.82, 0.93)),
                   (22.4, (0.20, 0.93)), (22.6, (-0.30, 0.50)), (22.85, (PILE_DEEYAN[0], PILE_DEEYAN[2]))])
    y_lift, y_sq = hop(t, [(17.33, 17.83, 0.12), (19.25, 19.75, 0.15)])
    figure(P, sc, "Y", y_pos[0], y_pos[1], 0.50, y_form, MARIGOLD, "b", yaw=-0.08, lift=y_lift, sq=y_sq,
           hair=on(t, 16.83, 21.17), eyes=on(t, 17.0, 21.33))
    return sc


def scene_for_picture(pic):
    """Scene plus per-prim activity (was this piece touched since the last picture?)."""
    t = pic * PIC_DT
    sc = build_scene(t)
    prev = {p["n"]: prim_vec(p) for p in build_scene((pic - 1) * PIC_DT)["prims"]}
    rng = np.random.default_rng(9000 + pic)
    for p in sc["prims"]:
        v = prim_vec(p)
        q = prev.get(p["n"])
        act = 1.0 if (q is None or q.shape != v.shape) else min(1.0, float(np.abs(v - q).max()) / 0.012)
        if p["n"].startswith("smoke"):
            act = 1.0
        p["act"] = act
        if act > 0.05:      # a hand never puts a piece back exactly
            j = rng.normal(0.0, 0.0022, 3) * act
            for key in ("c", "a", "b"):
                if key in p:
                    p[key] = tuple(np.asarray(p[key]) + j)
    sc["pic"] = pic
    return sc


# =====================================================================================
#  Textures (made once on the CPU)
# =====================================================================================

def find_font(path, want, size):
    for idx in range(12):
        try:
            f = ImageFont.truetype(path, size, index=idx)
        except Exception:
            break
        if f.getname()[1] == want:
            return f
    return ImageFont.truetype(path, size)


def to_lin(img):
    a = np.asarray(img, dtype=np.float32) / 255.0
    return a ** 2.2


def make_mat_texture():
    """Self-healing cutting mat: printed grid, knife cuts, dust, lint and clay crumbs. RGB + gloss."""
    ppu = 520.0
    w = int((MAT_X1 - MAT_X0) * ppu)
    h = int((MAT_Z1 - MAT_Z0) * ppu)
    rng = np.random.default_rng(11)
    base = np.zeros((h, w, 3), np.float32)
    mott = gaussian_filter(rng.standard_normal((h, w)).astype(np.float32), 46)
    mott = mott / mott.std()
    fine = gaussian_filter(rng.standard_normal((h, w)).astype(np.float32), 1.2)
    fine = fine / fine.std()
    tone = 1.0 + 0.07 * mott + 0.05 * fine
    for i, v in enumerate((30, 104, 82)):
        base[:, :, i] = v * tone
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    over = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(over)

    def px(x, z):
        return ((x - MAT_X0) * ppu, (z - MAT_Z0) * ppu)

    x0, x1, z0, z1 = MAT_X0 + 0.15, MAT_X1 - 0.15, MAT_Z0 + 0.15, MAT_Z1 - 0.1
    n = 0
    xv = x0
    while xv <= x1 + 1e-6:
        major = n % 5 == 0
        d.line([px(xv, z0), px(xv, z1)], fill=(176, 206, 160, 150 if major else 78), width=3 if major else 1)
        xv += 0.1
        n += 1
    n = 0
    zv = z0
    while zv <= z1 + 1e-6:
        major = n % 5 == 0
        d.line([px(x0, zv), px(x1, zv)], fill=(176, 206, 160, 150 if major else 78), width=3 if major else 1)
        zv += 0.1
        n += 1
    d.rectangle([px(x0, z0), px(x1, z1)], outline=(186, 212, 168, 190), width=4)
    d.line([px(x0, z1), px(x0 + 1.8, z1 - 1.8)], fill=(176, 206, 160, 90), width=2)   # 45 degree guide
    # knife cuts (pale) and old deep cuts (dark)
    gloss = Image.new("L", (w, h), 128)
    gd = ImageDraw.Draw(gloss)
    for i in range(260):
        cx, cz = rng.uniform(-1.9, 1.9), rng.uniform(-1.3, 1.2)
        ang = rng.normal(0.0, 0.5) + (math.pi / 2 if rng.random() < 0.4 else 0.0)
        ln = rng.uniform(0.08, 0.9)
        a = px(cx - math.cos(ang) * ln / 2, cz - math.sin(ang) * ln / 2)
        b = px(cx + math.cos(ang) * ln / 2, cz + math.sin(ang) * ln / 2)
        if rng.random() < 0.75:
            d.line([a, b], fill=(170, 214, 186, int(rng.uniform(40, 120))), width=1)
        else:
            d.line([a, b], fill=(10, 50, 38, int(rng.uniform(70, 150))), width=2)
        gd.line([a, b], fill=60, width=3)
    for i in range(5200):   # dust
        p = px(rng.uniform(-2.2, 2.2), rng.uniform(-1.7, 1.3))
        r = rng.uniform(0.5, 1.7)
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=(214, 220, 204, int(rng.uniform(40, 150))))
    for i in range(90):     # lint fibres
        cx, cz = rng.uniform(-1.9, 1.9), rng.uniform(-1.2, 1.2)
        pts = []
        ang = rng.uniform(0, 6.28)
        for s in range(7):
            pts.append(px(cx, cz))
            ang += rng.normal(0, 0.55)
            cx += math.cos(ang) * 0.012
            cz += math.sin(ang) * 0.012
        d.line(pts, fill=(226, 226, 214, int(rng.uniform(70, 150))), width=1)
    crumbs = [(204, 88, 70), (58, 94, 142), (236, 222, 190), (226, 176, 62), (104, 152, 116), (236, 142, 44)]
    for i in range(420):    # clay crumbs and smears where the work happens
        cx, cz = rng.normal(0.15, 0.75), rng.normal(0.35, 0.45)
        p = px(cx, cz)
        r = abs(rng.normal(0.0, 1.5)) + 0.8
        c = crumbs[int(rng.integers(0, len(crumbs)))]
        d.ellipse([p[0] - r, p[1] - r * 0.8, p[0] + r, p[1] + r * 0.8], fill=c + (int(rng.uniform(110, 230)),))
    for i in range(46):     # greasy thumb smears
        p = px(rng.normal(0.15, 0.8), rng.normal(0.3, 0.5))
        rx, rz = rng.uniform(14, 60), rng.uniform(8, 30)
        gd.ellipse([p[0] - rx, p[1] - rz, p[0] + rx, p[1] + rz], fill=int(rng.uniform(150, 215)))
    img = Image.alpha_composite(img.convert("RGBA"), over).convert("RGB")
    gloss = gloss.filter(ImageFilter.GaussianBlur(5))
    rgb = to_lin(img)
    g = np.asarray(gloss, np.float32)[:, :, None] / 255.0
    tex = np.concatenate([rgb, g], axis=2)
    return torch.from_numpy(tex).permute(2, 0, 1)[None].contiguous().to(DEV)


def make_card_textures():
    """The animator's folded tent card: one hand-stamped card per scene."""
    w, h = 1040, 640
    type_path = "/System/Library/Fonts/Supplemental/AmericanTypewriter.ttc"
    hand_path = "/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf"
    rng = np.random.default_rng(5)
    out = []
    for idx, (small, big, hand) in enumerate(CARD_TEXT):
        paper = np.zeros((h, w, 3), np.float32)
        fib = gaussian_filter(rng.standard_normal((h, w)).astype(np.float32), (0.7, 5.0))
        fib = fib / fib.std()
        blot = gaussian_filter(rng.standard_normal((h, w)).astype(np.float32), 60)
        blot = blot / blot.std()
        tone = 1.0 + 0.016 * fib + 0.02 * blot
        for i, v in enumerate((240, 230, 208)):
            paper[:, :, i] = v * tone
        img = Image.fromarray(np.clip(paper, 0, 255).astype(np.uint8)).convert("RGBA")
        ink = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(ink)
        d.rectangle([34, 34, w - 34, h - 34], outline=(152, 58, 44, 220), width=5)
        d.rectangle([48, 48, w - 48, h - 48], outline=(152, 58, 44, 150), width=2)
        f_small = find_font(type_path, "Bold", 58)
        d.text((w / 2, 122), small, font=f_small, fill=(70, 20, 20, 255),
               stroke_width=2, stroke_fill=(70, 20, 20, 255), anchor="mm")
        size = 148
        while True:
            f_big = find_font(type_path, "Bold", size)
            if d.textlength(big, font=f_big) <= w - 150 or size < 60:
                break
            size -= 6
        d.text((w / 2, 292), big, font=f_big, fill=(12, 10, 14, 255),
               stroke_width=2, stroke_fill=(12, 10, 14, 255), anchor="mm")
        d.line([(w / 2 - 150, 396), (w / 2 + 150, 396)], fill=(152, 58, 44, 180), width=3)
        size = 78
        while True:
            f_hand = ImageFont.truetype(hand_path, size)
            if d.textlength(hand, font=f_hand) <= w - 150 or size < 40:
                break
            size -= 4
        d.text((w / 2, 484), hand, font=f_hand, fill=(12, 28, 62, 255),
               stroke_width=2, stroke_fill=(12, 28, 62, 255), anchor="mm")
        # uneven stamp ink
        a = np.asarray(ink, np.float32)
        wear = gaussian_filter(rng.standard_normal((h, w)).astype(np.float32), 2.2)
        wear = np.clip(0.93 + 0.12 * wear / wear.std(), 0.70, 1.0)
        a[:, :, 3] *= wear
        ink = Image.fromarray(a.astype(np.uint8), "RGBA").filter(ImageFilter.GaussianBlur(0.35))
        ink = ink.rotate(float(rng.normal(0, 0.5)), resample=Image.BICUBIC)
        img = Image.alpha_composite(img, ink).convert("RGB")
        out.append(torch.from_numpy(to_lin(img)).permute(2, 0, 1)[None].contiguous().to(DEV))
    return out


def make_tiles():
    """Periodic 3D fields: thumb dents / lumps (displacement) and marbling swirl."""
    rng = np.random.default_rng(3)
    T = TILE

    def band(sigma):
        n = gaussian_filter(rng.standard_normal((T, T, T)).astype(np.float32), sigma, mode="wrap")
        return n / n.std()

    lumps = band(9.0)
    mid = band(3.2)
    dents = np.zeros((T, T, T), np.float32)
    zz, yy, xx = np.mgrid[0:T, 0:T, 0:T].astype(np.float32) - T / 2
    for i in range(34):
        s = rng.uniform(4.0, 8.0)
        el = rng.uniform(0.6, 1.0, 3)
        kern = np.exp(-((xx / el[0]) ** 2 + (yy / el[1]) ** 2 + (zz / el[2]) ** 2) / (2 * s * s))
        dents += np.roll(kern, tuple(int(v) for v in rng.integers(0, T, 3)), axis=(0, 1, 2))
    disp = 0.0050 * lumps + 0.0015 * mid + 0.0085 * dents
    swirl = np.sin(2.6 * band(8.0) + 1.8 * band(16.0) * 2.0)
    return disp.astype(np.float32), swirl.astype(np.float32)


def tile_to_grid(tile):
    rz, ry, rx = -(-NZ // TILE), -(-NY // TILE), -(-NX // TILE)
    return tile.repeat(rz, ry, rx)[:NZ, :NY, :NX].contiguous()


# =====================================================================================
#  Renderer
# =====================================================================================

class Renderer:
    def __init__(self):
        t0 = time.time()
        self.mat_tex = make_mat_texture()
        self.cards = make_card_textures()
        disp, swirl = make_tiles()
        self.disp_tile = torch.from_numpy(disp).to(DEV)
        self.disp_static = tile_to_grid(self.disp_tile)
        self.swirl = tile_to_grid(torch.from_numpy(swirl).to(DEV))
        self.D = torch.zeros((NZ, NY, NX), device=DEV)
        self.M = torch.zeros((5, NZ, NY, NX), device=DEV)
        self.xs = torch.arange(NX, device=DEV, dtype=torch.float32) * VOX + (GMIN[0] + 0.5 * VOX)
        self.ys = torch.arange(NY, device=DEV, dtype=torch.float32) * VOX + (GMIN[1] + 0.5 * VOX)
        self.zs = torch.arange(NZ, device=DEV, dtype=torch.float32) * VOX + (GMIN[2] + 0.5 * VOX)
        cv = VOX * COARSE
        self.cxs = torch.arange(NX // COARSE, device=DEV, dtype=torch.float32) * cv + (GMIN[0] + 0.5 * cv)
        self.cys = torch.arange(NY // COARSE, device=DEV, dtype=torch.float32) * cv + (GMIN[1] + 0.5 * cv)
        self.czs = torch.arange(NZ // COARSE, device=DEV, dtype=torch.float32) * cv + (GMIN[2] + 0.5 * cv)
        self.g0 = torch.tensor(GMIN, device=DEV, dtype=torch.float32)
        self.gscale = torch.tensor(2.0 / (GMAX - GMIN), device=DEV, dtype=torch.float32)
        self.bmin = torch.tensor(GMIN + VOX, device=DEV, dtype=torch.float32)
        self.bmax = torch.tensor(GMAX - VOX, device=DEV, dtype=torch.float32)
        fw = CAM_TGT - CAM_POS
        fw = fw / np.linalg.norm(fw)
        rt = np.cross(fw, [0.0, 1.0, 0.0])
        rt = rt / np.linalg.norm(rt)
        up = np.cross(rt, fw)
        self.cam = [torch.tensor(v, device=DEV, dtype=torch.float32) for v in (CAM_POS, rt, up, fw)]
        self.focus_depth = float(np.dot(FOCUS_AT - CAM_POS, fw))
        print("setup %.1fs on %s" % (time.time() - t0, DEV), file=sys.stderr)

    # ---------------- signed distance of one primitive ----------------
    @staticmethod
    def prim_dist(pr, X, Y, Z):
        if pr["t"] == "cap":
            ax, ay, az = pr["a"]
            bx, by, bz = pr["b"]
            pax, pay, paz = X - ax, Y - ay, Z - az
            bax, bay, baz = bx - ax, by - ay, bz - az
            den = bax * bax + bay * bay + baz * baz + 1e-8
            h = ((pax * bax + pay * bay + paz * baz) / den).clamp(0.0, 1.0)
            dx, dy, dz = pax - bax * h, pay - bay * h, paz - baz * h
            return torch.sqrt(dx * dx + dy * dy + dz * dz + 1e-10) - pr["r"]
        cx, cy, cz = pr["c"]
        lx, ly, lz = X - cx, Y - cy, Z - cz
        if pr["t"] == "tor":
            R, an = pr["R"], pr["an"]
            px = lx.abs()
            py = -ly
            sx, sy = math.sin(an), math.cos(an)
            ln = torch.sqrt(px * px + py * py + 1e-10)
            kk = torch.where(sy * px > sx * py, px * sx + py * sy, ln)
            return torch.sqrt((px * px + py * py + lz * lz + R * R - 2.0 * R * kk).clamp(min=1e-10)) - pr["r"]
        yaw, roll = pr["yaw"], pr["roll"]
        if yaw:
            c, s = math.cos(yaw), math.sin(yaw)
            lx, lz = c * lx - s * lz, s * lx + c * lz
        if roll:
            c, s = math.cos(roll), math.sin(roll)
            lx, ly = c * lx + s * ly, -s * lx + c * ly
        hx, hy, hz = pr["h"]
        tx, tz = pr["tx"], pr["tz"]
        corr = 1.0
        if (tx or tz) and hy > 1e-5:
            u = ((ly + hy) / (2.0 * hy)).clamp(0.0, 1.0)
            qx = lx.abs() - hx * (1.0 - tx * u)
            qz = lz.abs() - hz * (1.0 - tz * u)
            corr = 1.0 / math.sqrt(1.0 + max(tx * hx, tz * hz) ** 2 / (4.0 * hy * hy))
        else:
            qx = lx.abs() - hx
            qz = lz.abs() - hz
        qy = ly.abs() - hy
        ox, oy, oz = qx.clamp(min=0.0), qy.clamp(min=0.0), qz.clamp(min=0.0)
        outside = torch.sqrt(ox * ox + oy * oy + oz * oz + 1e-10)
        inside = torch.maximum(qx, torch.maximum(qy, qz)).clamp(max=0.0)
        return (outside + inside) * corr - pr["r"]

    @staticmethod
    def prim_bounds(pr):
        if pr["t"] == "cap":
            a, b = np.array(pr["a"]), np.array(pr["b"])
            return np.minimum(a, b) - pr["r"], np.maximum(a, b) + pr["r"]
        c = np.array(pr["c"])
        if pr["t"] == "tor":
            e = np.array([pr["R"] + pr["r"], pr["R"] + pr["r"], pr["r"]])
        elif pr["yaw"] or pr["roll"]:
            e = np.full(3, math.sqrt(sum(v * v for v in pr["h"])) + pr["r"])
        else:
            e = np.array(pr["h"]) + pr["r"]
        return c - e, c + e

    # ---------------- bake the clay into the grid ----------------
    def bake(self, sc):
        prims = sc["prims"]
        # 1. coarse true distance everywhere (for big empty-space steps)
        X, Y, Z = self.cxs[None, None, :], self.cys[None, :, None], self.czs[:, None, None]
        dc = torch.full((self.czs.numel(), self.cys.numel(), self.cxs.numel()), 1.0e3, device=DEV)
        for pr in prims:
            d = self.prim_dist(pr, X, Y, Z)
            k = pr["k"]
            m = (0.5 + 0.5 * (dc - d) / k).clamp(0.0, 1.0)
            dc = dc * (1.0 - m) + d * m - k * m * (1.0 - m)
        up = F.interpolate(dc[None, None], size=(NZ, NY, NX), mode="trilinear", align_corners=False)[0, 0]
        # 2. exact union, colour, activity and glow in a band round each piece
        D, M = self.D, self.M
        D.fill_(1.0e3)
        M.zero_()
        for pr in prims:
            lo, hi = self.prim_bounds(pr)
            k = pr["k"]
            pad = BAND + k + VOX
            i0 = np.clip(np.floor((lo - pad - GMIN) / VOX).astype(int), 0, [NX, NY, NZ])
            i1 = np.clip(np.ceil((hi + pad - GMIN) / VOX).astype(int), 0, [NX, NY, NZ])
            if np.any(i1 <= i0):
                continue
            sl = (slice(i0[2], i1[2]), slice(i0[1], i1[1]), slice(i0[0], i1[0]))
            d = self.prim_dist(pr, self.xs[None, None, i0[0]:i1[0]], self.ys[None, i0[1]:i1[1], None],
                               self.zs[i0[2]:i1[2], None, None])
            dprev = D[sl]
            m = (0.5 + 0.5 * (dprev - d) / k).clamp(0.0, 1.0)
            D[sl] = dprev * (1.0 - m) + d * m - k * m * (1.0 - m)
            kc = max(0.0035, k * pr["mix"])
            marb = self.swirl[sl] * (kc * 1.6) if pr["mix"] > 0.5 else 0.0
            mc = (0.5 + 0.5 * (dprev - d + marb) / kc).clamp(0.0, 1.0)
            vec = torch.tensor(list(pr["col"]) + [pr["act"], pr["glow"]], device=DEV, dtype=torch.float32)
            sub = M[(slice(None),) + sl]
            M[(slice(None),) + sl] = sub * (1.0 - mc) + vec[:, None, None, None] * mc
        # 3. thumb dents: a still field for untouched clay, a fresh one for clay that was handled
        pic = sc["pic"]
        rng = np.random.default_rng(700 + pic)
        boil = tile_to_grid(torch.roll(self.disp_tile, tuple(int(v) for v in rng.integers(8, TILE - 8, 3)), (0, 1, 2)))
        act = M[3].clamp(0.0, 1.0)
        D += self.disp_static * (1.0 - act) + boil * act
        self.Dg = torch.where(D < BAND_OK, D, torch.maximum(up - 0.016, torch.full_like(up, BAND_OK)))[None, None]
        self.Mg = M[None]
        del up, boil, dc

    def sdf(self, p):
        g = ((p - self.g0) * self.gscale - 1.0).view(1, 1, 1, -1, 3)
        return F.grid_sample(self.Dg, g, mode="bilinear", padding_mode="border", align_corners=False).view(-1)

    def material(self, p):
        g = ((p - self.g0) * self.gscale - 1.0).view(1, 1, 1, -1, 3)
        return F.grid_sample(self.Mg, g, mode="bilinear", padding_mode="border", align_corners=False).view(5, -1)

    def aabb(self, o, rd):
        safe = torch.where(rd.abs() < 1e-6, torch.full_like(rd, 1e-6), rd)
        t0 = (self.bmin - o) / safe
        t1 = (self.bmax - o) / safe
        tn = torch.minimum(t0, t1).amax(dim=1).clamp(min=0.0)
        tf = torch.maximum(t0, t1).amin(dim=1)
        return tn, tf

    def march(self, o, rd, t0, t1, steps=72, eps=0.0011):
        """Sphere-trace the clay grid. Returns hit distance per ray (INF for a miss)."""
        out = torch.full((o.shape[0],), INF, device=DEV)
        idx = torch.nonzero(t1 > t0).squeeze(1)
        if idx.numel() == 0:
            return out
        t = t0[idx].clone()
        te = t1[idx]
        oo = o[idx]
        dd = rd[idx]
        for i in range(steps):
            d = self.sdf(oo + dd * t[:, None])
            hit = d < eps
            t = torch.where(hit, t, t + d * 0.88)
            if i % 6 == 5 or i == steps - 1:
                if i == steps - 1:
                    hit = d < eps * 6.0
                out[idx[hit]] = t[hit]
                keep = (~hit) & (t < te)
                idx, t, te, oo, dd = idx[keep], t[keep], te[keep], oo[keep], dd[keep]
                if idx.numel() == 0:
                    break
        return out

    # ---------------- fine surface detail (evaluated at hit points) ----------------
    @staticmethod
    def hash3(ix, iy, iz, s):
        return torch.frac(torch.sin(ix * 127.1 + iy * 311.7 + iz * 74.7 + s) * 43758.5453)

    def fingerprint(self, p):
        """Whorls of fingerprint ridges in patches where a thumb pressed."""
        hsum = torch.zeros(p.shape[0], device=DEV)
        for cell, ang, s in ((0.150, 0.0, 1.3), (0.210, 0.9, 7.7)):
            c, sn = math.cos(ang), math.sin(ang)
            qx = (p[:, 0] * c + p[:, 2] * sn) / cell + s
            qy = p[:, 1] / cell + s * 0.37
            qz = (-p[:, 0] * sn + p[:, 2] * c) / cell - s
            ix, iy, iz = qx.floor(), qy.floor(), qz.floor()
            r1 = self.hash3(ix, iy, iz, s)
            r2 = self.hash3(ix, iy, iz, s + 1.7)
            r3 = self.hash3(ix, iy, iz, s + 3.1)
            r4 = self.hash3(ix, iy, iz, s + 4.9)
            dx = qx - ix - 0.5 - (r1 - 0.5) * 0.3
            dy = qy - iy - 0.5 - (r2 - 0.5) * 0.3
            dz = qz - iz - 0.5 - (r3 - 0.5) * 0.3
            rr = torch.sqrt(dx * dx + dy * dy + dz * dz + 1e-9)
            dist = torch.sqrt(dx * dx + (dy * (1.1 + 0.5 * r4)) ** 2 + dz * dz + 1e-9) * cell
            swirl = torch.atan2(dy, dx + dz + 1e-5)
            ridge = torch.sin(dist * (2.0 * math.pi / 0.0080) + 1.3 * torch.sin(swirl * 2.0 + r1 * 6.28))
            mask = ((0.44 - rr) / 0.20).clamp(0.0, 1.0)
            mask = mask * mask * (3.0 - 2.0 * mask) * (r4 < 0.62).float()
            hsum = hsum + ridge * mask
        return hsum

    def detail_normal(self, p, n):
        e = 0.0013
        h0 = self.fingerprint(p)
        ex = torch.tensor([e, 0.0, 0.0], device=DEV)
        ey = torch.tensor([0.0, e, 0.0], device=DEV)
        ez = torch.tensor([0.0, 0.0, e], device=DEV)
        g = torch.stack([self.fingerprint(p + ex) - h0, self.fingerprint(p + ey) - h0,
                         self.fingerprint(p + ez) - h0], dim=1) / e
        # fine palm grain
        gr = torch.stack([torch.sin(p[:, 1] * 517.0 + p[:, 2] * 331.0) * torch.sin(p[:, 0] * 433.0),
                          torch.sin(p[:, 2] * 487.0 + p[:, 0] * 293.0) * torch.sin(p[:, 1] * 389.0),
                          torch.sin(p[:, 0] * 541.0 + p[:, 1] * 311.0) * torch.sin(p[:, 2] * 463.0)], dim=1)
        g = g * 0.00030 + gr * 0.045
        g = g - (g * n).sum(1, keepdim=True) * n
        return F.normalize(n - g, dim=1), h0

    # ---------------- one sample per pixel ----------------
    def trace(self, o, rd, sc, u_light):
        N = o.shape[0]
        zero3 = torch.zeros((N, 3), device=DEV)
        # --- nearest surface ---
        tg = torch.where(rd[:, 1] < -1e-4, -o[:, 1] / rd[:, 1].clamp(max=-1e-4), torch.full((N,), INF, device=DEV))
        tw = torch.where(rd[:, 2] < -1e-4, (WALL_Z - o[:, 2]) / rd[:, 2].clamp(max=-1e-4),
                         torch.full((N,), INF, device=DEV))
        tn, tf = self.aabb(o, rd)
        tc = self.march(o, rd, tn, torch.minimum(tf, tg))
        tbest = torch.minimum(tg, tw)
        kind = torch.where(tg < tw, 2, 5)          # 2 mat/desk, 5 wall
        kind = torch.where(tc < tbest, 1, kind)    # 1 clay
        tbest = torch.minimum(tbest, tc)
        quv = torch.zeros((N, 2), device=DEV)
        qn = zero3.clone()
        qid = torch.zeros((N,), device=DEV, dtype=torch.long)
        for qi, (p0, U, V) in enumerate(sc["quads"]):
            nrm = torch.linalg.cross(U, V)
            nrm = nrm / nrm.norm()
            den = (rd * nrm).sum(1)
            tq = ((p0 - o) * nrm).sum(1) / torch.where(den.abs() < 1e-6, torch.full_like(den, 1e-6), den)
            hp = o + rd * tq[:, None] - p0
            a = (hp * U).sum(1) / (U * U).sum()
            b = (hp * V).sum(1) / (V * V).sum()
            ok = (tq > 0) & (tq < tbest) & (a >= 0) & (a <= 1) & (b >= 0) & (b <= 1)
            tbest = torch.where(ok, tq, tbest)
            kind = torch.where(ok, 3, kind)
            quv = torch.where(ok[:, None], torch.stack([a, b], 1), quv)
            qn = torch.where(ok[:, None], nrm[None, :].expand(N, 3), qn)
            qid = torch.where(ok, qi, qid)
        en = zero3.clone()
        for (ex, ey, ez, er) in sc["eyes"]:
            c = torch.tensor([ex, ey, ez], device=DEV, dtype=torch.float32)
            oc = o - c
            bq = (oc * rd).sum(1)
            disc = bq * bq - ((oc * oc).sum(1) - er * er)
            te = -bq - torch.sqrt(disc.clamp(min=0.0))
            ok = (disc > 0) & (te > 0) & (te < tbest + er * 0.6)
            tbest = torch.where(ok, torch.minimum(te, tbest), tbest)
            kind = torch.where(ok, 4, kind)
            en = torch.where(ok[:, None], F.normalize(oc + rd * te[:, None], dim=1), en)

        P = o + rd * tbest[:, None]
        Nn = torch.zeros((N, 3), device=DEV)
        Nn[:, 1] = 1.0
        alb = torch.zeros((N, 3), device=DEV)
        rough = torch.full((N,), 0.5, device=DEV)
        f0 = torch.full((N,), 0.04, device=DEV)
        sss = torch.zeros((N,), device=DEV)
        emi = torch.zeros((N, 3), device=DEV)
        pic = sc["pic"]

        # --- clay ---
        ic = torch.nonzero(kind == 1).squeeze(1)
        if ic.numel() > 0:
            pc = P[ic]
            e = 0.0062
            k1 = torch.tensor([1.0, -1.0, -1.0], device=DEV)
            k2 = torch.tensor([-1.0, -1.0, 1.0], device=DEV)
            k3 = torch.tensor([-1.0, 1.0, -1.0], device=DEV)
            k4 = torch.tensor([1.0, 1.0, 1.0], device=DEV)
            n = (k1 * self.sdf(pc + k1 * e)[:, None] + k2 * self.sdf(pc + k2 * e)[:, None]
                 + k3 * self.sdf(pc + k3 * e)[:, None] + k4 * self.sdf(pc + k4 * e)[:, None])
            n = F.normalize(n, dim=1)
            m = self.material(pc)
            a = m[0:3].t().contiguous()
            act = m[3]
            glow = m[4].clamp(0.0, 1.0)
            # handled clay gets fresh prints this picture, resting clay keeps its own
            shift = torch.tensor([0.37 * (pic % 11) + 0.11, 0.23 * (pic % 7) + 0.05, 0.41 * (pic % 5)], device=DEV)
            pd = pc + (act > 0.3).float()[:, None] * shift
            n2, fp = self.detail_normal(pd, n)
            # hand-kneaded pigment: slow value drift, dust flecks, dirt in the creases
            v = torch.sin(pd[:, 0] * 7.3 + torch.sin(pd[:, 1] * 5.1 + pd[:, 2] * 6.7) * 1.7) * \
                torch.sin(pd[:, 2] * 8.9 + torch.sin(pd[:, 0] * 4.3 + pd[:, 1] * 3.1) * 2.0)
            a = a * (1.0 + 0.085 * v)[:, None]
            a = a * (1.0 - 0.030 * fp)[:, None]
            cq = pc / 0.026
            ci = cq.floor()
            r1 = self.hash3(ci[:, 0], ci[:, 1], ci[:, 2], 2.2)
            r2 = self.hash3(ci[:, 0], ci[:, 1], ci[:, 2], 5.6)
            cf = cq - ci - 0.5
            sp = ((0.20 - torch.sqrt((cf * cf).sum(1) + 1e-9) / (0.45 + r2)) / 0.08).clamp(0.0, 1.0)
            dust = sp * (r1 < 0.16).float() * 0.55
            dark = sp * (r1 > 0.90).float() * 0.45
            a = a * (1.0 - dust)[:, None] + torch.tensor([0.62, 0.60, 0.56], device=DEV) * dust[:, None]
            a = a * (1.0 - dark)[:, None]
            cav = (1.0 - self.sdf(pc + n * 0.016) / 0.016).clamp(0.0, 1.0)
            a = a * (1.0 - 0.30 * cav)[:, None]
            rg = torch.full((ic.numel(),), 0.40, device=DEV) + 0.07 * v
            # faces: a pressed smile, rouge on the cheeks, a bindi
            for (hc, hr, yaw, style) in sc["faces"]:
                c = torch.tensor(hc, device=DEV, dtype=torch.float32)
                vv = (pc - c) / hr
                fx = vv[:, 0] * math.cos(yaw) - vv[:, 2] * math.sin(yaw)
                fz = vv[:, 0] * math.sin(yaw) + vv[:, 2] * math.cos(yaw)
                fy = vv[:, 1]
                near = ((vv * vv).sum(1) < 1.6) & (fz > 0.25)
                arc = (torch.sqrt(fx * fx + (fy - 0.02) ** 2 + 1e-9) - 0.40).abs()
                smile = ((0.050 - arc) / 0.02).clamp(0.0, 1.0) * ((-0.24 - fy) / 0.05).clamp(0.0, 1.0)
                smile = smile * near.float()
                a = a * (1.0 - smile)[:, None] + torch.tensor(srgb(110, 40, 40), device=DEV) * smile[:, None]
                ch = torch.sqrt((fx.abs() - 0.56) ** 2 + (fy + 0.16) ** 2 + 1e-9)
                blush = ((0.24 - ch) / 0.14).clamp(0.0, 1.0) * near.float() * 0.42
                a = a * (1.0 - blush)[:, None] + torch.tensor(srgb(232, 110, 104), device=DEV) * blush[:, None]
                if style == "s":
                    bd = torch.sqrt(fx * fx + (fy - 0.40) ** 2 + 1e-9)
                    bindi = ((0.075 - bd) / 0.02).clamp(0.0, 1.0) * near.float()
                    a = a * (1.0 - bindi)[:, None] + torch.tensor(RED, device=DEV) * bindi[:, None]
            Nn[ic] = n2
            alb[ic] = a
            rough[ic] = rg
            sss[ic] = 1.0
            emi[ic] = glow[:, None] * torch.tensor([2.6, 1.45, 0.42], device=DEV)

        # --- cutting mat and desk ---
        ig = torch.nonzero(kind == 2).squeeze(1)
        if ig.numel() > 0:
            pg = P[ig]
            u = (pg[:, 0] - MAT_X0) / (MAT_X1 - MAT_X0) * 2.0 - 1.0
            v = (pg[:, 2] - MAT_Z0) / (MAT_Z1 - MAT_Z0) * 2.0 - 1.0
            tx = F.grid_sample(self.mat_tex, torch.stack([u, v], 1).view(1, 1, -1, 2), mode="bilinear",
                               padding_mode="border", align_corners=False).view(4, -1)
            on_mat = ((u.abs() < 1.0) & (v.abs() < 1.0)).float()
            grain = torch.sin(pg[:, 2] * 93.0 + torch.sin(pg[:, 0] * 2.1) * 6.0 + torch.sin(pg[:, 0] * 0.7) * 9.0)
            wood = torch.tensor(srgb(96, 62, 40), device=DEV)[None, :] * (1.0 + 0.16 * grain)[:, None]
            alb[ig] = tx[0:3].t() * on_mat[:, None] + wood * (1.0 - on_mat)[:, None]
            rough[ig] = (0.62 - 0.30 * (tx[3] - 0.5)) * on_mat + 0.45 * (1.0 - on_mat)
            f0[ig] = 0.045

        # --- tent card ---
        iq = torch.nonzero(kind == 3).squeeze(1)
        if iq.numel() > 0:
            uv = quv[iq]
            tex = self.cards[sc["card"]]
            g = torch.stack([uv[:, 0] * 2.0 - 1.0, 1.0 - uv[:, 1] * 2.0], 1).view(1, 1, -1, 2)
            ca = F.grid_sample(tex, g, mode="bilinear", padding_mode="border", align_corners=False).view(3, -1).t()
            blank = torch.tensor(srgb(226, 214, 190), device=DEV)[None, :].expand(iq.numel(), 3)
            alb[iq] = torch.where((qid[iq] == 0)[:, None], ca, blank)
            nq = qn[iq]
            facing = ((nq * rd[iq]).sum(1) > 0).float()[:, None]
            Nn[iq] = nq * (1.0 - 2.0 * facing)
            rough[iq] = 0.85
            f0[iq] = 0.02
            sss[iq] = 0.25

        # --- bead eyes ---
        ie = torch.nonzero(kind == 4).squeeze(1)
        if ie.numel() > 0:
            Nn[ie] = en[ie]
            alb[ie] = 0.012
            rough[ie] = 0.30
            f0[ie] = 0.0

        # --- lighting ---
        lit = kind != 5
        il = torch.nonzero(lit).squeeze(1)
        col = torch.zeros((N, 3), device=DEV)
        iw = torch.nonzero(~lit).squeeze(1)
        if iw.numel() > 0:
            pw = P[iw]
            glowv = torch.exp(-((pw[:, 0] + 1.6) ** 2) / 9.0 - ((pw[:, 1] - 1.2) ** 2) / 5.0)
            col[iw] = torch.tensor([0.050, 0.036, 0.030], device=DEV)[None, :] * (0.25 + 1.3 * glowv)[:, None]
        if il.numel() > 0:
            p = P[il]
            n = Nn[il]
            v = -rd[il]
            a = alb[il]
            s = sss[il]
            kpos = torch.tensor(KEY_POS, device=DEV, dtype=torch.float32)
            aim = torch.tensor(KEY_AIM - KEY_POS, device=DEV, dtype=torch.float32)
            aim = aim / aim.norm()
            t1v = F.normalize(torch.linalg.cross(aim, torch.tensor([0.0, 1.0, 0.0], device=DEV)), dim=0)
            t2v = torch.linalg.cross(t1v, aim)
            ul = u_light[il]
            rr = torch.sqrt(ul[:, 0]) * KEY_RADIUS
            th = ul[:, 1] * (2.0 * math.pi)
            ls = kpos[None, :] + (rr * torch.cos(th))[:, None] * t1v + (rr * torch.sin(th))[:, None] * t2v
            L = ls - p
            dist = L.norm(dim=1)
            L = L / dist[:, None]
            centre = F.normalize(kpos[None, :] - p, dim=1)
            cosang = -(centre * aim).sum(1)
            spot = ((cosang - 0.80) / (0.955 - 0.80)).clamp(0.0, 1.0)
            spot = spot * spot * (3.0 - 2.0 * spot)
            ekey = (KEY_POWER * (0.10 + 0.90 * spot) / (dist * dist))[:, None] * torch.tensor(KEY_COL, device=DEV)
            ndl = (n * L).sum(1)
            # shadow ray through the clay grid and the card
            so = p + n * 0.007 + L * 0.004
            tn2, tf2 = self.aabb(so, L)
            vis = (self.march(so, L, tn2, torch.minimum(tf2, dist), steps=40, eps=0.0016) >= INF * 0.5).float()
            for qi, (p0, U, V) in enumerate(sc["quads"]):
                nrm = torch.linalg.cross(U, V)
                den = (L * nrm).sum(1)
                tq = ((p0 - so) * nrm).sum(1) / torch.where(den.abs() < 1e-6, torch.full_like(den, 1e-6), den)
                hp = so + L * tq[:, None] - p0
                qa = (hp * U).sum(1) / (U * U).sum()
                qb = (hp * V).sum(1) / (V * V).sum()
                blk = (tq > 0.004) & (tq < dist) & (qa >= 0) & (qa <= 1) & (qb >= 0) & (qb <= 1)
                vis = vis * (~blk).float()
            # ambient occlusion from the distance field
            ao = torch.ones(il.numel(), device=DEV)
            for dd, wgt in ((0.014, 0.42), (0.04, 0.34), (0.10, 0.26), (0.22, 0.20)):
                ao = ao - wgt * (1.0 - self.sdf(p + n * dd) / dd).clamp(0.0, 1.0)
            ao = ao.clamp(0.06, 1.0)
            # diffuse with a waxy wrap: light bleeds past the terminator, redder than the surface
            lam = ndl.clamp(min=0.0) * vis
            wrap = ((ndl + 0.42) / 1.42).clamp(0.0, 1.0) ** 2
            bleed = (wrap - ndl.clamp(min=0.0) * 0.72).clamp(min=0.0) * (0.35 + 0.65 * vis)
            thin = (self.sdf(p + L * 0.085) / 0.085).clamp(0.0, 1.0) * (0.35 - ndl).clamp(0.0, 1.0)
            warm = torch.tensor([1.22, 0.86, 0.62], device=DEV)
            diff = a * ekey * lam[:, None] * (1.0 - 0.22 * s)[:, None]
            diff = diff + (a ** 0.82) * warm * ekey * ((bleed * 0.62 + thin * 0.55) * s)[:, None]
            # room fill + bounce off the green mat
            hemi = (0.5 + 0.5 * n[:, 1])[:, None]
            amb = torch.tensor(SKY_COL, device=DEV) * hemi + torch.tensor(BOUNCE_COL, device=DEV) * (1.0 - hemi) * 2.2
            diff = diff + a * amb * ao[:, None]
            # cool rim from the window behind
            rim = torch.tensor(RIM_DIR / np.linalg.norm(RIM_DIR), device=DEV, dtype=torch.float32)
            rv = torch.ones(il.numel(), device=DEV)
            for st in (0.05, 0.13, 0.30):
                rv = torch.minimum(rv, (self.sdf(p + n * 0.012 + rim * st) / (st * 0.45)).clamp(0.0, 1.0))
            rndl = (n * rim).sum(1).clamp(min=0.0)
            diff = diff + a * torch.tensor(RIM_COL, device=DEV) * (rndl * rv * 0.85)[:, None]
            # lit windows spill onto whatever stands near
            for (lx, ly, lz, pw) in sc["lamps"]:
                lv = torch.tensor([lx, ly, lz], device=DEV, dtype=torch.float32)[None, :] - p
                d2 = (lv * lv).sum(1)
                nl = ((n * lv).sum(1) / torch.sqrt(d2 + 1e-8)).clamp(min=0.0)
                diff = diff + a * torch.tensor([1.0, 0.62, 0.24], device=DEV) * (pw * nl / (d2 + 0.012) * ao)[:, None]
            # waxy speculars (GGX)
            al = (rough[il] ** 2).clamp(min=0.01)
            hv = F.normalize(L + v, dim=1)
            ndh = (n * hv).sum(1).clamp(min=0.0)
            ndv = (n * v).sum(1).clamp(min=0.05)
            den = ndh * ndh * (al * al - 1.0) + 1.0
            dggx = al * al / (math.pi * den * den)
            fres = f0[il] + (1.0 - f0[il]) * (1.0 - (v * hv).sum(1).clamp(0.0, 1.0)) ** 5
            spec = dggx * fres / (4.0 * ndv * 1.0 + 0.2) * (ndl > 0).float() * vis * ndl.clamp(0.0, 1.0)
            rh = F.normalize(rim + v, dim=1)
            spec2 = ((n * rh).sum(1).clamp(min=0.0) ** 40) * rv * 0.22 * (f0[il] > 0).float()
            c = diff + ekey * spec[:, None] + torch.tensor(RIM_COL, device=DEV) * spec2[:, None] + emi[il]
            # the lamp mirrored in the glossy bead eyes
            eyes = (kind[il] == 4)
            if eyes.any():
                refl = -v + 2.0 * (n * v).sum(1, keepdim=True) * n
                ca = (refl * centre).sum(1)
                hl = ((ca - 0.9925) / 0.0045).clamp(0.0, 1.0) * 7.0
                c2 = (refl * rim).sum(1)
                hl2 = ((c2 - 0.985) / 0.01).clamp(0.0, 1.0) * 0.5
                c = c + (eyes.float() * hl)[:, None] * torch.tensor(KEY_COL, device=DEV) \
                    + (eyes.float() * hl2)[:, None] * torch.tensor(RIM_COL, device=DEV)
            col[il] = c
        return col

    # ---------------- a whole picture ----------------
    def render(self, sc, width, height, spp):
        self.bake(sc)
        pic = sc["pic"]
        # the tent card, put down by hand (a little differently each scene)
        rng = np.random.default_rng(40 + sc["card"])
        yaw = 0.16 + rng.normal(0, 0.02)
        x0 = -1.27 + rng.normal(0, 0.008)
        z0 = 0.72 + rng.normal(0, 0.006)
        cw, chh, lean = 0.70, 0.43, math.radians(21)
        U = np.array([math.cos(yaw), 0.0, -math.sin(yaw)]) * cw
        back = np.array([-math.sin(yaw), 0.0, -math.cos(yaw)])
        V = (np.array([0.0, 1.0, 0.0]) * math.cos(lean) + back * math.sin(lean)) * chh
        p0 = np.array([x0, 0.0, z0])
        V2 = (np.array([0.0, 1.0, 0.0]) * math.cos(lean) - back * math.sin(lean)) * chh
        p1 = p0 + back * (2.0 * chh * math.sin(lean))
        tt = lambda a: torch.tensor(a, device=DEV, dtype=torch.float32)
        sc["quads"] = [(tt(p0), tt(U), tt(V)), (tt(p1), tt(U), tt(V2))]

        cpos, rt, up, fw = self.cam
        torch.manual_seed(1234 + pic)
        N = width * height
        yy, xx = torch.meshgrid(torch.arange(height, device=DEV, dtype=torch.float32),
                                torch.arange(width, device=DEV, dtype=torch.float32), indexing="ij")
        xx, yy = xx.reshape(-1), yy.reshape(-1)
        rot = torch.rand((N, 6), device=DEV)
        acc = torch.zeros((N, 3), device=DEV)
        for s in range(spp):
            q = torch.tensor([(s * 0.7548776662) % 1.0, (s * 0.5698402909) % 1.0, (s * 0.8191725134) % 1.0,
                              (s * 0.6710436067) % 1.0, (s * 0.5497004779) % 1.0, (s * 0.3819660113) % 1.0],
                             device=DEV)
            u = torch.frac(rot + q[None, :])
            sx = (xx + u[:, 0] - width * 0.5) / height
            sy = (height * 0.5 - (yy + u[:, 1])) / height
            d = sx[:, None] * rt + sy[:, None] * up + FOCAL * fw
            d = d / d.norm(dim=1, keepdim=True)
            pf = cpos[None, :] + d * (self.focus_depth / (d * fw).sum(1, keepdim=True))
            lr = torch.sqrt(u[:, 2]) * APERTURE
            la = u[:, 3] * (2.0 * math.pi)
            o = cpos[None, :] + (lr * torch.cos(la))[:, None] * rt + (lr * torch.sin(la))[:, None] * up
            rd = F.normalize(pf - o, dim=1)
            acc += self.trace(o, rd, sc, u[:, 4:6]).clamp(max=24.0)
        img = (acc / spp).view(height, width, 3)
        return self.finish(img, pic)

    @staticmethod
    def finish(img, pic):
        """Lens and film: bloom, vignette, exposure flicker, tone curve, grain."""
        h, w, _ = img.shape
        rng = np.random.default_rng(31000 + pic)
        x = img.permute(2, 0, 1)[None]
        small = F.avg_pool2d((x - 1.1).clamp(min=0.0), 4)
        rad = max(3, int(h / 1080 * 9))
        ax = torch.arange(-3 * rad, 3 * rad + 1, device=DEV, dtype=torch.float32)
        kern = torch.exp(-ax * ax / (2.0 * rad * rad))
        kern = (kern / kern.sum()).view(1, 1, 1, -1)
        b = small.view(3, 1, small.shape[2], small.shape[3])
        b = F.conv2d(F.pad(b, (3 * rad, 3 * rad, 0, 0), mode="replicate"), kern)
        b = F.conv2d(F.pad(b, (0, 0, 3 * rad, 3 * rad), mode="replicate"), kern.transpose(2, 3))
        b = F.interpolate(b.view(1, 3, small.shape[2], small.shape[3]), size=(h, w), mode="bilinear",
                          align_corners=False)
        x = x + 0.55 * b
        yy, xx = torch.meshgrid(torch.linspace(-1, 1, h, device=DEV), torch.linspace(-1, 1, w, device=DEV),
                                indexing="ij")
        r2 = (xx * xx * (w / h) ** 2 + yy * yy) / (1.0 + (w / h) ** 2)
        x = x * (1.0 - 0.42 * r2)[None, None] * float(0.94 * (1.0 + rng.uniform(-0.014, 0.014)))
        x = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)      # filmic shoulder
        x = x.clamp(0.0, 1.0) ** (1.0 / 2.2)
        lum = x.mean(dim=1, keepdim=True)
        x = lum + (x - lum) * 1.06
        g = torch.randn((1, 1, h, w), device=DEV) * 0.013 + torch.randn((1, 3, h, w), device=DEV) * 0.005
        x = (x + g * (1.15 - lum)).clamp(0.0, 1.0)
        arr = (x[0].permute(1, 2, 0) * 255.0 + 0.5).to(torch.uint8).cpu().numpy()
        return Image.fromarray(arr, "RGB")


# =====================================================================================
#  Entry points
# =====================================================================================

def picture_for_time(t):
    return int(round((t % DURATION) / PIC_DT)) % PICTURES


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--still", type=float, help="render one picture at this time (seconds)")
    ap.add_argument("--sheet", type=str, help="comma separated times: render a contact sheet")
    ap.add_argument("--scale", type=float, default=1.0, help="resolution scale (0.5 = 960x540)")
    ap.add_argument("--spp", type=int, default=20, help="samples per pixel")
    ap.add_argument("--out", type=str, help="output file for --still / --sheet")
    ap.add_argument("--frames", type=str, help="folder for the rendered pictures (kept, so a cut-short job resumes)")
    ap.add_argument("--first", type=int, default=0)
    ap.add_argument("--last", type=int, default=PICTURES)
    ap.add_argument("--no-encode", action="store_true")
    args = ap.parse_args()
    w = int(WIDTH * args.scale) // 2 * 2
    h = int(HEIGHT * args.scale) // 2 * 2

    with torch.no_grad():
        R = Renderer()
        if args.still is not None:
            t0 = time.time()
            img = R.render(scene_for_picture(picture_for_time(args.still)), w, h, args.spp)
            img.save(args.out or "clay_still.png")
            print("still %.1fs" % (time.time() - t0), file=sys.stderr)
            return
        if args.sheet:
            times = [float(v) for v in args.sheet.split(",")]
            cols = 2 if len(times) <= 8 else 3
            rows = -(-len(times) // cols)
            sheet = Image.new("RGB", (w * cols, h * rows))
            for i, tv in enumerate(times):
                t0 = time.time()
                img = R.render(scene_for_picture(picture_for_time(tv)), w, h, args.spp)
                sheet.paste(img, ((i % cols) * w, (i // cols) * h))
                print("t=%.2f %.1fs" % (tv, time.time() - t0), file=sys.stderr)
            sheet.save(args.out or "clay_sheet.png")
            return

        frames = Path(args.frames) if args.frames else Path(tempfile.gettempdir()) / "heart-of-spades-clay-frames"
        frames.mkdir(parents=True, exist_ok=True)
        t_start = time.time()
        for pic in range(args.first, args.last):
            f = frames / ("pic_%04d_%dx%d.png" % (pic, w, h))
            if f.exists() and f.stat().st_size > 10000:
                continue
            R.render(scene_for_picture(pic), w, h, args.spp).save(f)
            done = pic - args.first + 1
            print("picture %d/%d  (%.1fs each)" % (pic + 1, PICTURES, (time.time() - t_start) / done),
                  file=sys.stderr, flush=True)
        if args.no_encode:
            return
        missing = [p for p in range(PICTURES) if not (frames / ("pic_%04d_%dx%d.png" % (p, w, h))).exists()]
        if missing:
            raise SystemExit("missing pictures: %s" % missing[:10])
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [ffmpeg, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (w, h), "-r", str(FPS),
               "-i", "-", "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p",
               "-movflags", "+faststart", str(OUT_FILE)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        for pic in range(PICTURES):
            raw = Image.open(frames / ("pic_%04d_%dx%d.png" % (pic, w, h))).convert("RGB").tobytes()
            proc.stdin.write(raw)
            proc.stdin.write(raw)        # on twos
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", errors="replace")
        if proc.wait():
            print(err, file=sys.stderr)
            raise SystemExit(1)
        Image.open(frames / ("pic_%04d_%dx%d.png" % (picture_for_time(POSTER_TIME), w, h))).save(POSTER_FILE)
        print("wrote %s\nwrote %s" % (OUT_FILE, POSTER_FILE))


if __name__ == "__main__":
    main()
