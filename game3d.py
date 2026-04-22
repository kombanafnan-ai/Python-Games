"""
ADAPTIVE DARK 3D  -  First-Person Psychological Horror
=======================================================
Pure Python + Pygame raycasting engine (Wolfenstein-style).
* First-person human player view
* Human ghost entity (Slendrina-style tall pale woman)
* Adaptive AI (heat-map, prediction, 3 phases)
* Procedural audio heartbeat
* Sanity / stamina system
* Note pickups & lore
* No external assets required
"""

import pygame
import sys
import math
import random
import time
import heapq
from collections import deque

# ================================================================
# SCREEN & RENDER CONFIG
# ================================================================
SW, SH     = 960, 640
HALF_H     = SH // 2
FOV        = math.pi / 3          # 60 degrees
HALF_FOV   = FOV / 2
NUM_RAYS   = SW                   # one ray per pixel column
RAY_STEP   = FOV / NUM_RAYS
MAX_DEPTH  = 20.0
WALL_H_SCALE = 1.0
FPS        = 60

# Map tile size (world units)
CELL       = 1.0
MOVE_SPEED = 3.0
ROT_SPEED  = 2.2
MOUSE_SENS = 0.002

# ================================================================
# COLORS
# ================================================================
BLACK      = (0,   0,   0  )
WHITE      = (255, 255, 255)
DARK_GRAY  = (25,  22,  20 )
GRAY       = (70,  65,  60 )
LIGHT_GRAY = (140, 130, 120)
RED        = (180, 20,  20 )
DARK_RED   = (80,  5,   5  )
BLOOD_RED  = (130, 0,   0  )
YELLOW     = (220, 200, 40 )
ORANGE     = (200, 100, 15 )
GREEN      = (20,  160, 40 )
CYAN       = (20,  180, 180)
BONE       = (200, 180, 150)
RUST       = (90,  35,  8  )
SKIN       = (210, 180, 140)
PALE       = (220, 215, 210)
GHOST_BLUE = (140, 160, 210)
DARK_BLUE  = (20,  25,  60 )
DIM_WHITE  = (180, 175, 170)

# ================================================================
# LEVEL MAP  (0=floor/open, 1=wall)
# ================================================================
LEVEL_MAP = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,1],
    [1,0,1,1,0,0,1,0,1,1,1,0,1,1,1,1,0,0,1,0,1,1,0,1],
    [1,0,1,0,0,0,0,0,0,0,1,0,0,0,0,1,0,0,0,0,0,1,0,1],
    [1,0,1,0,1,1,1,1,1,0,1,1,1,0,0,1,1,1,1,1,0,1,0,1],
    [1,0,0,0,1,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,1,0,1],
    [1,0,1,0,1,0,1,1,0,1,1,0,1,1,1,1,0,1,1,0,0,0,0,1],
    [1,0,1,0,0,0,1,0,0,0,1,0,0,0,0,1,0,1,0,0,1,1,0,1],
    [1,0,1,1,1,0,1,0,1,0,0,0,1,0,0,1,0,1,0,1,1,0,0,1],
    [1,0,0,0,1,0,0,0,1,0,1,1,1,0,0,0,0,1,0,0,0,0,0,1],
    [1,1,1,0,1,1,1,0,1,1,1,0,0,0,1,1,0,1,1,1,0,1,0,1],
    [1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,1,0,0,0,1,0,1,0,1],
    [1,0,1,1,1,0,0,0,1,1,1,0,1,0,1,0,0,1,0,0,0,1,0,1],
    [1,0,0,0,0,0,1,0,0,0,1,0,0,0,1,0,1,1,0,1,1,1,0,1],
    [1,0,1,1,0,0,1,1,1,0,0,0,1,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
]
MAP_ROWS = len(LEVEL_MAP)
MAP_COLS = len(LEVEL_MAP[0])

KEY_POS        = (19.5, 2.5)
EXIT_POS       = (22.5, 14.5)
NOTE_POSITIONS = [(5.5,5.5),(11.5,3.5),(16.5,9.5),(3.5,13.5),(20.5,11.5)]
PLAYER_START   = (1.5, 1.5, math.pi / 4)   # x, y, angle
ENEMY_START    = (11.5, 8.5)

def is_wall(x, y):
    c, r = int(x), int(y)
    if 0 <= r < MAP_ROWS and 0 <= c < MAP_COLS:
        return LEVEL_MAP[r][c] == 1
    return True

def dist2(ax, ay, bx, by):
    return math.hypot(ax-bx, ay-by)

# ================================================================
# A* PATHFINDING  (tile-based)
# ================================================================
def astar(sx, sy, gx, gy):
    sc, sr = int(sx), int(sy)
    gc, gr = int(gx), int(gy)
    if LEVEL_MAP[gr][gc] == 1:
        return []
    open_set = []
    heapq.heappush(open_set, (0, (sc, sr)))
    came = {}
    g = {(sc,sr): 0}
    dirs = [(1,0),(-1,0),(0,1),(0,-1)]
    while open_set:
        _, cur = heapq.heappop(open_set)
        if cur == (gc, gr):
            path = []
            while cur in came:
                path.append(cur)
                cur = came[cur]
            path.reverse()
            return path
        for dc, dr in dirs:
            nb = (cur[0]+dc, cur[1]+dr)
            if LEVEL_MAP[nb[1]][nb[0]] == 1:
                continue
            ng = g[cur] + 1
            if ng < g.get(nb, 1e9):
                came[nb] = cur
                g[nb] = ng
                f = ng + abs(nb[0]-gc) + abs(nb[1]-gr)
                heapq.heappush(open_set, (f, nb))
    return []

