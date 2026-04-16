#!/usr/bin/env python3
"""Generate yarn-ball node sprites for the cockpit DAG.

Requires: Pillow (pip install Pillow)

Usage:
    python3 sprites/generate.py          # Generate all sprites
    python3 sprites/generate.py --preview # Generate + display via timg
"""

import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

SCRIPT_DIR = Path(__file__).parent
NODES_DIR = SCRIPT_DIR / "nodes"

# Pixel grid for chunky look, then upscale
PIXEL_GRID = 32         # small grid = chunkier pixels
RENDER_SIZE = 256        # upscale target for processing
OUTPUT_SIZE = 64         # final output

# Tokyo Night palette — state colors
STATES = {
    "ready": {
        "base": (158, 206, 106),   # #9ece6a
        "dark": (105, 155, 65),
        "light": (195, 230, 155),
        "strand": (130, 180, 80),
    },
    "blocked": {
        "base": (247, 118, 142),   # #f7768e
        "dark": (195, 75, 100),
        "light": (255, 170, 190),
        "strand": (220, 95, 115),
    },
    "wip": {
        "base": (224, 175, 104),   # #e0af68
        "dark": (175, 130, 65),
        "light": (245, 210, 155),
        "strand": (200, 155, 85),
    },
    "open": {
        "base": (86, 95, 137),     # #565f89
        "dark": (55, 62, 100),
        "light": (125, 135, 175),
        "strand": (70, 78, 120),
    },
    "done": {
        "base": (122, 162, 247),   # #7aa2f7
        "dark": (80, 115, 195),
        "light": (170, 200, 255),
        "strand": (100, 140, 220),
    },
}


def _clamp(v, lo=0, hi=255):
    return max(lo, min(hi, int(v)))


def _sphere_shade(px, py, cx, cy, r):
    """Shading factor 0.0 (deep shadow) to 1.0 (fully lit).
    Light source: top-left, slightly toward viewer."""
    dx = (px - cx) / r
    dy = (py - cy) / r
    dist2 = dx * dx + dy * dy
    if dist2 > 1.0:
        return 0.0
    nz = math.sqrt(max(0, 1.0 - dist2))
    # Light direction normalized
    lx, ly, lz = -0.50, -0.55, 0.68
    ln = math.sqrt(lx * lx + ly * ly + lz * lz)
    dot = (dx * lx + dy * ly + nz * lz) / ln
    return max(0.0, dot)


def _dist_sq(ax, ay, bx, by):
    return (ax - bx) ** 2 + (ay - by) ** 2


