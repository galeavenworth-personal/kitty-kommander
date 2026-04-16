#!/usr/bin/env python3
"""Generate pixel-art kitty sprites for the cockpit DAG.

Requires: Pillow (pip install Pillow)

Usage:
    python3 scripts/generate_kitties.py                    # Generate all sprites
    python3 scripts/generate_kitties.py --preview          # Generate + display via timg
    python3 scripts/generate_kitties.py --role kommander   # Generate one role only
    python3 scripts/generate_kitties.py --size panel       # Generate one size tier only
"""

import argparse
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent
KITTY_DIR = REPO_DIR / "sprites" / "kitties"

# ── Tokyo Night Palette ─────────────────────────────────────────────────────

PALETTE = {
    "bg": (26, 27, 38),         # #1a1b26
    "dark": (36, 40, 59),       # #24283b
    "fg": (169, 177, 214),      # #a9b1d6
    "grey": (86, 95, 137),      # #565f89
    "blue": (122, 162, 247),    # #7aa2f7
    "green": (158, 206, 106),   # #9ece6a
    "red": (247, 118, 142),     # #f7768e
    "yellow": (224, 175, 104),  # #e0af68
    "violet": (187, 154, 247),  # #bb9af7
    "cyan": (125, 207, 255),    # #7dcfff
    "orange": (255, 158, 100),  # #ff9e64
}

ROLE_ACCENTS = {
    "kommander": (169, 177, 214),  # white/silver
    "lead": (224, 175, 104),       # gold/amber
    "builder": (255, 158, 100),    # orange
    "scout": (125, 207, 255),      # cyan
    "critic": (187, 154, 247),     # violet
    "integrator": (158, 206, 106), # green
}

STATES = ["idle", "active", "thinking", "blocked", "handoff", "done", "alert"]

FOCUS_STATES = ["idle", "active", "blocked", "done"]

SIZE_TIERS = {
    "panel": {"render": 128, "output": 32},
    "badge": {"render": 64, "output": 16},
    "focus": {"render": 192, "output": 48},
}

# Body colors — dark cyber-cats
BODY_BASE = (36, 40, 59)       # #24283b
BODY_DARK = (26, 27, 38)       # #1a1b26
BODY_LIGHT = (55, 60, 85)      # subtle highlight


# ── Drawing Helpers ─────────────────────────────────────────────────────────

def _blend(c1, c2, t):
    """Blend two RGB tuples by factor t (0=c1, 1=c2)."""
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def _with_alpha(rgb, a):
    """Append alpha to an RGB tuple."""
    return rgb + (a,)


def _draw_triangle(draw, points, fill):
    """Draw a filled triangle from 3 (x,y) points."""
    draw.polygon(points, fill=fill)


def _draw_ellipse(draw, cx, cy, rx, ry, fill):
    """Draw a filled ellipse centered at (cx, cy)."""
    draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=fill)


# ── Kitty Drawing ──────────────────────────────────────────────────────────

