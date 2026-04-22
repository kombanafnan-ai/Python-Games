# ADAPTIVE DARK 3D
### First-Person Psychological Horror Game
> *"She is watching. She remembers. She adapts."*

---

## QUICK START

```bash
pip install pygame
python game3d.py
```

---

## REQUIREMENTS

| Item        | Details                          |
|-------------|----------------------------------|
| Python      | 3.8 or higher                    |
| Pygame      | 2.0 or higher (`pip install pygame`) |
| Screen      | 960 x 640 minimum                |
| OS          | Windows / macOS / Linux          |
| Extra libs  | None — pure Python + Pygame only |

---

## CONTROLS

| Key / Input           | Action                              |
|-----------------------|-------------------------------------|
| **W** / Up Arrow      | Move forward                        |
| **S** / Down Arrow    | Move backward                       |
| **A**                 | Strafe left                         |
| **D**                 | Strafe right                        |
| **Mouse move**        | Look left / right (primary)         |
| **Left Arrow**        | Look left (keyboard fallback)       |
| **Right Arrow**       | Look right (keyboard fallback)      |
| **Left Shift**        | Run — faster but drains stamina     |
| **E**                 | Interact (pick up key, read notes, use exit) |
| **ESC**               | Quit game                           |

> Mouse is captured during gameplay. Press **ESC** to release it.

---

## OBJECTIVE

You are trapped inside a dark abandoned facility.

1. Explore the corridors in **first-person 3D**
2. Find the **KEY** hidden in the **northeast** section of the map
3. Carry the key to the **EXIT DOOR** in the **southeast** corner
4. Escape without being caught by the ghost

**Bonus goal:** Find all **5 hidden notes** scattered around the map
to piece together the full backstory of what happened here.

---

## THE GHOST — Human Entity

The ghost is a **tall pale woman** rendered as a 3D billboard sprite,
drawn entirely with procedural code — no image files used.

### Appearance
- Long dark flowing hair hanging down to her waist
- Pale blue-white glowing body
- Hollow black eye sockets
- Red glowing pupils — only visible when she is chasing you
- Flowing white dress with vertical fold lines
- Arms hanging loosely at her sides
- Ghostly aura glow around her head

### Ghost Color by State

| Color              | Ghost State                        |
|--------------------|------------------------------------|
| Pale blue-white    | Patrolling — unaware of you        |
| Orange-white       | Alerted — investigating a sound    |
| Bright red-white   | Chasing — she has seen you         |
| Purple             | Ambush — silently waiting for you  |

### Visual Behaviour by Phase

| Phase | Visual Effect                                      |
|-------|----------------------------------------------------|
| I     | Always visible, steady glow                        |
| II    | Randomly flickers — 4% chance to vanish per frame  |
| III   | Heavy flickering — 8% chance in ambush mode        |

---

## ADAPTIVE AI — 3 Phases

The ghost **learns your behaviour** over time. She is never scripted.
The longer you play, the smarter and faster she becomes.

---

### Phase I — AWARENESS
*Active from the start of the game.*

- Patrols 12 random waypoints across the map
- Reacts to **sight** (direct line-of-view up to 7 tiles)
- Reacts to **sound** (your movement within 3.5 tiles)
- Chases toward your **last known position** after losing sight
- Speed: **1.6 units/sec** (patrol: 0.55x = ~0.88 u/s)
- Switches to **Search** mode if she loses you for 2.2 seconds

---

### Phase II — ADAPTATION
*Triggers after ~250 total observations (~5 minutes of play).*

- Builds a **tile heat map** — records every tile you visit
- Hunts toward the tiles you visit **most frequently**
- **Predicts** where you are heading using your velocity (2.5 tiles ahead)
- Intercepts rather than just following
- Ghost begins to **flicker** visually
- Speed increases to **1.9 units/sec**
- Switches to **Hunt** mode when she loses you (smarter search)

---

### Phase III — MASTERY
*Triggers after ~600 total observations (~12 minutes of play).*

