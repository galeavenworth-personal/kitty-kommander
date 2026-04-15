# kitty-kommander — Design Brief

## What this is

A terminal cockpit for orchestrating AI agent teams. It renders entirely
inside a GPU-accelerated terminal ([kitty](https://sw.kovidgoyal.net/kitty/))
using inline images via the kitty graphics protocol. No browser, no Electron.

The metaphor: **herding cats.**

Work items are yarn balls. Agents are kitties. A dependency graph of yarn
balls connected by strands is the primary visualization. Kitties sit on,
carry, and interact with the yarn balls to show who's doing what.

## Logo and existing identity

See the included files:

- `kitty-kommander-logo.png` — The project logo. A white cat at a cockpit console.
- `kitty-kommander.PNG` — Additional reference artwork.

The sprite system should feel like it belongs in the same world as this logo.

## Design principle: hard shell, soft core

The governing principle is: **govern the ecosystem, not the scratchpad.**

A cell's boundary — its status, its blockers, its completion, its
identity in the hierarchy — is strictly governed. That's the hard shell.
A cell's internals — how agents talk, what tools they use, how messy
their work-in-progress gets — is free. That's the soft core.

The Kommander never reaches into a sub-cell's internals. It only sees
the envelope: who owns it, what state it's in, what it's blocked on,
whether it's done. This means the visualization has the same discipline:

- **Cell boundaries**: rigid, legible, color-coded by group state
- **Cell internals**: organic, swarming, kitties doing cat things

The contrast between rigid infrastructure and organic workforce IS the
visual identity. The control surface (Tokyo Night panels, timestamped
logs, punch-record sidebars) is unyielding. The swarm inside the DAG
is alive.

Work matures through stages, and the visualization should reflect this:

- **Unstructured** — ephemeral agent scratch work (wisps). May not
  appear in the DAG at all.
- **Cataloged** — tracked, owned, findable. Appears as a yarn ball node.
- **Connected** — dependencies wired. Yarn strands link it to other
  nodes.
- **Published** — promoted to parent cell via federation. Visible in the
  Kommander's view. This is a deliberate act, not automatic.

Agents may create messy work freely. They must not create orphaned work.
That's the real discipline.

## The recursive cell architecture

Agents work in **cells** — small teams of up to 5 (one leader + four workers).
Cells stack recursively:

```
Kommander (the conductor)
├── Lead A → sub-cell of 4 workers
├── Lead B → sub-cell of 4 workers  
├── Lead C → direct worker (no sub-cell)
└── Lead D → sub-cell with its own sub-cells...
```

One layer: 5 agents. Two layers: 21. Three layers: 85. Nobody manages
more than four direct reports. This is how you scale from a single team
to hundreds of agents without any coordinator becoming a bottleneck.

The visualization needs to show this hierarchy. A single cell's work is
a panel showing its yarn ball DAG with kitty sprites indicating agent
states. Multiple cells mean multiple panels. The Kommander's view shows
the top-level DAG with sub-cells summarized.

## What we need designed

### 1. Kitty agent sprites (the big ask)

32-bit RGBA pixel art — cyber-operator aesthetic. Each kitty sprite answers one question:
**who is working, what are they doing, or what just changed?**

If a kitty doesn't answer one of those — it shouldn't exist.

See `SPRITES.md` for the full role/state/size matrix. The key dimensions:

**Roles** (distinguished by accent color):

| Role | Accent | Character |
|------|--------|-----------|
| Kommander | White/silver | Regal posture, commands the cockpit |
| Lead | Gold/amber | Seated upright, oversees a cell |
| Builder | Orange | Typing, ears forward — making things |
| Scout | Cyan | Leaning forward, peering — inspecting |
| Critic | Violet | Paw raised, eyes narrowed — reviewing |
| Integrator | Green | Carrying or arranging yarn balls — merging |

**States** (pose changes per state):

| State | Pose | When |
|-------|------|------|
| idle | Sitting, tail wrapped | Waiting for work |
| active | Typing, paws on controls | Executing a task |
| thinking | Head tilted, paw raised | Planning |
| blocked | Caution indicator | Stalled on a dependency |
| handoff | Carrying yarn ball | Passing work to another agent |
| done | Tail up, settled | Task complete |
| alert | Ears up, straight posture | Escalation or attention needed |

**Sizes:**

| Tier | Size | Use |
|------|------|-----|
| Badge | 16×16 | DAG node overlays, inline indicators |
| Compact | 24×24 | Task lists, agent rosters |
| Panel | 32×32 | Side panels, team displays |
| Focus | 48×48 | Detail view, selected agent |

### 2. Cell group identity

Groups of cats have real collective nouns. These map to hierarchy levels:

| Name | What it means | Visual feel |
|------|---------------|-------------|
| **Pounce** | A single cell (1 lead + workers) | Tight group, focused |
| **Clowder** | A cell with sub-cells (2 layers) | Organized cluster |
| **Destruction** | Full 3-layer deployment (dozens of agents) | Controlled chaos |
| **Glaring** | A cell that's blocked/waiting | Tense, watchful |
| **Nuisance** | A cell experiencing failures | Scattered, alert |

These could influence panel borders, background textures, or ambient
sprite decorations that convey group state at a glance.

### 3. DAG integration

Kitty sprites appear in the dependency graph alongside yarn balls:

- **Perched on node**: A kitty sitting on a yarn ball = agent owns that work item
- **Walking along edge**: Work flowing between nodes = handoff in progress
- **Carrying yarn ball**: Agent is actively moving work downstream
- **Sleeping on node**: Idle or waiting for dependency to resolve
- **Waving flag**: Blocker or escalation from that node
- **Sparkle on node**: Just completed

Persistent kitties show **ownership and state**.
Transient kitties show **change**.
Decorative kitties should be **rare**.

### 4. Updated yarn ball sprites (optional)

The current yarn balls exist (see `yarn_*.png` files). They work. But if
the kitty sprites inspire a refreshed yarn ball style — same colors, better
integration with the kitties — that's welcome. See `generate_yarn_balls.py`
for how they're currently generated (Pillow, 256×256 rendered down to 64×64).

## Color palette — Tokyo Night

Everything must use this palette. No exceptions.

```
Background:    #1a1b26  (very dark navy)
Dark panel:    #24283b  (slightly lighter panel bg)
Foreground:    #a9b1d6  (light blue-grey text)
Grey:          #565f89  (muted, de-emphasized)
Accent/Blue:   #7aa2f7  (primary accent — links, highlights)
Green:         #9ece6a  (ready, success, go)
Red:           #f7768e  (blocked, error, stop)
Yellow:        #e0af68  (in-progress, warning, active)
Violet:        #bb9af7  (review, critic role)
Cyan:          #7dcfff  (scout role, info)
Orange:        #ff9e64  (builder role)
```

## Aesthetic direction

**Cyber-operator kitties, not meme cats.** These are serious infrastructure
tokens that happen to be cats. Think tactical gear — subtle visors,
headsets, glowing tech-eye accents — not internet captions or cartoon
expressions.

See the concept art references:

- `kittydag-concept1.png` — Full cockpit mockup showing kitties perched
  on DAG nodes with status labels, connected by glowing strands. This is
  the aspirational target for the Dashboard tab. The layout maps directly
  to the existing `cockpit_dash.py` pipeline: DAG left, status panel
  right, activity log bottom.
- `kittyconcept1.png` — Single kitty close-up. Heterochromatic eyes
  (one organic, one tech), grey/silver base, seated pose. This is close
  to the Kommander at Focus size (48×48).

The concept art is more detailed than functional sprites will be. At
32×32, expect ~60% of that detail — silhouette, accent glow, and pose
will read clearly; fine gear texture will not. At 48×48, closer to 80%.
At 16×16, a colored silhouette with ears. That's fine — badge size only
needs to answer "which role" via color.

## Production pipeline

**Path: AI-generated at high res → manual cleanup → downscale.**

1. **Generate** at 256×256 or 512×512 per sprite. Prompt for the specific
   role + state + palette. Transparent background. Consistent style across
   the matrix.
2. **Clean up** artifacts manually. Ensure silhouette reads at target size.
   Ensure accent color is prominent and consistent with the role's hex.
3. **Downscale** to target sizes (48×48 Focus, 32×32 Panel, 16×16 Badge).
   Use nearest-neighbor or careful bicubic — preserve crispness.
4. **Verify** on dark background (#1a1b26). Each sprite must be legible
   at its target size without squinting.
5. **Badge fallback**: If 16×16 downscale loses too much, generate a
   simplified silhouette programmatically from the Panel sprite — extract
   dominant shape + accent color.

Output: individual PNGs at `sprites/kitties/{size}/{role}_{state}.png`.

## Technical constraints

1. **32-bit RGBA PNG, transparent backgrounds.** All sprites sit on the
   #1a1b26 terminal background. Full alpha channel for anti-aliased edges
   and glow effects. The kitty graphics protocol transmits raw RGBA to
   the GPU — no palette reduction anywhere in the pipeline.

2. **Pixel art with depth.** Not flat 16-color SNES sprites. Use the
   full 32-bit depth for smooth edges, subtle shading, and glow effects
   on tech accents (visors, eyes). But keep the pixel-art character:
   sharp forms, bold color blocking, deliberate composition. The detail
   budget is small — every pixel must earn its place.

3. **Render at high res, deliver at target size.** Generate at 256×256
   or 512×512. Downscale to target (48, 32, 16). This gives anti-aliasing
   and edge quality that hand-pixeling at target size cannot match.

4. **Terminal grid alignment.** The terminal has a character grid. Sprites
   will be placed by Graphviz (for DAG nodes) or by direct timg calls
   (for panel displays). They don't need to align to exact cell boundaries
   but should look good at the listed sizes.

5. **Dark background assumed.** These will always appear on #1a1b26 or
   #24283b. Light mode does not exist. Design for dark. Glow and accent
   colors should pop against the dark navy background.

## Deliverables we're hoping for

- Individual PNGs for the kitty roles × states matrix
- At minimum: the 6 roles × 7 states at Panel size (32×32) = 42 sprites
- Badge (16×16) and Focus (48×48) versions of the most common states
  (idle, active, blocked, done = 24 Focus sprites)
- Design direction for the group identity concepts (pounce, clowder, etc.)
- Updated yarn balls in matching pixel-art-with-depth style
- File naming: `{role}_{state}.png` per the convention in `SPRITES.md`

## Reference files in this package

### Design documents
| File | What it is |
|------|------------|
| `BRIEF.md` | This document — concept, palette, constraints, deliverables |
| `SPRITES.md` | Sprite doctrine — roles, states, sizes, file naming, discipline |
| `STACK.md` | Technical stack — orchestration engine, state protocol, rendering pipeline |
| `PANELS.md` | Panel wireframes — DAG, sidebar, Cockpit panes, and Helm (multi-cell) |

### Concept art
| File | What it is |
|------|------------|
| `kittydag-concept1.png` | Cockpit DAG mockup — aspirational, art-heavy |
| `kittyconcept1.png` | Single kitty close-up — Kommander character reference |
| `kittyTUIConcept2.png` | Four TUI panel concepts — closest to functional target |
| `kittyTUIContept1.jpg` | Same four panels at larger scale |

`kittyTUIConcept2.png` is the most useful reference. Its four quadrants
map to real components: top-left = DAG pane, bottom-right = sidebar pane,
bottom-left = Helm topology (multi-cell), top-right = aspirational
pipeline view. See `PANELS.md` for grounded wireframes of each.

### Identity and existing assets
| File | What it is |
|------|------------|
| `kitty-kommander-logo.png` | Project logo |
| `kitty-kommander.PNG` | Additional reference art |
| `yarn_ready.png` | Current yarn ball sprite (green/ready) |
| `yarn_blocked.png` | Current yarn ball sprite (red/blocked) |
| `yarn_wip.png` | Current yarn ball sprite (yellow/in-progress) |
| `yarn_open.png` | Current yarn ball sprite (grey/open) |
| `yarn_done.png` | Current yarn ball sprite (blue/done) |
| `generate_yarn_balls.py` | Pillow script that generates the current yarn balls |