def draw_pixel_yarn_ball(grid_size, colors):
    """Draw a yarn ball on a small pixel grid with chunky pixel-art aesthetics."""
    img = Image.new("RGBA", (grid_size, grid_size), (0, 0, 0, 0))
    px = img.load()

    cx = cy = grid_size / 2.0
    r = grid_size / 2.0 - 2.0  # room for glow ring

    base = colors["base"]
    dark = colors["dark"]
    light = colors["light"]
    strand = colors["strand"]

    # Precompute strand distances for every pixel
    # Horizontal wrapping strands: (y_offset_frac, amplitude_frac, freq, phase)
    h_strands = [
        (-0.40, 0.06, 1.8, 0.0),
        (-0.12, 0.09, 2.0, 0.6),
        (0.16,  0.08, 2.2, 1.2),
        (0.42,  0.06, 1.5, 1.8),
    ]
    # Diagonal wrapping strands: (angle_deg, offset_frac)
    d_strands = [
        (38,  -0.22),
        (38,   0.22),
        (142, -0.18),
        (142,  0.28),
    ]

    # Strand thickness — at grid=32 this gives ~3px wide strands with clear gaps
    strand_half = r * 0.22

    for y in range(grid_size):
        for x in range(grid_size):
            pcx, pcy = x + 0.5, y + 0.5
            dist_center = math.sqrt(_dist_sq(pcx, pcy, cx, cy))
            if dist_center > r:
                continue

            shade = _sphere_shade(pcx, pcy, cx, cy, r)

            # --- Strand distance ---
            best_strand_dist = 999.0

            for (cy_off, amp, freq, phase) in h_strands:
                strand_cy = cy + cy_off * r
                wave_y = strand_cy + amp * r * math.sin(
                    freq * math.pi * (pcx - cx) / r + phase
                )
                best_strand_dist = min(best_strand_dist, abs(pcy - wave_y))

            for (angle_deg, offset_frac) in d_strands:
                rad = math.radians(angle_deg)
                cos_a, sin_a = math.cos(rad), math.sin(rad)
                dx = pcx - cx - offset_frac * r * cos_a
                dy = pcy - cy - offset_frac * r * sin_a
                perp = abs(-sin_a * dx + cos_a * dy)
                best_strand_dist = min(best_strand_dist, perp)

            on_strand = best_strand_dist < strand_half
            strand_t = best_strand_dist / strand_half if strand_half > 0 else 1.0

            # --- Base color with dramatic shading ---
            if shade < 0.30:
                t = shade / 0.30
                cr = dark[0] + (base[0] - dark[0]) * t
                cg = dark[1] + (base[1] - dark[1]) * t
                cb = dark[2] + (base[2] - dark[2]) * t
            elif shade < 0.70:
                t = (shade - 0.30) / 0.40
                cr = base[0] + (light[0] - base[0]) * t * 0.3
                cg = base[1] + (light[1] - base[1]) * t * 0.3
                cb = base[2] + (light[2] - base[2]) * t * 0.3
            else:
                t = (shade - 0.70) / 0.30
                cr = base[0] + (light[0] - base[0]) * (0.3 + 0.7 * t * t)
                cg = base[1] + (light[1] - base[1]) * (0.3 + 0.7 * t * t)
                cb = base[2] + (light[2] - base[2]) * (0.3 + 0.7 * t * t)

            if on_strand:
                # Strand: raised yarn with rounded cross-section
                ridge = 1.0 - strand_t * strand_t  # parabolic profile
                s_shade = shade * 0.5 + 0.5  # strands catch more light
                sr = strand[0] * s_shade + light[0] * ridge * 0.35
                sg = strand[1] * s_shade + light[1] * ridge * 0.35
                sb = strand[2] * s_shade + light[2] * ridge * 0.35
                # Strong blend — strand dominates
                blend = 0.6 + 0.4 * (1.0 - strand_t)
                cr = cr * (1.0 - blend) + sr * blend
                cg = cg * (1.0 - blend) + sg * blend
                cb = cb * (1.0 - blend) + sb * blend
            else:
                # Between strands: darker groove for visible texture
                groove = min(1.0, best_strand_dist / (strand_half * 2.0))
                groove_darken = 0.72 + 0.28 * groove
                cr *= groove_darken
                cg *= groove_darken
                cb *= groove_darken

            px[x, y] = (_clamp(cr), _clamp(cg), _clamp(cb), 255)

    # --- Specular glint: small, sharp, 2-3 pixels, top-left ---
    hx = cx - r * 0.28
    hy = cy - r * 0.32
    glint_r = max(1.2, r * 0.11)

    for y in range(grid_size):
        for x in range(grid_size):
            pcx, pcy = x + 0.5, y + 0.5
            if _dist_sq(pcx, pcy, cx, cy) > r * r:
                continue
            d = math.sqrt(_dist_sq(pcx, pcy, hx, hy))
            if d < glint_r:
                t = d / glint_r
                intensity = int(220 * (1.0 - t * t))
                cur = px[x, y]
                px[x, y] = (
                    _clamp(cur[0] + intensity),
                    _clamp(cur[1] + intensity),
                    _clamp(cur[2] + intensity),
                    255,
                )

    # --- Edge glow: 1-2px colored ring at ball boundary ---
    glow = Image.new("RGBA", (grid_size, grid_size), (0, 0, 0, 0))
    gp = glow.load()
    glow_inner = r - 0.8
    glow_outer = r + 2.0

    for y in range(grid_size):
        for x in range(grid_size):
            pcx, pcy = x + 0.5, y + 0.5
            d = math.sqrt(_dist_sq(pcx, pcy, cx, cy))
            if glow_inner < d < glow_outer:
                # Peak glow right at the ball edge
                edge_dist = abs(d - r)
                half_width = (glow_outer - r)
                if edge_dist < half_width:
                    t = edge_dist / half_width
                    alpha = int(170 * (1.0 - t * t))
                    gp[x, y] = (base[0], base[1], base[2], alpha)

    img = Image.alpha_composite(img, glow)
    return img


def generate_yarn_ball(state_name, colors):
    """Generate a single yarn ball sprite with pixel-art-with-depth aesthetic."""
    # Step 1: Draw at small pixel grid for chunky pixel look
    pixel_art = draw_pixel_yarn_ball(PIXEL_GRID, colors)

    # Step 2: Upscale to RENDER_SIZE with nearest-neighbor (preserves blocky pixels)
    upscaled = pixel_art.resize((RENDER_SIZE, RENDER_SIZE), Image.NEAREST)

    # Step 3: Very subtle anti-aliasing — just enough to soften staircase edges
    # without destroying the pixel grid character
    smoothed = upscaled.filter(ImageFilter.GaussianBlur(radius=1.0))
    blended = Image.blend(upscaled, smoothed, alpha=0.2)

    # Step 4: Downscale to output with LANCZOS
    result = blended.resize((OUTPUT_SIZE, OUTPUT_SIZE), Image.LANCZOS)

    return result


def main():
    NODES_DIR.mkdir(parents=True, exist_ok=True)

    for state_name, colors in STATES.items():
        sprite = generate_yarn_ball(state_name, colors)
        out_path = NODES_DIR / f"yarn_{state_name}.png"
        sprite.save(str(out_path), "PNG")
        print(f"  {state_name:10s} -> {out_path}")

    print(f"\nGenerated {len(STATES)} yarn ball sprites in {NODES_DIR}/")

    if "--preview" in sys.argv:
        paths = sorted(str(p) for p in NODES_DIR.glob("yarn_*.png"))
        if paths:
            try:
                subprocess.run(["/usr/bin/timg", "--grid=5x1", "-g", "80x20"] + paths)
            except FileNotFoundError:
                print("timg not found — install it to preview sprites")


if __name__ == "__main__":
    main()