# ================================================================
# RAYCASTER
# ================================================================
class Raycaster:
    def __init__(self):
        # Pre-compute ray angles
        self.angles = [i * RAY_STEP - HALF_FOV for i in range(NUM_RAYS)]
        # Z-buffer for sprite occlusion
        self.z_buffer = [MAX_DEPTH] * NUM_RAYS

    def cast(self, surface, px, py, pa, wall_shading):
        """Cast all rays and draw walls/floor/ceiling. Returns z_buffer."""
        sw, sh = surface.get_size()
        self.z_buffer = [MAX_DEPTH] * NUM_RAYS

        # Floor & ceiling gradient
        for y in range(HALF_H):
            # Ceiling
            shade = max(0, int(8 + y * 0.15))
            pygame.draw.line(surface, (shade, shade-2, shade-3), (0, y), (sw, y))
        for y in range(HALF_H, sh):
            # Floor
            shade = max(0, int(4 + (sh-y) * 0.2))
            shade2 = max(0, int(2 + (sh-y) * 0.12))
            pygame.draw.line(surface, (shade, shade2, shade2//2), (0, y), (sw, y))

        for col, ray_angle in enumerate(self.angles):
            angle = pa + ray_angle
            # DDA raycasting
            ray_cos = math.cos(angle)
            ray_sin = math.sin(angle)

            # Avoid division by zero
            if abs(ray_cos) < 1e-9: ray_cos = 1e-9
            if abs(ray_sin) < 1e-9: ray_sin = 1e-9

            # DDA setup
            map_x, map_y = int(px), int(py)
            delta_x = abs(1.0 / ray_cos)
            delta_y = abs(1.0 / ray_sin)

            step_x = 1 if ray_cos > 0 else -1
            step_y = 1 if ray_sin > 0 else -1

            side_x = (map_x + 1.0 - px) * delta_x if ray_cos > 0 else (px - map_x) * delta_x
            side_y = (map_y + 1.0 - py) * delta_y if ray_sin > 0 else (py - map_y) * delta_y

            hit = False
            side = 0
            depth = 0
            for _ in range(int(MAX_DEPTH * 2)):
                if side_x < side_y:
                    side_x += delta_x
                    map_x  += step_x
                    side    = 0
                else:
                    side_y += delta_y
                    map_y  += step_y
                    side    = 1
                if 0 <= map_y < MAP_ROWS and 0 <= map_x < MAP_COLS:
                    if LEVEL_MAP[map_y][map_x] == 1:
                        hit = True
                        break
                else:
                    break

            if hit:
                if side == 0:
                    depth = (map_x - px + (1 - step_x) / 2) / ray_cos
                else:
                    depth = (map_y - py + (1 - step_y) / 2) / ray_sin
                depth = max(0.01, depth)
                # Fix fisheye
                depth_corrected = depth * math.cos(ray_angle)
                self.z_buffer[col] = depth_corrected

                wall_h = int(sh / max(depth_corrected, 0.01) * WALL_H_SCALE)
                wall_top    = max(0,  HALF_H - wall_h // 2)
                wall_bottom = min(sh, HALF_H + wall_h // 2)

                # Brick-like color with distance shading
                brightness = max(0, min(255, int(255 / (1 + depth_corrected * depth_corrected * 0.15))))
                if side == 1:
                    brightness = int(brightness * 0.6)

                # Alternate brick rows for texture feel
                tx = (map_x + map_y) % 3
                base_r = 55 + tx * 8
                base_g = 48 + tx * 5
                base_b = 40 + tx * 3
                r = max(0, min(255, int(base_r * brightness / 160)))
                g = max(0, min(255, int(base_g * brightness / 160)))
                b = max(0, min(255, int(base_b * brightness / 160)))

                # Draw wall slice
                pygame.draw.line(surface, (r, g, b), (col, wall_top), (col, wall_bottom))

        return self.z_buffer

# ================================================================
# GHOST SPRITE RENDERER  (human ghost - tall pale woman)
# ================================================================
class GhostRenderer:
    """Renders the ghost as a billboard sprite with hand-drawn human silhouette."""

    def render(self, surface, px, py, pa, gx, gy, z_buffer, alpha_mult=1.0,
               phase=1, state="patrol"):
        dx = gx - px
        dy = gy - py
        dist = math.hypot(dx, dy)
        if dist < 0.1 or dist > 18:
            return

        # Angle to ghost relative to player view
        angle_to = math.atan2(dy, dx)
        delta = angle_to - pa
        # Normalize
        while delta > math.pi:  delta -= 2 * math.pi
        while delta < -math.pi: delta += 2 * math.pi

        if abs(delta) > HALF_FOV + 0.3:
            return

        # Screen X position
        screen_x = int((delta / FOV + 0.5) * SW)

        # Height on screen
        h = int(SH / max(dist, 0.1) * 0.92)
        w = int(h * 0.38)
        if h < 4 or w < 2:
            return

        top  = HALF_H - int(h * 0.62)
        left = screen_x - w // 2

        # Ghost flicker in phase 2+
        if phase >= 2:
            flicker = random.random()
            if flicker < 0.04:
                return
        if phase >= 3 and state == "ambush":
            if random.random() < 0.08:
                return

        # Brightness by distance
        brightness = max(20, min(255, int(200 / (dist * 0.5 + 0.8))))
        alpha = min(255, int(brightness * alpha_mult))

        ghost_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        self._draw_ghost_body(ghost_surf, w, h, alpha, phase, state, dist)

        # Occlusion: only draw columns not behind walls
        for col_off in range(w):
            col = left + col_off
            if 0 <= col < SW:
                if z_buffer[col] > dist:
                    # Blit single column slice
                    slice_surf = pygame.Surface((1, h), pygame.SRCALPHA)
                    ghost_surf.lock()
                    for row in range(h):
                        px2 = ghost_surf.get_at((col_off, row))
                        if px2[3] > 0:
                            slice_surf.set_at((0, row), px2)
                    ghost_surf.unlock()
                    surface.blit(slice_surf, (col, top))

    def _draw_ghost_body(self, surf, w, h, alpha, phase, state, dist):
        """Draw a human ghost silhouette: tall woman with flowing dress."""
        # Color: pale ghostly blue-white, redder when chasing
        if state in ("chase", "hunt"):
            r2 = min(255, 200 + int(dist * 2))
            base_color = (r2, 200, 210, alpha)
            glow_color = (255, 100, 100, alpha // 3)
        elif state == "ambush":
            base_color = (180, 160, 220, alpha)
            glow_color = (120, 80, 200, alpha // 3)
        else:
            base_color = (200, 210, 230, alpha)
            glow_color = (180, 200, 255, alpha // 4)

        # ------ BODY PROPORTIONS ------
        head_r  = max(2, w // 4)
        head_cx = w // 2
        head_cy = int(h * 0.10)

        neck_top    = head_cy + head_r
        neck_bot    = int(h * 0.22)
        shoulder_y  = int(h * 0.26)
        waist_y     = int(h * 0.50)
        hem_y       = int(h * 0.92)

        shoulder_w  = int(w * 0.85)
        neck_w      = max(2, w // 6)
        waist_w     = int(w * 0.52)
        hem_w       = int(w * 0.95)

        # ------ DRESS/BODY ------
        # Draw filled trapezoid shapes for torso and skirt
        # Torso (shoulders -> waist)
        self._fill_trapezoid(surf, head_cx, shoulder_y, shoulder_w,
                              waist_y, waist_w, base_color)
        # Skirt (waist -> hem)
        self._fill_trapezoid(surf, head_cx, waist_y, waist_w,
                              hem_y, hem_w, base_color)

        # Dress folds (vertical lines, ghostly)
        fold_color = (base_color[0]-30, base_color[1]-30, base_color[2]-20, alpha//2)
        num_folds = max(3, w // 5)
        for i in range(1, num_folds):
            fx = head_cx - hem_w//2 + i * hem_w // num_folds
            pygame.draw.line(surf, fold_color,
                             (fx, waist_y), (fx + random.randint(-2,2), hem_y), 1)

        # ------ ARMS (hanging, slightly raised) ------
        arm_top_l = (head_cx - shoulder_w//2, shoulder_y + 4)
        arm_top_r = (head_cx + shoulder_w//2, shoulder_y + 4)
        arm_bot_l = (head_cx - shoulder_w//2 - 4, int(h * 0.58))
        arm_bot_r = (head_cx + shoulder_w//2 + 4, int(h * 0.58))
        arm_color = (base_color[0]-10, base_color[1]-10, base_color[2], alpha)
        pygame.draw.line(surf, arm_color, arm_top_l, arm_bot_l, max(1, w//8))
        pygame.draw.line(surf, arm_color, arm_top_r, arm_bot_r, max(1, w//8))

        # ------ NECK ------
        neck_color = (base_color[0]-5, base_color[1]-5, base_color[2], alpha)
        neck_rect = pygame.Rect(head_cx - neck_w//2, neck_top, neck_w, neck_bot - neck_top)
        pygame.draw.rect(surf, neck_color, neck_rect)

        # ------ HAIR (long, flowing) ------
        hair_color = (20, 15, 25, alpha)
        hair_w = int(w * 0.82)
        # Top of hair
        pygame.draw.ellipse(surf, hair_color,
                            (head_cx - hair_w//2, head_cy - head_r,
                             hair_w, head_r + 4))
        # Flowing sides
        for strand in range(5):
            sx = head_cx - hair_w//2 + strand * hair_w // 4
            sy_top = head_cy - head_r + 2
            sy_bot = int(h * 0.55) + random.randint(-8, 8)
            pygame.draw.line(surf, hair_color, (sx, sy_top),
                             (sx + random.randint(-6,6), sy_bot), max(1, w//10))

        # ------ HEAD ------
        pygame.draw.ellipse(surf, base_color,
                            (head_cx - head_r, head_cy - head_r,
                             head_r*2, int(head_r*2.1)))

        # ------ FACE ------
        eye_y = head_cy + head_r // 4
        eye_off = max(1, head_r // 2)
        # Empty black eye sockets
        eye_sz = max(1, head_r // 3)
        pygame.draw.ellipse(surf, (0,0,0,alpha),
                            (head_cx - eye_off - eye_sz, eye_y - eye_sz,
                             eye_sz*2, eye_sz*2))
        pygame.draw.ellipse(surf, (0,0,0,alpha),
                            (head_cx + eye_off - eye_sz, eye_y - eye_sz,
                             eye_sz*2, eye_sz*2))
        # White glowing pupils when chasing
        if state in ("chase","hunt","ambush"):
            pupil_glow = (255, 60, 60, alpha)
            pygame.draw.circle(surf, pupil_glow,
                               (head_cx - eye_off, eye_y), max(1, eye_sz//2))
            pygame.draw.circle(surf, pupil_glow,
                               (head_cx + eye_off, eye_y), max(1, eye_sz//2))

        # Grim mouth
        mouth_y = head_cy + int(head_r * 0.75)
        mouth_w = max(2, head_r)
        pygame.draw.arc(surf, (0,0,0,alpha),
                        (head_cx - mouth_w//2, mouth_y - 2, mouth_w, 6),
                        math.pi, 2*math.pi, max(1, head_r//5))

        # ------ GLOW AURA ------
        glow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        glow_r = max(2, w // 2)
        pygame.draw.circle(glow_surf, glow_color, (head_cx, head_cy), glow_r)
        surf.blit(glow_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    def _fill_trapezoid(self, surf, cx, y1, w1, y2, w2, color):
        """Fill a vertical trapezoid."""
        for y in range(y1, min(surf.get_height(), y2 + 1)):
            if y2 == y1:
                t = 0
            else:
                t = (y - y1) / (y2 - y1)
            cur_w = int(w1 + (w2 - w1) * t)
            x = cx - cur_w // 2
            if 0 <= y < surf.get_height() and cur_w > 0:
                pygame.draw.line(surf, color, (max(0,x), y),
                                 (min(surf.get_width()-1, x+cur_w), y))


# ================================================================
# PLAYER  (first-person human)
# ================================================================
class Player:
    def __init__(self, x, y, angle):
        self.x     = x
        self.y     = y
        self.angle = angle
        self.speed = MOVE_SPEED
        self.rot_speed = ROT_SPEED
        self.has_key   = False
        self.sanity    = 100.0
        self.stamina   = 100.0
        self.is_running= False
        self.is_moving = False
        self.notes_read= []
        self.alive     = True
        self.vx        = 0.0
        self.vy        = 0.0
        self.bob       = 0.0
        self.bob_timer = 0.0
        self.footstep_timer = 0.0

    def update(self, dt, keys):
        run  = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        spd  = self.speed * (1.7 if run and self.stamina > 0 else 1.0)
        self.is_running = run and self.stamina > 0

        # Mouse look
        mx = pygame.mouse.get_rel()[0]
        self.angle += mx * MOUSE_SENS

        # Keyboard rotation fallback
        if keys[pygame.K_LEFT]:  self.angle -= self.rot_speed * dt
        if keys[pygame.K_RIGHT]: self.angle += self.rot_speed * dt

        # Movement
        fw = bk = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:    fw =  1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  fw = -1
        if keys[pygame.K_a]:                         bk = -1
        if keys[pygame.K_d]:                         bk =  1

        move_x = (math.cos(self.angle) * fw - math.sin(self.angle) * bk) * spd * dt
        move_y = (math.sin(self.angle) * fw + math.cos(self.angle) * bk) * spd * dt

        self.is_moving = fw != 0 or bk != 0

        # Collision
        margin = 0.22
        nx = self.x + move_x
        ny = self.y + move_y
        if not is_wall(nx + math.copysign(margin, move_x), self.y):
            self.x = nx
        if not is_wall(self.x, ny + math.copysign(margin, move_y)):
            self.y = ny

        # Stamina
        if self.is_running:
            self.stamina = max(0, self.stamina - dt * 18)
        else:
            self.stamina = min(100, self.stamina + dt * 7)

        # Camera bob
        if self.is_moving:
            self.bob_timer += dt * (8 if self.is_running else 5)
            self.bob = math.sin(self.bob_timer) * (3 if self.is_running else 1.5)
        else:
            self.bob *= 0.85

        # Footstep sound timer
        self.footstep_timer += dt if self.is_moving else 0
        self.vx = move_x / dt if dt > 0 else 0
        self.vy = move_y / dt if dt > 0 else 0


# ================================================================
# ADAPTIVE AI ENTITY
# ================================================================
class Entity:
    STATES = ["patrol","alert","chase","hunt","ambush","search"]

    def __init__(self, x, y):
        self.x, self.y   = x, y
        self.speed_base   = 1.6
        self.speed        = self.speed_base
        self.state        = "patrol"
        self.state_timer  = 0
        self.patrol_wps   = self._gen_patrol()
        self.patrol_idx   = 0
        self.sight_range  = 7.0
        self.hear_range   = 3.5
        self.last_known   = None
        self.lost_timer   = 0
        self.search_tiles = []
        self.search_idx   = 0
        self.blink_timer  = 0.0
        self.visible      = True
        self.heat_map     = {}
        self.ambush_tiles = []
        self.phase        = 1
        self._path_cache  = {}
        self._path_ts     = {}

    def _gen_patrol(self):
        pts = []
        for r in range(MAP_ROWS):
            for c in range(MAP_COLS):
                if LEVEL_MAP[r][c] == 0:
                    pts.append((c + 0.5, r + 0.5))
        random.shuffle(pts)
        return pts[:12]

    def observe(self, player):
        tc = (int(player.x), int(player.y))
        self.heat_map[tc] = self.heat_map.get(tc, 0) + 1
        total = sum(self.heat_map.values())
        if total > 250 and self.phase < 2:
            self.phase = 2
            self.speed_base = 1.9
        if total > 600 and self.phase < 3:
            self.phase = 3
            self.speed_base = 2.4
        if len(self.heat_map) > 15:
            hot = sorted(self.heat_map, key=lambda k: self.heat_map[k], reverse=True)[:4]
            self.ambush_tiles = hot

    def los(self, px, py):
        dx = px - self.x
        dy = py - self.y
        dist = math.hypot(dx, dy)
        if dist > self.sight_range:
            return False
        steps = int(dist * 4)
        if steps == 0:
            return True
        for i in range(1, steps):
            t = i / steps
            cx = self.x + dx * t
            cy = self.y + dy * t
            if is_wall(cx, cy):
                return False
        return True

    def path_to(self, gx, gy):
        key = (int(self.x), int(self.y), int(gx), int(gy))
        now = time.time()
        if key in self._path_cache and now - self._path_ts.get(key,0) < 0.6:
            return list(self._path_cache[key])
        p = astar(self.x, self.y, gx, gy)
        self._path_cache[key] = list(p)
        self._path_ts[key] = now
        return p

    def predict(self, player):
        spd = math.hypot(player.vx, player.vy)
        if spd < 0.1:
            return player.x, player.y
        ahead = 2.5
        px = player.x + (player.vx / spd) * ahead
        py = player.y + (player.vy / spd) * ahead
        if not is_wall(px, py):
            return px, py
        return player.x, player.y

    def update(self, dt, player, sound):
        self.state_timer += dt
        self.observe(player)

        dist = dist2(self.x, self.y, player.x, player.y)
        can_see  = self.los(player.x, player.y)
        can_hear = dist < self.hear_range and player.is_moving

        # Blink phase 2+
        if self.phase >= 2:
            self.blink_timer += dt
            self.visible = (self.blink_timer % 1.8) < 1.4
        else:
            self.visible = True

        if self.state == "patrol":
            self.speed = self.speed_base * 0.55
            if can_see or can_hear:
                self.state = "alert"
                self.state_timer = 0
                sound.trigger("alert")
            else:
                self._patrol(dt)

        elif self.state == "alert":
            self.speed = self.speed_base * 0.75
            if can_see:
                self.state = "chase"
                self.state_timer = 0
                sound.trigger("chase")
            elif self.state_timer > 3:
                self.state = "patrol"
            else:
                if can_hear:
                    self._move_to(player.x, player.y, dt)

        elif self.state == "chase":
            self.speed = self.speed_base
            if can_see:
                self.last_known = (player.x, player.y)
                self.lost_timer = 0
                target = self.predict(player) if self.phase >= 2 else (player.x, player.y)
                self._move_to(*target, dt)
            else:
                self.lost_timer += dt
                if self.lost_timer > 2.2:
                    self.state = "hunt" if self.phase >= 2 else "search"
                    self.state_timer = 0
                    self._setup_search(player)
                elif self.last_known:
                    self._move_to(*self.last_known, dt)

        elif self.state == "hunt":
            self.speed = self.speed_base * 1.05
            if can_see:
                self.state = "chase"
                return
            if self.search_tiles and self.search_idx < len(self.search_tiles):
                tc = self.search_tiles[self.search_idx]
                tx, ty = tc[0]+0.5, tc[1]+0.5
                if dist2(self.x,self.y,tx,ty) < 0.5:
                    self.search_idx += 1
                else:
                    self._move_to(tx, ty, dt)
            else:
                if self.heat_map:
                    hot = max(self.heat_map, key=lambda k: self.heat_map[k])
                    self._move_to(hot[0]+0.5, hot[1]+0.5, dt)
                else:
                    self.state = "patrol"

        elif self.state == "ambush":
            self.speed = self.speed_base * 1.15
            if can_see:
                self.state = "chase"
                return
            if self.ambush_tiles:
                t = self.ambush_tiles[0]
                tx, ty = t[0]+0.5, t[1]+0.5
                if dist2(self.x,self.y,tx,ty) < 0.6:
                    if self.state_timer > 5:
                        self.state = "patrol"
                else:
                    self._move_to(tx, ty, dt)
            else:
                self.state = "patrol"

        elif self.state == "search":
            self.speed = self.speed_base * 0.65
            if can_see or can_hear:
                self.state = "chase"
                return
            if self.search_tiles and self.search_idx < len(self.search_tiles):
                tc = self.search_tiles[self.search_idx]
                tx, ty = tc[0]+0.5, tc[1]+0.5
                if dist2(self.x,self.y,tx,ty) < 0.5:
                    self.search_idx += 1
                else:
                    self._move_to(tx, ty, dt)
            else:
                self.state = "patrol"

        if self.phase >= 3 and self.state == "patrol" and random.random() < 0.0008:
            self.state = "ambush"

    def _patrol(self, dt):
        if not self.patrol_wps:
            return
        wp = self.patrol_wps[self.patrol_idx % len(self.patrol_wps)]
        if dist2(self.x, self.y, *wp) < 0.4:
            self.patrol_idx = (self.patrol_idx + 1) % len(self.patrol_wps)
        else:
            self._move_to(*wp, dt)

    def _move_to(self, tx, ty, dt):
        d = dist2(self.x, self.y, tx, ty)
        if d < 0.05:
            return
        if d > 1.5:
            path = self.path_to(tx, ty)
            if path:
                nx, ny = path[0][0]+0.5, path[0][1]+0.5
                self._step(nx, ny, dt)
                return
        self._step(tx, ty, dt)

    def _step(self, tx, ty, dt):
        dx = tx - self.x
        dy = ty - self.y
        d = math.hypot(dx, dy)
        if d < 0.01:
            return
        nx = self.x + dx/d * self.speed * dt
        ny = self.y + dy/d * self.speed * dt
        margin = 0.2
        if not is_wall(nx + math.copysign(margin, dx/d), self.y):
            self.x = nx
        if not is_wall(self.x, ny + math.copysign(margin, dy/d)):
            self.y = ny

    def _setup_search(self, player):
        pc, pr = int(player.x), int(player.y)
        cands = []
        for dr in range(-5,6):
            for dc in range(-5,6):
                c, r = pc+dc, pr+dr
                if 0<=r<MAP_ROWS and 0<=c<MAP_COLS and LEVEL_MAP[r][c]==0:
                    cands.append((c,r))
        if self.phase >= 2:
            cands.sort(key=lambda t: -self.heat_map.get(t,0))
        else:
            random.shuffle(cands)
        self.search_tiles = cands[:8]
        self.search_idx = 0


# ================================================================
# SOUND MANAGER
# ================================================================
class SoundManager:
    def __init__(self):
        self.enabled = False
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self.enabled = True
        except:
            return
        self.sounds = {}
        self.cooldowns = {}
        self.hb_timer = 0.0
        self.hb_interval = 1.5
        self._make_sounds()

    def _make_sounds(self):
        import array
        rate = 22050
        def tone(freq, dur, wave="square", vol=6000):
            n = int(rate * dur)
            buf = array.array("h", [0]*n)
            for i in range(n):
                t = i/rate
                env = math.exp(-3*t/dur)
                if wave == "square":
                    v = vol if math.sin(2*math.pi*freq*t) > 0 else -vol
                elif wave == "sine":
                    v = int(vol * math.sin(2*math.pi*freq*t))
                else:
                    v = int(vol * (2*(freq*t%1)-1))
                buf[i] = max(-32767, min(32767, int(v*env)))
            return pygame.sndarray.make_sound(buf)
        try:
            self.sounds = {
                "heartbeat": tone(65, 0.18, "sine", 7000),
                "alert":     tone(520, 0.09, "square", 5000),
                "chase":     tone(320, 0.14, "square", 6000),
                "step_soft": tone(180, 0.05, "sine", 2000),
            }
        except:
            self.enabled = False

    def trigger(self, name, cd=0.8):
        if not self.enabled or name not in self.sounds:
            return
        now = time.time()
        if now - self.cooldowns.get(name,0) > cd:
            try: self.sounds[name].play()
            except: pass
            self.cooldowns[name] = now

    def update(self, dt, player, entity):
        if not self.enabled:
            return
        d = dist2(player.x, player.y, entity.x, entity.y)
        ratio = max(0, 1 - d / (entity.sight_range * 2))
        self.hb_interval = max(0.25, 1.6 - ratio * 1.35)
        self.hb_timer += dt
        if self.hb_timer >= self.hb_interval:
            self.hb_timer = 0
            self.trigger("heartbeat", cd=0.05)
        if player.is_moving:
            step_cd = 0.28 if player.is_running else 0.45
            self.trigger("step_soft", cd=step_cd)


# ================================================================
# PROP / OBJECT SPRITES  (key, exit door, notes)
# ================================================================
class Prop:
    def __init__(self, x, y, kind):
        self.x    = x
        self.y    = y
        self.kind = kind    # "key", "exit", "note"
        self.bob  = 0.0

    def render(self, surface, px, py, pa, z_buffer, has_key, notes_read, idx):
        if self.kind == "key" and has_key:
            return
        if self.kind == "note" and idx in notes_read:
            return

        dx = self.x - px
        dy = self.y - py
        dist = math.hypot(dx, dy)
        if dist < 0.2 or dist > 12:
            return

        angle_to = math.atan2(dy, dx)
        delta = angle_to - pa
        while delta >  math.pi: delta -= 2*math.pi
        while delta < -math.pi: delta += 2*math.pi
        if abs(delta) > HALF_FOV + 0.2:
            return

        screen_x = int((delta / FOV + 0.5) * SW)

        size = int(SH / max(dist, 0.1) * 0.18)
        if size < 4:
            return

        self.bob += 0.04
        bob_y = int(math.sin(self.bob) * 4)

        top  = HALF_H - size//2 + bob_y
        left = screen_x - size//2

        prop_surf = pygame.Surface((size, size), pygame.SRCALPHA)

        if self.kind == "key":
            c = YELLOW
            pygame.draw.circle(prop_surf, c, (size//2, size//4), max(2, size//4))
            pygame.draw.line(prop_surf, c, (size//2, size//2), (size//2, size-2), max(1, size//8))
            pygame.draw.line(prop_surf, c, (size//2, size*3//4), (size*3//4, size*3//4), max(1,size//8))
        elif self.kind == "exit":
            color = GREEN if has_key else RUST
            pygame.draw.rect(prop_surf, color, (2, 2, size-4, size-4), 3)
            font = pygame.font.SysFont("courier", max(8, size//3))
            lbl = font.render("EXIT", True, color)
            prop_surf.blit(lbl, (size//2 - lbl.get_width()//2, size//2 - lbl.get_height()//2))
        elif self.kind == "note":
            pygame.draw.rect(prop_surf, BONE, (1, 1, size-2, size-2))
            pygame.draw.rect(prop_surf, RUST, (1, 1, size-2, size-2), 2)
            font = pygame.font.SysFont("courier", max(6, size//4))
            lbl = font.render("!", True, DARK_RED)
            prop_surf.blit(lbl, (size//2-lbl.get_width()//2, size//2-lbl.get_height()//2))

        # Occlusion
        for col_off in range(size):
            col = left + col_off
            if 0 <= col < SW and z_buffer[col] > dist:
                pygame.draw.line(surface, (0,0,0,0), (col, top), (col, top+size))
                slice_surf = pygame.Surface((1, size), pygame.SRCALPHA)
                for row in range(size):
                    if 0 <= col_off < size and 0 <= row < size:
                        px2 = prop_surf.get_at((col_off, row))
                        if px2[3] > 0:
                            slice_surf.set_at((0, row), px2)
                surface.blit(slice_surf, (col, top))


# ================================================================
# HUD  (first-person elements)
# ================================================================
def draw_hud(surface, player, entity, elapsed):
    font  = pygame.font.SysFont("courier", 15)
    font2 = pygame.font.SysFont("courier", 12)
    sw, sh = surface.get_size()

    # -- SANITY BAR --
    sanity_color = GREEN if player.sanity > 60 else YELLOW if player.sanity > 30 else RED
    pygame.draw.rect(surface, (20,15,15), (12, 12, 106, 14))
    pygame.draw.rect(surface, sanity_color, (13, 13, int(player.sanity * 1.0), 12))
    surface.blit(font2.render("SANITY", True, DIM_WHITE), (12, 28))

    # -- STAMINA BAR --
    pygame.draw.rect(surface, (15,15,20), (12, 44, 106, 10))
    pygame.draw.rect(surface, CYAN, (13, 45, int(player.stamina * 1.0), 8))
    surface.blit(font2.render("STAMINA", True, DIM_WHITE), (12, 56))

    # -- KEY --
    if player.has_key:
        k = font.render("[KEY]", True, YELLOW)
        surface.blit(k, (12, 76))

    # -- THREAT PHASE --
    phases = ["", "I", "II", "III"]
    ph_color = GREEN if entity.phase==1 else ORANGE if entity.phase==2 else RED
    surface.blit(font.render(f"THREAT: {phases[entity.phase]}", True, ph_color), (sw-180, 12))
    surface.blit(font2.render(f"ENTITY: {entity.state.upper()}", True, LIGHT_GRAY), (sw-180, 30))

    mins = int(elapsed)//60
    secs = int(elapsed)%60
    surface.blit(font2.render(f"TIME: {mins:02d}:{secs:02d}", True, GRAY), (sw-180, 48))

    # -- CROSSHAIR --
    cx, cy = sw//2, sh//2
    cross_color = (180,160,160,160)
    for dx2, dy2, ex, ey in [(-8,0,-3,0),(3,0,8,0),(0,-8,0,-3),(0,3,0,8)]:
        pygame.draw.line(surface, cross_color, (cx+dx2, cy+dy2), (cx+ex, cy+ey), 1)

    # -- INTERACT HINT --
    d_key  = dist2(player.x, player.y, KEY_POS[0], KEY_POS[1])
    d_exit = dist2(player.x, player.y, EXIT_POS[0], EXIT_POS[1])
    for i, (nx, ny) in enumerate(NOTE_POSITIONS):
        if dist2(player.x, player.y, nx, ny) < 1.2 and i not in player.notes_read:
            lbl = font.render("[E] Read note", True, BONE)
            surface.blit(lbl, (sw//2 - lbl.get_width()//2, sh//2 + 40))
    if d_key < 1.2 and not player.has_key:
        lbl = font.render("[E] Pick up key", True, YELLOW)
        surface.blit(lbl, (sw//2 - lbl.get_width()//2, sh//2 + 40))
    if d_exit < 1.2:
        lbl = font.render("[E] Use exit door", True, GREEN if player.has_key else RUST)
        surface.blit(lbl, (sw//2 - lbl.get_width()//2, sh//2 + 40))

    # -- CONTROLS (fade out after 25s) --
    if elapsed < 25:
        a = max(0, int(255 * (1 - elapsed/25)))
        hints = ["WASD: Move", "Mouse/Arrows: Look", "Shift: Run", "E: Interact", "ESC: Quit"]
        for i, h in enumerate(hints):
            s = font2.render(h, True, GRAY)
            s.set_alpha(a)
            surface.blit(s, (sw//2 - 50, sh - 100 + i*14))


# ================================================================
# SCREEN EFFECTS
# ================================================================
def draw_sanity_effect(surface, sanity, elapsed):
    sw, sh = surface.get_size()
    if sanity < 50:
        intensity = int((50 - sanity) / 50 * 90)
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((70, 0, 0, intensity))
        surface.blit(overlay, (0, 0))
    if sanity < 25:
        for y in range(0, sh, 5):
            pygame.draw.line(surface, (0,0,0), (0,y), (sw,y))
        # Distortion
        if random.random() < 0.15:
            strip_y = random.randint(0, sh-20)
            strip_h = random.randint(2, 12)
            strip = surface.subsurface((0, strip_y, sw, strip_h)).copy()
            offset = random.randint(-15, 15)
            surface.blit(strip, (offset, strip_y))
    if sanity < 10:
        # Heavy vignette pulse
        t = time.time()
        v = int(abs(math.sin(t * 4)) * 100)
        vig = pygame.Surface((sw, sh), pygame.SRCALPHA)
        vig.fill((v, 0, 0, 80))
        surface.blit(vig, (0,0))

def draw_vignette(surface, strength=0.55):
    sw, sh = surface.get_size()
    vig = pygame.Surface((sw, sh), pygame.SRCALPHA)
    for r in range(max(sw,sh)//2, 0, -6):
        a = int(strength * 255 * (1 - r/(max(sw,sh)/2)))
        a = max(0, min(255, a))
        pygame.draw.circle(vig, (0,0,0,a), (sw//2, sh//2), r, 8)
    surface.blit(vig, (0,0))

def screen_shake(surface, amt):
    if amt < 1:
        return
    tmp = surface.copy()
    ox = random.randint(-amt, amt)
    oy = random.randint(-amt, amt)
    surface.fill(BLACK)
    surface.blit(tmp, (ox, oy))

def draw_breath_effect(surface, bob):
    """Subtle hand-held camera feel."""
    if abs(bob) < 0.5:
        return
    sw, sh = surface.get_size()
    shift = int(bob * 0.3)
    if shift == 0:
        return
    tmp = surface.copy()
    surface.blit(tmp, (0, shift))


# ================================================================
# NOTE POPUP
# ================================================================
NOTES_TEXT = [
    "Day 12. The generator failed again.\nSomething moved in the east corridor.\nI locked the door but I can hear it breathing.\nIt knows I am here.",
    "To whoever finds this:\nDo NOT go into the basement. We made a mistake.\nThe experiment was a failure. It should not exist.\nIt learns. God help you if it has seen you.",
    "I tried hiding in the same room twice.\nIt found me both times. Like it remembered.\nI have to keep moving. I have to be unpredictable.",
    "The key to the exit door is in the northeast room.\nBut IT patrols there now. It has adapted.\nWait for it to move away. Watch the patterns.\nThey change every time.",
    "My name was Dr. Elara Voss. I created her.\nI am so sorry. She was never meant to hunt.\nShe was meant to protect. Run.\nAnd never use the same path twice.",
]

class NoteUI:
    def __init__(self):
        self.active = False
        self.text   = ""
        self.timer  = 0.0
        self.duration = 7.0

    def show(self, text):
        self.active = True
        self.text   = text
        self.timer  = 0.0

    def update(self, dt):
        if self.active:
            self.timer += dt
            if self.timer > self.duration:
                self.active = False

    def draw(self, surface):
        if not self.active:
            return
        sw, sh = surface.get_size()
        fade = min(1.0, min(self.timer, self.duration - self.timer))
        alpha = int(255 * min(1.0, fade))
        pw, ph = 520, 190
        px2 = (sw - pw) // 2
        py2 = sh - ph - 28
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((8, 4, 4, 210))
        pygame.draw.rect(panel, BLOOD_RED, (0,0,pw,ph), 2)
        title_font = pygame.font.SysFont("courier", 13, bold=True)
        body_font  = pygame.font.SysFont("courier", 13)
        title = title_font.render("-- FOUND NOTE --", True, BLOOD_RED)
        panel.blit(title, (pw//2 - title.get_width()//2, 8))
        lines = self.text.split("\n")
        for i, line in enumerate(lines):
            s = body_font.render(line, True, BONE)
            s.set_alpha(alpha)
            panel.blit(s, (16, 30 + i * 18))
        panel.set_alpha(alpha)
        surface.blit(panel, (px2, py2))


# ================================================================
# TITLE / GAME OVER / WIN SCREENS
# ================================================================
def title_screen(surface, clock):
    font_big  = pygame.font.SysFont("courier", 56, bold=True)
    font_med  = pygame.font.SysFont("courier", 20)
    font_sm   = pygame.font.SysFont("courier", 13)
    t = 0.0
    pygame.mouse.set_visible(True)
    while True:
        dt = clock.tick(FPS) / 1000
        t += dt
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_RETURN: return
                if ev.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
        surface.fill((3, 1, 1))
        for _ in range(25):
            pygame.draw.line(surface,(15,5,5),
                             (random.randint(0,SW),random.randint(0,SH)),
                             (random.randint(0,SW),random.randint(0,SH)),1)
        pulse = 0.5 + 0.5*math.sin(t*2.0)
        rv = int(160 + 80*pulse)
        t1 = font_big.render("ADAPTIVE DARK", True, (rv, 8, 8))
        surface.blit(t1, (SW//2-t1.get_width()//2, 110))
        t2 = font_med.render("3D First-Person Psychological Horror", True, (90,65,65))
        surface.blit(t2, (SW//2-t2.get_width()//2, 200))
        if int(t*2)%2==0:
            p = font_med.render("PRESS ENTER TO BEGIN", True, (130,25,25))
            surface.blit(p, (SW//2-p.get_width()//2, 310))
        l1 = font_sm.render("She is watching. She remembers. She adapts.", True, (55,35,35))
        surface.blit(l1, (SW//2-l1.get_width()//2, 380))
        l2 = font_sm.render("WASD + Mouse to move  |  E to interact  |  Shift to run", True, (45,30,30))
        surface.blit(l2, (SW//2-l2.get_width()//2, 415))
        esc = font_sm.render("ESC to quit", True, (35,25,25))
        surface.blit(esc, (SW//2-esc.get_width()//2, 450))
        draw_vignette(surface, 0.75)
        pygame.display.flip()

def game_over_screen(surface, clock, reason, elapsed):
    font_big = pygame.font.SysFont("courier", 50, bold=True)
    font_med = pygame.font.SysFont("courier", 20)
    font_sm  = pygame.font.SysFont("courier", 13)
    t = 0.0
    pygame.mouse.set_visible(True)
    while True:
        dt = clock.tick(FPS)/1000; t += dt
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_RETURN, pygame.K_r): return "restart"
                if ev.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
        surface.fill((2,0,0))
        for _ in range(18):
            pygame.draw.line(surface,(12,0,0),
                             (random.randint(0,SW),random.randint(0,SH)),
                             (random.randint(0,SW)+random.randint(1,5),random.randint(0,SH)),1)
        pulse = 0.5+0.5*math.sin(t*3)
        rv = int(170+70*pulse)
        o = font_big.render("YOU DIED", True, (rv,0,0))
        surface.blit(o,(SW//2-o.get_width()//2, 140))
        r2 = font_med.render(reason, True, (130,70,70))
        surface.blit(r2,(SW//2-r2.get_width()//2, 220))
        mins=int(elapsed)//60; secs=int(elapsed)%60
        ts = font_med.render(f"Survived: {mins:02d}:{secs:02d}", True,(70,50,50))
        surface.blit(ts,(SW//2-ts.get_width()//2,260))
        if int(t*2)%2==0:
            rr=font_med.render("R or ENTER to try again", True,(110,25,25))
            surface.blit(rr,(SW//2-rr.get_width()//2,330))
        e2=font_sm.render("ESC to quit", True,(45,25,25))
        surface.blit(e2,(SW//2-e2.get_width()//2,375))
        draw_vignette(surface,0.85)
        pygame.display.flip()

def win_screen(surface, clock, elapsed, notes_read):
    font_big = pygame.font.SysFont("courier", 46, bold=True)
    font_med = pygame.font.SysFont("courier", 19)
    font_sm  = pygame.font.SysFont("courier", 13)
    t = 0.0
    pygame.mouse.set_visible(True)
    while True:
        dt = clock.tick(FPS)/1000; t += dt
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_RETURN, pygame.K_r): return "restart"
                if ev.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
        surface.fill((0,5,2))
        pulse=0.5+0.5*math.sin(t*1.5)
        gv=int(70+70*pulse)
        o=font_big.render("YOU ESCAPED", True,(10,gv+80,10))
        surface.blit(o,(SW//2-o.get_width()//2,130))
        mins=int(elapsed)//60; secs=int(elapsed)%60
        ts=font_med.render(f"Time: {mins:02d}:{secs:02d}", True,(60,150,60))
        surface.blit(ts,(SW//2-ts.get_width()//2,210))
        ns=font_med.render(f"Notes found: {len(notes_read)} / {len(NOTE_POSITIONS)}", True,(60,130,60))
        surface.blit(ns,(SW//2-ns.get_width()//2,245))
        lore=font_sm.render("She still wanders the halls, waiting for the next visitor.", True,(30,70,30))
        surface.blit(lore,(SW//2-lore.get_width()//2,300))
        if int(t*2)%2==0:
            rr=font_med.render("R to play again  |  ESC to quit", True,(30,90,30))
            surface.blit(rr,(SW//2-rr.get_width()//2,360))
        draw_vignette(surface,0.5)
        pygame.display.flip()


# ================================================================
# MINIMAP  (small corner overlay)
# ================================================================
def draw_minimap(surface, player, entity):
    scale = 7
    mw = MAP_COLS * scale
    mh = MAP_ROWS * scale
    ox = SW - mw - 8
    oy = 8
    # Background
    mm = pygame.Surface((mw, mh), pygame.SRCALPHA)
    mm.fill((0,0,0,140))
    for r in range(MAP_ROWS):
        for c in range(MAP_COLS):
            if LEVEL_MAP[r][c] == 1:
                pygame.draw.rect(mm, (55,50,45,200), (c*scale, r*scale, scale-1, scale-1))
    # Player dot
    px2 = int(player.x * scale)
    py2 = int(player.y * scale)
    pygame.draw.circle(mm, (80,200,80), (px2, py2), 3)
    # Direction line
    ex2 = int((player.x + math.cos(player.angle)*1.5) * scale)
    ey2 = int((player.y + math.sin(player.angle)*1.5) * scale)
    pygame.draw.line(mm, GREEN, (px2,py2), (ex2,ey2), 1)
    # Entity
    if entity.visible:
        ex3 = int(entity.x * scale)
        ey3 = int(entity.y * scale)
        c3 = RED if entity.state in ("chase","hunt") else ORANGE if entity.state=="alert" else (80,40,80)
        pygame.draw.circle(mm, c3, (ex3, ey3), 3)
    pygame.draw.rect(mm, (80,60,40,180), (0,0,mw,mh), 1)
    surface.blit(mm, (ox, oy))


# ================================================================
# MAIN GAME SESSION
# ================================================================
def game_session(screen, clock):
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)

    player   = Player(*PLAYER_START)
    entity   = Entity(*ENEMY_START)
    sound    = SoundManager()
    note_ui  = NoteUI()
    raycaster= Raycaster()
    ghost_r  = GhostRenderer()

    # Props
    props = [Prop(*KEY_POS, "key"), Prop(*EXIT_POS, "exit")]
    for i, (nx, ny) in enumerate(NOTE_POSITIONS):
        props.append(Prop(nx, ny, "note"))

    elapsed       = 0.0
    shake_amt     = 0
    game_over     = False
    won           = False
    death_reason  = ""
    interact_cool = 0.0

    # Flush mouse
    pygame.mouse.get_rel()

    while True:
        dt = min(clock.tick(FPS)/1000, 0.05)
        elapsed += dt
        interact_cool = max(0, interact_cool - dt)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.event.set_grab(False)
                return "quit"
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    pygame.event.set_grab(False)
                    return "quit"
                if ev.key == pygame.K_e and interact_cool <= 0:
                    interact_cool = 0.5
                    # Key pickup
                    if not player.has_key and dist2(player.x,player.y,*KEY_POS) < 1.2:
                        player.has_key = True
                        note_ui.show("You found the key.\nThe exit door is to the southeast.")
                    # Exit
                    if dist2(player.x,player.y,*EXIT_POS) < 1.2:
                        if player.has_key:
                            won = True
                        else:
                            note_ui.show("The door is locked.\nFind the key first.")
                    # Notes
                    for i,(nx,ny) in enumerate(NOTE_POSITIONS):
                        if i not in player.notes_read and dist2(player.x,player.y,nx,ny) < 1.2:
                            player.notes_read.append(i)
                            note_ui.show(NOTES_TEXT[i])
                            interact_cool = 1.2

        keys = pygame.key.get_pressed()

        if not game_over and not won:
            player.update(dt, keys)
            entity.update(dt, player, sound)
            sound.update(dt, player, entity)
            note_ui.update(dt)

            d = dist2(player.x,player.y,entity.x,entity.y)

            # Sanity
            if d < entity.sight_range * 0.65:
                player.sanity = max(0, player.sanity - dt * 9)
                shake_amt = max(shake_amt, int((1-d/(entity.sight_range*0.65))*6))
            else:
                player.sanity = min(100, player.sanity + dt * 1.4)
                shake_amt = max(0, shake_amt - 1)

            # Caught
            if d < 0.65:
                game_over = True
                death_reason = "She found you."
            if player.sanity <= 0:
                game_over = True
                death_reason = "Your mind shattered in the darkness."

        # ---- RENDER ----
        # 1. Raycasting (walls, floor, ceiling)
        z_buf = raycaster.cast(screen, player.x, player.y, player.angle, True)

        # 2. Props
        for i, prop in enumerate(props):
            note_idx = i - 2  # first 2 are key and exit
            prop.render(screen, player.x, player.y, player.angle, z_buf,
                        player.has_key, player.notes_read, note_idx)

        # 3. Ghost
        if entity.visible or entity.phase < 2:
            ghost_r.render(screen, player.x, player.y, player.angle,
                           entity.x, entity.y, z_buf, 1.0,
                           entity.phase, entity.state)

        # 4. Post-processing
        draw_breath_effect(screen, player.bob)
        draw_sanity_effect(screen, player.sanity, elapsed)
        draw_vignette(screen, 0.42)

        # 5. HUD
        draw_hud(screen, player, entity, elapsed)
        draw_minimap(screen, player, entity)
        note_ui.draw(screen)

        if shake_amt > 0:
            screen_shake(screen, shake_amt)

        pygame.display.flip()

        if game_over:
            pygame.event.set_grab(False)
            pygame.mouse.set_visible(True)
            return game_over_screen(screen, clock, death_reason, elapsed)
        if won:
            pygame.event.set_grab(False)
            pygame.mouse.set_visible(True)
            return win_screen(screen, clock, elapsed, player.notes_read)

    pygame.event.set_grab(False)
    return "quit"


# ================================================================
# ENTRY POINT
# ================================================================
def main():
    pygame.init()
    screen = pygame.display.set_mode((SW, SH))
    pygame.display.set_caption("ADAPTIVE DARK 3D")
    clock = pygame.time.Clock()

    title_screen(screen, clock)

    while True:
        result = game_session(screen, clock)
        if result == "quit":
            break

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()