- Activates **Ambush mode** — pre-positions near your predicted route
- Small random chance (0.08%) each frame to enter ambush from patrol
- Speed increases to **2.4 units/sec**
- Maximum visual flickering in ambush state
- Extremely difficult to avoid at this phase

**Survival tip:** Never walk the same corridor twice.
Change your route constantly. Be completely unpredictable.

---

## AI STATE MACHINE

```
PATROL --> ALERT --> CHASE --> SEARCH (Phase I)
                           --> HUNT   (Phase II+)
                           --> AMBUSH (Phase III)
```

| State   | Trigger                              | Speed Multiplier |
|---------|--------------------------------------|-----------------|
| Patrol  | Default state                        | 0.55x           |
| Alert   | Heard or saw player briefly          | 0.75x           |
| Chase   | Direct line of sight to player       | 1.0x (full)     |
| Search  | Lost player (Phase I)                | 0.65x           |
| Hunt    | Lost player (Phase II+)              | 1.05x           |
| Ambush  | Predicted player route (Phase III)   | 1.15x           |

---

## PLAYER SYSTEMS

### First-Person View
- Full **mouse look** with sensitivity of 0.002 rad/pixel
- **WASD movement** with diagonal normalisation
- **Wall collision** with 0.22 unit margin
- **Field of view:** 60 degrees

### Camera Bob
- Subtle up-down camera motion when walking (1.5px amplitude)
- Stronger bob when running (3px amplitude)
- Smoothly eases out when you stop

### Sanity Meter
Sanity drains when the ghost is within **65% of her 7-tile sight range** (~4.55 tiles).

| Sanity Level | Effect                                        |
|--------------|-----------------------------------------------|
| 100% – 50%   | Normal view                                   |
| 50% – 25%    | Red screen overlay appears and intensifies    |
| 25% – 10%    | Scanline effect + horizontal screen glitching |
| Below 10%    | Heavy pulsing red vignette                    |
| 0%           | **GAME OVER** — psychological collapse        |

- Drain rate: **9 units/sec** near ghost
- Recovery rate: **1.4 units/sec** when safe

### Stamina Bar
- Hold **Shift** to run at **1.7x** normal speed
- Drain rate: **18 units/sec** while running
- Recovery rate: **7 units/sec** while walking or standing

### Screen Shake
- Activates when the ghost is very close
- Intensity scales from 0 to 6 pixels based on proximity

---

## WORLD OBJECTS

| Object     | Location         | How to use              |
|------------|------------------|-------------------------|
| Key        | Northeast (19.5, 2.5)  | Walk close + press **E** |
| Exit Door  | Southeast (22.5, 14.5) | Walk close + press **E** (need key) |
| Note 1     | (5.5, 5.5)       | Walk close + press **E** |
| Note 2     | (11.5, 3.5)      | Walk close + press **E** |
| Note 3     | (16.5, 9.5)      | Walk close + press **E** |
| Note 4     | (3.5, 13.5)      | Walk close + press **E** |
| Note 5     | (20.5, 11.5)     | Walk close + press **E** |

All objects are rendered as **3D billboard sprites** that scale with distance
and are correctly occluded behind walls using the Z-buffer.

---

## NOTES AND LORE

Five notes reveal the story of the facility and the ghost's origin.

| Note | Author             | Hint                                        |
|------|--------------------|---------------------------------------------|
| 1    | Unknown survivor   | Day 12 journal — something is in the halls  |
| 2    | Unknown survivor   | Warning — do not go to the basement         |
| 3    | Unknown survivor   | Observation — she remembers your hiding spots |
| 4    | Unknown survivor   | Key location hint + pattern warning         |
| 5    | Dr. Elara Voss     | The creator's confession — she built the entity |

---

## AUDIO

All audio is **procedurally generated** using `pygame.sndarray`.
No audio files are required.

| Sound      | Trigger                              | Type        |
|------------|--------------------------------------|-------------|
| Heartbeat  | Continuous — speeds up near ghost    | 65 Hz sine  |
| Alert tone | Ghost enters Alert state             | 520 Hz square |
| Chase tone | Ghost enters Chase state             | 320 Hz square |
| Footsteps  | Player is moving                     | 180 Hz sine |

