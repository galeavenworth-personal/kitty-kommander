#!/usr/bin/env python3
"""Generate yarn-ball node sprites for the cockpit DAG.

Requires: Pillow (pip install Pillow)

Usage:
    python3 sprites/generate.py          # Generate all sprites
    python3 sprites/generate.py --preview # Generate + display via timg
"""

import math
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

SCRIPT_DIR = Path(__file__).parent
NODES_DIR = SCRIPT_DIR / "nodes"

# Render at high res, downscale for quality
RENDER_SIZE = 256
OUTPUT_SIZE = 64

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


def draw_yarn_strands(draw, cx, cy, r, strand_color, width=4):
    """Draw curved yarn strand lines across the ball surface."""
    # Horizontal wraps
    for offset_pct in [-0.35, -0.1, 0.15, 0.4]:
        y_off = int(r * offset_pct)
        # Elliptical arc simulating a wrap around the sphere
        squash = math.sqrt(max(0, 1 - (offset_pct ** 2) * 1.5))
        arc_h = int(r * 0.35 * squash)
        arc_w = int(r * 0.85)
        bbox = [cx - arc_w, cy + y_off - arc_h, cx + arc_w, cy + y_off + arc_h]
        draw.arc(bbox, start=10, end=170, fill=strand_color + (160,), width=width)

    # Diagonal wraps
    for angle, offset_pct in [(30, -0.2), (30, 0.2), (150, -0.15), (150, 0.25)]:
        rad = math.radians(angle)
        x_off = int(r * offset_pct * math.cos(rad))
        y_off = int(r * offset_pct * math.sin(rad))
        arc_r = int(r * 0.7)
        bbox = [cx - arc_r + x_off, cy - arc_r + y_off,
                cx + arc_r + x_off, cy + arc_r + y_off]
        draw.arc(bbox, start=angle - 70, end=angle + 70,
                 fill=strand_color + (120,), width=width - 1)


def generate_yarn_ball(state_name, colors):
    """Generate a single yarn ball sprite."""
    size = RENDER_SIZE
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    r = size // 2 - 12

    # --- Base filled circle ---
    draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                 fill=colors["base"] + (255,))

    # --- Spherical shading (darker toward bottom-right) ---
    shade = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shade_draw = ImageDraw.Draw(shade)
    # Gradient: draw concentric offset circles getting darker
    steps = 20
    for i in range(steps):
        t = i / steps
        alpha = int(90 * t)
        offset = int(r * 0.25 * t)
        shade_r = int(r * (1.0 - t * 0.3))
        shade_draw.ellipse(
            [cx - shade_r + offset, cy - shade_r + offset,
             cx + shade_r + offset, cy + shade_r + offset],
            fill=colors["dark"] + (alpha,),
        )
    # Clip shading to ball shape
    ball_mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(ball_mask).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    shade.putalpha(Image.composite(shade.split()[3], Image.new("L", (size, size), 0), ball_mask))
    img = Image.alpha_composite(img, shade)

    # --- Yarn strands ---
    strand_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    strand_draw = ImageDraw.Draw(strand_layer)
    draw_yarn_strands(strand_draw, cx, cy, r, colors["strand"], width=5)
    # Clip strands to ball
    strand_layer.putalpha(
        Image.composite(strand_layer.split()[3], Image.new("L", (size, size), 0), ball_mask)
    )
    img = Image.alpha_composite(img, strand_layer)

    # --- Specular highlight (upper-left) ---
    highlight = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    h_draw = ImageDraw.Draw(highlight)
    h_cx = cx - int(r * 0.3)
    h_cy = cy - int(r * 0.3)
    h_r = int(r * 0.35)
    h_draw.ellipse([h_cx - h_r, h_cy - h_r, h_cx + h_r, h_cy + h_r],
                   fill=(255, 255, 255, 70))
    highlight = highlight.filter(ImageFilter.GaussianBlur(radius=20))
    highlight.putalpha(
        Image.composite(highlight.split()[3], Image.new("L", (size, size), 0), ball_mask)
    )
    img = Image.alpha_composite(img, highlight)

    # --- Final anti-aliased circular mask ---
    final_mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(final_mask).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    final_mask = final_mask.filter(ImageFilter.GaussianBlur(radius=2))
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(img, mask=final_mask)

    # --- Downscale ---
    result = result.resize((OUTPUT_SIZE, OUTPUT_SIZE), Image.LANCZOS)

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