def draw_kitty(size, accent, state):
    """Draw a single kitty sprite at the given render size.

    Returns an RGBA PIL Image.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Scale factor relative to 128px reference
    s = size / 128.0

    # Center of sprite
    cx = size // 2

    # Accent-tinted body: blend base with accent for subtle role coloring
    body_tinted = _blend(BODY_BASE, accent, 0.15)
    body_tinted_light = _blend(BODY_LIGHT, accent, 0.2)

    # State-based pose adjustments
    body_tilt = 0        # horizontal body shift
    head_tilt = 0        # horizontal head shift
    ear_extra = 0        # extra ear height for alert
    tail_up = False
    paw_raised = False
    paw_extended = False
    blocked_mark = False
    lean_forward = False
    eye_wide = False

    if state == "idle":
        pass  # default pose
    elif state == "active":
        lean_forward = True
        body_tilt = int(3 * s)
        paw_extended = True
    elif state == "thinking":
        head_tilt = int(5 * s)
        paw_raised = True
    elif state == "blocked":
        blocked_mark = True
    elif state == "handoff":
        paw_extended = True
        body_tilt = int(-2 * s)
    elif state == "done":
        tail_up = True
    elif state == "alert":
        ear_extra = int(6 * s)
        eye_wide = True

    # ── Tail ──
    tail_x = cx - int(22 * s) + body_tilt
    tail_base_y = int(88 * s)

    if state == "idle":
        # Tail curled around body base — accent tip
        for i in range(12):
            t = i / 11
            tx = tail_x - int(8 * s * t) + int(15 * s * t * t)
            ty = tail_base_y + int(8 * s * math.sin(t * math.pi))
            tr = max(int((3 - t * 1.5) * s), int(1 * s))
            col = _blend(body_tinted, accent, max(0, t - 0.5) * 1.2)
            _draw_ellipse(draw, tx, ty, tr, tr, _with_alpha(col, 255))
    elif tail_up:
        # Tail extends upward — done state, strong accent gradient
        for i in range(14):
            t = i / 13
            tx = tail_x - int(12 * s * t)
            ty = tail_base_y - int(35 * s * t)
            tr = max(int((3 - t * 1.5) * s), int(1 * s))
            col = _blend(body_tinted, accent, t * 0.7)
            _draw_ellipse(draw, tx, ty, tr, tr, _with_alpha(col, 255))
    else:
        # Default tail — accent tip on last third
        for i in range(12):
            t = i / 11
            tx = tail_x - int(15 * s * t)
            ty = tail_base_y - int(8 * s * t) + int(5 * s * math.sin(t * 2))
            tr = max(int((3 - t * 1.5) * s), int(1 * s))
            col = _blend(body_tinted, accent, max(0, t - 0.6) * 1.5)
            _draw_ellipse(draw, tx, ty, tr, tr, _with_alpha(col, 255))

    # ── Body ── (oval torso, bottom 60%)
    body_cx = cx + body_tilt
    body_cy = int(78 * s)
    body_rx = int(22 * s)
    body_ry = int(26 * s)

    if lean_forward:
        body_cy -= int(2 * s)

    # Body shadow (depth)
    _draw_ellipse(draw, body_cx + int(2 * s), body_cy + int(2 * s),
                  body_rx, body_ry, _with_alpha(BODY_DARK, 180))
    # Body fill — accent-tinted
    _draw_ellipse(draw, body_cx, body_cy, body_rx, body_ry,
                  _with_alpha(body_tinted, 255))
    # Body highlight (top-left) — accent-tinted
    _draw_ellipse(draw, body_cx - int(5 * s), body_cy - int(8 * s),
                  int(12 * s), int(10 * s), _with_alpha(body_tinted_light, 140))

    # ── Accent chest patch (prominent role color on torso) ──
    chest_y = body_cy - int(6 * s)
    _draw_ellipse(draw, body_cx, chest_y, int(11 * s), int(10 * s),
                  _with_alpha(accent, 55))

    # ── Accent collar / chest marking (strong band) ──
    collar_y = body_cy - int(18 * s)
    _draw_ellipse(draw, body_cx, collar_y, int(14 * s), int(4 * s),
                  _with_alpha(accent, 200))

    # ── Paws ── (at base of body)
    paw_y = body_cy + int(22 * s)
    paw_r = int(5 * s)

    if paw_extended:
        # One paw extended forward/outward
        _draw_ellipse(draw, body_cx - int(10 * s), paw_y, paw_r, int(3 * s),
                      _with_alpha(body_tinted, 255))
        _draw_ellipse(draw, body_cx + int(18 * s), paw_y - int(5 * s),
                      paw_r + int(2 * s), int(3 * s),
                      _with_alpha(body_tinted, 255))
    elif paw_raised:
        # One paw raised near chin (thinking)
        _draw_ellipse(draw, body_cx - int(10 * s), paw_y, paw_r, int(3 * s),
                      _with_alpha(body_tinted, 255))
        _draw_ellipse(draw, body_cx + int(8 * s), body_cy - int(20 * s),
                      int(4 * s), int(4 * s),
                      _with_alpha(body_tinted, 255))
    else:
        # Standard sitting paws
        _draw_ellipse(draw, body_cx - int(10 * s), paw_y, paw_r, int(3 * s),
                      _with_alpha(body_tinted, 255))
        _draw_ellipse(draw, body_cx + int(10 * s), paw_y, paw_r, int(3 * s),
                      _with_alpha(body_tinted, 255))

    # ── Head ── (circle overlapping top of body)
    head_cx = body_cx + head_tilt
    head_cy = int(44 * s)
    head_r = int(18 * s)

    # Head shadow
    _draw_ellipse(draw, head_cx + int(2 * s), head_cy + int(2 * s),
                  head_r, head_r, _with_alpha(BODY_DARK, 160))
    # Head fill — accent-tinted
    _draw_ellipse(draw, head_cx, head_cy, head_r, head_r,
                  _with_alpha(body_tinted, 255))
    # Head highlight
    _draw_ellipse(draw, head_cx - int(4 * s), head_cy - int(5 * s),
                  int(10 * s), int(8 * s), _with_alpha(body_tinted_light, 120))

    # ── Ears ── (triangles on top of head)
    ear_h = int(14 * s) + ear_extra
    ear_w = int(10 * s)
    ear_base_y = head_cy - int(12 * s)

    # Left ear
    left_ear = [
        (head_cx - int(14 * s), ear_base_y),
        (head_cx - int(14 * s) - ear_w // 2, ear_base_y - ear_h),
        (head_cx - int(14 * s) + ear_w // 2 + int(3 * s), ear_base_y),
    ]
    _draw_triangle(draw, left_ear, _with_alpha(body_tinted, 255))
    # Left ear — large accent fill (covers top 60% of ear)
    le_base_mid = ((left_ear[0][0] + left_ear[2][0]) // 2,
                   left_ear[0][1] - int(ear_h * 0.35))
    ear_fill_l = [
        (left_ear[1][0], left_ear[1][1]),
        (le_base_mid[0] + int(5 * s), le_base_mid[1]),
        (le_base_mid[0] - int(5 * s), le_base_mid[1]),
    ]
    _draw_triangle(draw, ear_fill_l, _with_alpha(accent, 230))

    # Right ear
    right_ear = [
        (head_cx + int(14 * s), ear_base_y),
        (head_cx + int(14 * s) + ear_w // 2, ear_base_y - ear_h),
        (head_cx + int(14 * s) - ear_w // 2 - int(3 * s), ear_base_y),
    ]
    _draw_triangle(draw, right_ear, _with_alpha(body_tinted, 255))
    # Right ear — large accent fill
    re_base_mid = ((right_ear[0][0] + right_ear[2][0]) // 2,
                   right_ear[0][1] - int(ear_h * 0.35))
    ear_fill_r = [
        (right_ear[1][0], right_ear[1][1]),
        (re_base_mid[0] + int(5 * s), re_base_mid[1]),
        (re_base_mid[0] - int(5 * s), re_base_mid[1]),
    ]
    _draw_triangle(draw, ear_fill_r, _with_alpha(accent, 230))

    # ── Eyes ──
    eye_y = head_cy + int(2 * s)
    eye_sep = int(8 * s)
    eye_r = int(3 * s) if eye_wide else int(2.5 * s)

    # Left eye — normal (white/light)
    _draw_ellipse(draw, head_cx - eye_sep + head_tilt, eye_y,
                  eye_r, eye_r, _with_alpha((220, 225, 240), 255))

    # Right eye — tech eye (accent color with strong glow)
    tech_eye_x = head_cx + eye_sep + head_tilt
    # Outer glow halo
    glow_r2 = eye_r + int(5 * s)
    _draw_ellipse(draw, tech_eye_x, eye_y, glow_r2, glow_r2,
                  _with_alpha(accent, 35))
    # Inner glow
    glow_r = eye_r + int(3 * s)
    _draw_ellipse(draw, tech_eye_x, eye_y, glow_r, glow_r,
                  _with_alpha(accent, 80))
    # Tech eye
    _draw_ellipse(draw, tech_eye_x, eye_y, eye_r, eye_r,
                  _with_alpha(accent, 255))
    # Bright center dot
    _draw_ellipse(draw, tech_eye_x, eye_y, max(int(1 * s), 1), max(int(1 * s), 1),
                  _with_alpha((255, 255, 255), 200))

    if state == "blocked":
        # X-shaped eyes override
        x_size = int(3 * s)
        for ex in [head_cx - eye_sep + head_tilt, head_cx + eye_sep + head_tilt]:
            for dx, dy in [(-x_size, -x_size), (x_size, x_size),
                           (-x_size, x_size), (x_size, -x_size)]:
                draw.line([(ex - dx, eye_y - dy), (ex + dx, eye_y + dy)],
                          fill=_with_alpha(PALETTE["red"], 220),
                          width=max(int(1.5 * s), 1))

    # ── Nose / mouth (tiny) ──
    nose_y = eye_y + int(5 * s)
    _draw_ellipse(draw, head_cx + head_tilt, nose_y,
                  int(1.5 * s), int(1 * s), _with_alpha(accent, 180))

    # ── Blocked mark (red ! above head) ──
    if blocked_mark:
        mark_y = head_cy - head_r - int(12 * s)
        mark_x = head_cx
        mark_s = int(5 * s)
        draw.line([(mark_x, mark_y - mark_s), (mark_x, mark_y + int(2 * s))],
                  fill=_with_alpha(PALETTE["red"], 240),
                  width=max(int(2.5 * s), 1))
        _draw_ellipse(draw, mark_x, mark_y + int(5 * s),
                      int(1.5 * s), int(1.5 * s),
                      _with_alpha(PALETTE["red"], 240))

    return img


def draw_badge_kitty(size, accent, state):
    """Draw a simplified kitty for badge size (16x16 output).

    At small sizes, detail is lost — accent color must be the dominant
    visual feature. Uses accent-tinted body, large colored ears, bright
    eye glow, and an accent chest stripe.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    s = size / 64.0
    cx = size // 2

    # Accent-tinted body for badge — stronger tint than panel
    body_tinted = _blend(BODY_BASE, accent, 0.25)

    # ── Body silhouette (accent-tinted) ──
    body_cy = int(40 * s)
    body_rx = int(18 * s)
    body_ry = int(20 * s)
    _draw_ellipse(draw, cx, body_cy, body_rx, body_ry,
                  _with_alpha(body_tinted, 255))

    # ── Accent chest stripe (prominent color band across torso) ──
    _draw_ellipse(draw, cx, body_cy - int(6 * s), int(14 * s), int(7 * s),
                  _with_alpha(accent, 80))

    # ── Head (accent-tinted) ──
    head_cy = int(22 * s)
    head_r = int(15 * s)
    _draw_ellipse(draw, cx, head_cy, head_r, head_r,
                  _with_alpha(body_tinted, 255))

    # ── Ears (large, accent-filled — key silhouette + color signal) ──
    ear_h = int(12 * s)
    if state == "alert":
        ear_h = int(16 * s)

    left_ear = [
        (cx - int(12 * s), head_cy - int(8 * s)),
        (cx - int(16 * s), head_cy - int(8 * s) - ear_h),
        (cx - int(5 * s), head_cy - int(10 * s)),
    ]
    right_ear = [
        (cx + int(12 * s), head_cy - int(8 * s)),
        (cx + int(16 * s), head_cy - int(8 * s) - ear_h),
        (cx + int(5 * s), head_cy - int(10 * s)),
    ]
    # Fill entire ears with accent color — at 16px this IS the identity
    _draw_triangle(draw, left_ear, _with_alpha(accent, 220))
    _draw_triangle(draw, right_ear, _with_alpha(accent, 220))

    # ── Accent eye dot (large, with strong glow) ──
    eye_y = head_cy + int(2 * s)
    eye_x = cx + int(4 * s)
    eye_r = int(4 * s)

    # Wide glow halo
    _draw_ellipse(draw, eye_x, eye_y, eye_r + int(4 * s), eye_r + int(4 * s),
                  _with_alpha(accent, 40))
    # Inner glow
    _draw_ellipse(draw, eye_x, eye_y, eye_r + int(2 * s), eye_r + int(2 * s),
                  _with_alpha(accent, 80))
    # Eye
    _draw_ellipse(draw, eye_x, eye_y, eye_r, eye_r,
                  _with_alpha(accent, 255))

    # Second eye (dimmer)
    _draw_ellipse(draw, cx - int(4 * s), eye_y, int(2.5 * s), int(2.5 * s),
                  _with_alpha((200, 205, 220), 220))

    # ── State indicator ──
    if state == "blocked":
        # Red dot above head
        _draw_ellipse(draw, cx, int(4 * s), int(4 * s), int(4 * s),
                      _with_alpha(PALETTE["red"], 240))
    elif state == "done":
        # Accent tail flourish upward
        tail_x = cx - int(16 * s)
        for i in range(6):
            t = i / 5
            ty = body_cy + int(10 * s) - int(22 * s * t)
            tx = tail_x - int(3 * s * t)
            _draw_ellipse(draw, tx, ty, int(2.5 * s), int(2.5 * s),
                          _with_alpha(accent, int(230 * (1 - t * 0.4))))
    elif state == "active":
        # Forward lean — shift body slightly
        pass  # accent color carries identity at this size

    return img