Heartbeat interval ranges from **1.6 seconds** (safe) down to
**0.25 seconds** (ghost almost touching you).

> Audio is silently disabled if `pygame.mixer` is unavailable
> on your system.

---

## HUD ELEMENTS

| Element         | Location      | Description                              |
|-----------------|---------------|------------------------------------------|
| Sanity bar      | Top-left      | Green > Yellow > Red as it drains        |
| Stamina bar     | Top-left      | Cyan bar, drains when running            |
| KEY indicator   | Top-left      | Appears in yellow when key is collected  |
| Threat phase    | Top-right     | I / II / III with colour coding          |
| Entity state    | Top-right     | Current ghost AI state in text           |
| Timer           | Top-right     | Elapsed time MM:SS                       |
| Crosshair       | Centre        | Subtle 4-line crosshair                  |
| Interact hint   | Centre-bottom | Shows [E] prompt when near an object     |
| Controls hint   | Bottom-centre | Fades out after 25 seconds               |
| Minimap         | Top-right corner | Small overhead map overlay            |

### Minimap Key
| Symbol      | Meaning                           |
|-------------|-----------------------------------|
| Green dot   | Your position                     |
| Green line  | Your facing direction             |
| Red dot     | Ghost (chasing / hunting)         |
| Orange dot  | Ghost (alerted)                   |
| Purple dot  | Ghost (patrol / ambush)           |
| Dark blocks | Walls                             |

---

## GAME OVER CONDITIONS

| Condition                | Description                              |
|--------------------------|------------------------------------------|
| Caught by ghost          | Ghost comes within 0.65 units of you     |
| Sanity reaches zero      | Your mind collapses from sustained fear  |

---

## WIN CONDITION

Reach the **EXIT DOOR** while carrying the **KEY**.
The win screen shows your total survival time and how many notes you found.

---

## TECHNICAL REFERENCE

| Feature               | Implementation Detail                            |
|-----------------------|--------------------------------------------------|
| 3D engine             | DDA raycasting — 960 rays per frame (one per pixel column) |
| Field of view         | 60 degrees (pi/3 radians)                        |
| Max render distance   | 20 world units                                   |
| Fisheye correction    | `depth * cos(ray_angle)`                         |
| Wall shading          | Distance-based brightness + side darkening (0.6x N/S walls) |
| Wall texture          | Procedural brick variation using `(map_x + map_y) % 3` |
| Floor/ceiling         | Per-scanline gradient, no raycasting             |
| Sprite rendering      | Billboard with Z-buffer per-column occlusion     |
| Ghost body            | Procedural trapezoid fill — no image files       |
| Pathfinding           | A* (Manhattan heuristic, 4-directional, 0.6s cache) |
| Line of sight         | Step-based ray trace (4 steps per unit)          |
| AI memory             | Tile visit frequency heat map (dict)             |
| AI prediction         | Velocity look-ahead 2.5 tiles                    |
| Collision detection   | AABB with 0.22 unit wall margin                  |
| Audio                 | `pygame.sndarray` procedural tone generation     |
| Resolution            | 960 x 640 pixels                                 |
| Target FPS            | 60 (capped at 0.05s max delta)                   |
| Mouse capture         | `pygame.event.set_grab(True)` during gameplay    |
| External assets       | None required                                    |

---

## FILE STRUCTURE

```
game3d.py       # Complete game — single file, self-contained
README.md       # This documentation file
```

---

## KNOWN ISSUES

- Frame rate may drop on older hardware due to per-pixel column rendering
- Audio requires `pygame.mixer` — silently disabled if not supported
- No save system — each run starts from the beginning
- Mouse must be recaptured if the window loses focus

---

## CREDITS

- Engine: Custom DDA raycasting in Python + Pygame
- Ghost design: Inspired by Slendrina (Clown Games)
- Raycasting technique: Based on the Wolfenstein 3D algorithm
- All code, graphics, and audio: Procedurally generated, no external files