# ── Sprite Generation Pipeline ──────────────────────────────────────────────

def generate_sprite(role, state, tier):
    """Generate a single kitty sprite for the given role, state, and tier."""
    accent = ROLE_ACCENTS[role]
    render_size = SIZE_TIERS[tier]["render"]
    output_size = SIZE_TIERS[tier]["output"]

    if tier == "badge":
        img = draw_badge_kitty(render_size, accent, state)
    else:
        img = draw_kitty(render_size, accent, state)

    # Apply subtle Gaussian blur before downscale for anti-aliasing
    if render_size > output_size * 2:
        blur_radius = max(render_size / output_size * 0.3, 0.5)
        img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    # Downscale with LANCZOS
    result = img.resize((output_size, output_size), Image.LANCZOS)

    return result


def generate_all(roles=None, tiers=None):
    """Generate all kitty sprites. Returns list of (path, role, state, tier)."""
    if roles is None:
        roles = list(ROLE_ACCENTS.keys())
    if tiers is None:
        tiers = list(SIZE_TIERS.keys())

    generated = []

    for tier in tiers:
        tier_dir = KITTY_DIR / tier
        tier_dir.mkdir(parents=True, exist_ok=True)

        states = FOCUS_STATES if tier == "focus" else STATES

        for role in roles:
            for state in states:
                sprite = generate_sprite(role, state, tier)
                out_path = tier_dir / f"{role}_{state}.png"
                sprite.save(str(out_path), "PNG")
                generated.append((out_path, role, state, tier))

    return generated


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate pixel-art kitty sprites for the cockpit DAG"
    )
    parser.add_argument("--preview", action="store_true",
                        help="Display generated sprites via timg after generation")
    parser.add_argument("--role", choices=list(ROLE_ACCENTS.keys()),
                        help="Generate sprites for one role only")
    parser.add_argument("--size", choices=list(SIZE_TIERS.keys()),
                        help="Generate sprites for one size tier only")
    args = parser.parse_args()

    roles = [args.role] if args.role else None
    tiers = [args.size] if args.size else None

    print("Generating kitty sprites...")
    generated = generate_all(roles=roles, tiers=tiers)

    # Print summary grouped by tier
    by_tier = {}
    for path, role, state, tier in generated:
        by_tier.setdefault(tier, []).append((path, role, state))

    for tier in sorted(by_tier.keys()):
        items = by_tier[tier]
        output_size = SIZE_TIERS[tier]["output"]
        print(f"\n  {tier} ({output_size}x{output_size}): {len(items)} sprites")
        for path, role, state in items:
            print(f"    {role}_{state}.png")

    print(f"\nTotal: {len(generated)} sprite PNGs in {KITTY_DIR}/")

    if args.preview:
        # Show a grid per tier
        for tier in sorted(by_tier.keys()):
            items = by_tier[tier]
            paths = [str(p) for p, _, _ in items]
            if paths:
                print(f"\n--- {tier} ---")
                try:
                    subprocess.run(
                        ["/usr/bin/timg", "--grid=7x6", "-g", "120x40"] + paths[:42]
                    )
                except FileNotFoundError:
                    print("timg not found — install it to preview sprites")


if __name__ == "__main__":
    main()
