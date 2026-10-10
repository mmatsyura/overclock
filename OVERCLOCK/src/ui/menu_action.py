import math
import random

import pygame

from src.entities.enemies.chaser import ChaserEnemy
from src.entities.enemies.hex_splitter import HexSplitterEnemy
from src.entities.enemies.orb import OrbEnemy
from src.entities.enemies.pink_shooter import PinkShooterEnemy
from src.entities.enemies.radiant import RadiantEnemy
from src.entities.enemies.spawn_entry import begin_edge_spawn, update_edge_spawn
from src.entities.player import Player
from src.rendering.enemy_death_fx import EnemyDeathFX
from src.rendering.spawn_fx import draw_enemy_spawn_fx
from src.settings import *


class MenuWorldCamera:
    def __init__(self, world_size):
        self.world_size = pygame.Vector2(world_size)
        self.viewport_size = pygame.Vector2(world_size)

    def world_to_screen(self, pos, scale):
        return pygame.Vector2(pos)

    def world_to_screen_raw(self, pos, scale):
        return pygame.Vector2(pos)

    def world_to_screen_unwrapped(self, pos, scale):
        return pygame.Vector2(pos)

    def render_scale(self, scale):
        return scale


class MenuActionDirector:
    def __init__(self, screen_size, scale):
        self.world_size = pygame.Vector2(screen_size)
        self.scale = scale
        self.camera = MenuWorldCamera(screen_size)
        self.center = self.world_size * 0.5

        self.player = Player(self.center)
        self.player.angle = random.uniform(-math.pi, math.pi)
        self.player.vel = pygame.Vector2(random.uniform(-80.0, 80.0), random.uniform(-80.0, 80.0))

        self.enemies = []
        self.player_projectiles = []
        self.enemy_projectiles = []

        self.enemy_death_fx = EnemyDeathFX()

        self.pending_spawns = []
        self.spawn_timer = 0.65

        self.mode = "idle"
        self.mode_timer = random.uniform(1.6, 2.8)
        self.target_enemy = None

        self.orbit_angle = random.uniform(0.0, math.tau)
        self.orbit_sign = random.choice((-1.0, 1.0))
        self.orbit_radius_x = self.world_size.x * random.uniform(0.055, 0.085)
        self.orbit_radius_y = self.world_size.y * random.uniform(0.07, 0.11)
        self.orbit_speed = random.uniform(0.62, 0.88)

        self.aim_error = pygame.Vector2()
        self.aim_error_timer = 0.0

        self.fire_window = 0.0
        self.fire_pause = random.uniform(0.4, 1.0)

        self.thrust_timer = random.uniform(0.4, 1.0)
        self.thrusting = False

        self.evade_timer = 0.0
        self.evade_direction = pygame.Vector2()

        self.time = 0.0

    @staticmethod
    def angle_diff(target, current):
        return (target - current + math.pi) % math.tau - math.pi

    @staticmethod
    def clamp(value, low, high):
        return max(low, min(high, value))

    def alive_enemy_count(self):
        return sum(enemy.alive for enemy in self.enemies)

    def choose_mode(self):
        alive = [enemy for enemy in self.enemies if enemy.alive and not getattr(enemy, "spawn_intro_active", False)]

        if not alive:
            self.mode = "idle"
            self.mode_timer = random.uniform(1.8, 3.8)
            self.target_enemy = None
            return

        if random.random() < 0.36:
            self.mode = "idle"
            self.mode_timer = random.uniform(1.3, 3.2)
            self.target_enemy = None

            self.orbit_sign = random.choice((-1.0, 1.0))
            self.orbit_radius_x = self.world_size.x * random.uniform(0.045, 0.09)
            self.orbit_radius_y = self.world_size.y * random.uniform(0.06, 0.12)
            self.orbit_speed = random.uniform(0.58, 0.92)

        else:
            self.mode = "engage"
            self.mode_timer = random.uniform(2.0, 4.4)
            self.target_enemy = self.choose_target()

    def choose_target(self):
        candidates = [enemy for enemy in self.enemies if enemy.alive and not getattr(enemy, "spawn_intro_active", False)]

        if not candidates:
            return None

        scored = []

        for enemy in candidates:
            distance = self.player.pos.distance_to(enemy.pos)
            score = distance + random.uniform(-120.0, 150.0)

            if isinstance(enemy, PinkShooterEnemy):
                score -= 35.0

            if isinstance(enemy, RadiantEnemy):
                score -= 15.0

            if isinstance(enemy, HexSplitterEnemy):
                score -= 20.0

            scored.append((score, enemy))

        scored.sort(key=lambda item: item[0])

        pool = scored[:min(3, len(scored))]

        return random.choice(pool)[1]

    def update_aim_error(self, dt):
        self.aim_error_timer -= dt

        if self.aim_error_timer > 0.0:
            return

        self.aim_error_timer = random.uniform(0.28, 0.68)

        angle = random.uniform(0.0, math.tau)
        radius = random.uniform(42.0, 115.0)

        self.aim_error = pygame.Vector2(math.cos(angle), math.sin(angle)) * radius

    def get_projectile_evade(self):
        best_strength = 0.0
        best_direction = None

        for projectile in self.enemy_projectiles:
            if not projectile.alive or not projectile.active:
                continue

            if projectile.vel.length_squared() <= 0.001:
                continue

            relative = self.player.pos - projectile.pos

            if relative.length_squared() > 280.0 * 280.0:
                continue

            velocity = projectile.vel
            speed_sq = velocity.length_squared()

            t = self.clamp(relative.dot(velocity) / speed_sq, 0.0, 0.72)

            closest = projectile.pos + velocity * t
            miss = self.player.pos - closest
            miss_distance = miss.length()

            if miss_distance > 105.0:
                continue

            direction = velocity.normalize()
            side = pygame.Vector2(-direction.y, direction.x)

            sign = 1.0 if side.dot(self.player.pos - projectile.pos) >= 0.0 else -1.0
            strength = 1.0 - miss_distance / 105.0

            if strength > best_strength:
                best_strength = strength
                best_direction = side * sign

        return best_direction, best_strength

    def get_contact_evade(self):
        nearest = None
        nearest_distance = 999999.0

        for enemy in self.enemies:
            if not enemy.alive or getattr(enemy, "spawn_intro_active", False):
                continue

            delta = self.player.pos - enemy.pos
            distance = delta.length()
            danger = getattr(enemy, "hit_radius", 20.0) + 105.0

            if distance < danger and distance < nearest_distance and distance > 0.001:
                nearest = delta.normalize()
                nearest_distance = distance

        return nearest

    def center_pressure(self):
        dx = (self.player.pos.x - self.center.x) / max(1.0, self.world_size.x * 0.14)
        dy = (self.player.pos.y - self.center.y) / max(1.0, self.world_size.y * 0.18)

        return math.sqrt(dx * dx + dy * dy)

    def update_player(self, dt):
        self.mode_timer -= dt
        self.evade_timer = max(0.0, self.evade_timer - dt)

        self.update_aim_error(dt)

        if self.mode_timer <= 0.0:
            self.choose_mode()

        projectile_evade, projectile_strength = self.get_projectile_evade()
        contact_evade = self.get_contact_evade()

        pressure = self.center_pressure()

        if projectile_evade is not None and projectile_strength > 0.18:
            self.evade_direction = projectile_evade
            self.evade_timer = max(self.evade_timer, random.uniform(0.35, 0.62))

        elif contact_evade is not None:
            self.evade_direction = contact_evade
            self.evade_timer = max(self.evade_timer, random.uniform(0.28, 0.48))

        force_return = pressure > 1.0
        hard_return = pressure > 1.45

        shooting = False

        if self.evade_timer > 0.0 and not hard_return:
            desired_direction = self.evade_direction

            if self.player.pos.distance_squared_to(self.center) > 1.0:
                desired_direction += (self.center - self.player.pos).normalize() * 0.22

            thrusting = True

        elif force_return:
            desired_direction = self.center - self.player.pos

            if desired_direction.length_squared() <= 0.001:
                desired_direction = pygame.Vector2(1.0, 0.0)

            thrusting = True

        elif self.mode == "idle":
            self.orbit_angle += dt * self.orbit_sign * self.orbit_speed

            orbit_point = self.center + pygame.Vector2(math.cos(self.orbit_angle) * self.orbit_radius_x, math.sin(self.orbit_angle) * self.orbit_radius_y)

            desired_direction = orbit_point - self.player.pos

            self.thrust_timer -= dt

            if self.thrust_timer <= 0.0:
                self.thrusting = not self.thrusting

                if self.thrusting:
                    self.thrust_timer = random.uniform(0.38, 0.95)
                else:
                    self.thrust_timer = random.uniform(0.22, 0.72)

            thrusting = self.thrusting or self.player.vel.length() < 85.0

        else:
            if self.target_enemy is None or not self.target_enemy.alive or getattr(self.target_enemy, "spawn_intro_active", False):
                self.target_enemy = self.choose_target()

            if self.target_enemy is None:
                self.mode = "idle"
                self.mode_timer = random.uniform(1.4, 2.8)

                desired_direction = self.center - self.player.pos
                thrusting = self.player.vel.length() < 110.0

            else:
                distance = self.player.pos.distance_to(self.target_enemy.pos)
                lead = self.clamp(distance / 1900.0, 0.03, 0.13)

                aim_point = self.target_enemy.pos + getattr(self.target_enemy, "vel", pygame.Vector2()) * lead + self.aim_error

                desired_direction = aim_point - self.player.pos

                thrusting = self.player.vel.length() < 75.0 and random.random() < 0.42

                shooting = self.update_fire_logic(dt, self.target_enemy, desired_direction)

        if desired_direction.length_squared() <= 0.001:
            desired_direction = pygame.Vector2(math.cos(self.player.angle), math.sin(self.player.angle))
        else:
            desired_direction = desired_direction.normalize()

        aim_point = self.player.pos + desired_direction * 700.0

        self.player.update(dt, aim_point, thrusting, self.world_size)

        projectile = self.player.update_weapon(dt, shooting)

        if projectile is not None:
            self.player_projectiles.append(projectile)

    def update_fire_logic(self, dt, target, aim_delta):
        self.fire_window = max(0.0, self.fire_window - dt)
        self.fire_pause = max(0.0, self.fire_pause - dt)

        if target is None or aim_delta.length_squared() <= 0.001:
            return False

        target_angle = math.atan2(aim_delta.y, aim_delta.x)

        error = abs(self.angle_diff(target_angle, self.player.angle))
        distance = self.player.pos.distance_to(target.pos)

        aligned = error < 0.34 and distance < 720.0

        if aligned and self.fire_pause <= 0.0 and self.fire_window <= 0.0:
            self.fire_window = random.uniform(0.78, 1.65)
            self.fire_pause = self.fire_window + random.uniform(0.42, 1.25)

        if not aligned or self.fire_window <= 0.0:
            return False

        return random.random() > 0.10

    def update_spawning(self, dt):
        self.spawn_timer -= dt

        for item in self.pending_spawns:
            item["delay"] -= dt

        ready = [item for item in self.pending_spawns if item["delay"] <= 0.0]

        self.pending_spawns = [item for item in self.pending_spawns if item["delay"] > 0.0]

        for item in ready:
            self.spawn_enemy(item["kind"], item["side"], item["lane"])

        if self.spawn_timer > 0.0:
            return

        if self.alive_enemy_count() + len(self.pending_spawns) >= 7:
            self.spawn_timer = random.uniform(0.7, 1.2)
            return

        self.queue_spawn_pattern()

        self.spawn_timer = random.uniform(1.65, 3.0)

    def queue_spawn(self, kind, side, lane, delay):
        self.pending_spawns.append({"kind": kind, "side": side, "lane": self.clamp(lane, 0.12, 0.88), "delay": delay})

    def queue_spawn_pattern(self):
        pattern = random.choices(("chaser_pack", "orb_pressure", "pink_duel", "radiant_pair", "hex_entry", "mixed"), weights=(29, 17, 18, 12, 13, 11), k=1)[0]

        side = random.choice(("left", "right", "top", "bottom"))

        opposite = {
            "left": "right",
            "right": "left",
            "top": "bottom",
            "bottom": "top",
        }[side]

        lane = random.uniform(0.24, 0.76)

        if pattern == "chaser_pack":
            count = random.randint(2, 4)

            for i in range(count):
                offset = (i - (count - 1) * 0.5) * 0.085
                self.queue_spawn("chaser", side, lane + offset, i * random.uniform(0.28, 0.45))

        elif pattern == "orb_pressure":
            self.queue_spawn("orb", side, lane, 0.0)

            if random.random() < 0.72:
                self.queue_spawn("chaser", opposite, random.uniform(0.25, 0.75), random.uniform(0.75, 1.25))

        elif pattern == "pink_duel":
            self.queue_spawn("pink", side, lane, 0.0)

            if random.random() < 0.42:
                self.queue_spawn("pink", opposite, random.uniform(0.28, 0.72), random.uniform(0.9, 1.4))

        elif pattern == "radiant_pair":
            self.queue_spawn("radiant", side, lane - 0.07, 0.0)

            if random.random() < 0.60:
                self.queue_spawn("radiant", side, lane + 0.07, 0.55)

        elif pattern == "hex_entry":
            self.queue_spawn("hex", side, lane, 0.0)

            if random.random() < 0.48:
                self.queue_spawn("chaser", opposite, random.uniform(0.28, 0.72), random.uniform(0.9, 1.4))

        else:
            self.queue_spawn(random.choice(("orb", "pink", "radiant")), side, lane, 0.0)
            self.queue_spawn("chaser", opposite, random.uniform(0.22, 0.78), random.uniform(0.65, 1.15))

    def edge_target(self, side, lane):
        margin = 52.0

        if side == "left":
            return pygame.Vector2(margin, self.world_size.y * lane)

        if side == "right":
            return pygame.Vector2(self.world_size.x - margin, self.world_size.y * lane)

        if side == "top":
            return pygame.Vector2(self.world_size.x * lane, margin)

        return pygame.Vector2(self.world_size.x * lane, self.world_size.y - margin)

    def spawn_enemy(self, kind, side, lane):
        target = self.edge_target(side, lane)

        if kind == "chaser":
            enemy = ChaserEnemy(target, self.world_size)
            style = "chaser"
            color = CHASER_ACCENT
            duration = 0.64

        elif kind == "orb":
            enemy = OrbEnemy(target, self.player.pos, self.world_size)
            style = "orb"
            color = ORB_ACCENT
            duration = 0.82

        elif kind == "pink":
            enemy = PinkShooterEnemy(target, self.world_size)
            style = "pink"
            color = PINK_SHOOTER_ACCENT
            duration = 0.74

        elif kind == "radiant":
            enemy = RadiantEnemy(target, self.world_size)
            style = "radiant"
            color = RADIANT_ACCENT
            duration = 0.92

        else:
            enemy = HexSplitterEnemy(target, self.world_size)
            style = "hex"
            color = HEX_ACCENT
            duration = 1.0

        begin_edge_spawn(enemy, target, side, self.world_size, style, color, duration)

        self.enemies.append(enemy)

    def update_enemies(self, dt):
        for enemy in list(self.enemies):
            if not enemy.alive:
                continue

            if update_edge_spawn(enemy, dt):
                continue

            enemy.update(dt, self.player.pos, self.world_size, self.enemies, None, self.player_projectiles)

            consume_projectiles = getattr(enemy, "consume_projectiles", None)

            if consume_projectiles is not None:
                self.enemy_projectiles.extend(consume_projectiles())

    def update_player_projectiles(self, dt):
        spawned_children = []
        killed_something = False

        for projectile in self.player_projectiles:
            if not projectile.alive:
                continue

            projectile.update(dt, self.world_size, None)

            if not projectile.alive:
                continue

            for enemy in self.enemies:
                if not enemy.alive or getattr(enemy, "spawn_intro_active", False):
                    continue

                radius = BULLET_HIT_RADIUS + enemy.hit_radius

                if not projectile.collides_with(enemy.pos, radius):
                    continue

                projectile.alive = False

                register_hit = getattr(enemy, "register_hit", None)

                if register_hit is not None:
                    register_hit(projectile.vel)

                killed = enemy.take_damage(1)

                consume_children = getattr(enemy, "consume_children", None)

                if consume_children is not None:
                    children = consume_children()

                    if children:
                        spawned_children.extend(children)

                if killed:
                    killed_something = True

                    self.enemy_death_fx.spawn(enemy.pos, enemy.vel, getattr(enemy, "death_color", (255, 65, 65)), getattr(enemy, "death_core", (255, 175, 175)))

                break

        if spawned_children:
            self.enemies.extend(spawned_children)

        if killed_something and random.random() < 0.24:
            self.mode = "idle"
            self.mode_timer = random.uniform(0.9, 2.0)
            self.target_enemy = None

        self.player_projectiles = [projectile for projectile in self.player_projectiles if projectile.alive]
        self.enemies = [enemy for enemy in self.enemies if enemy.alive]

    def update_enemy_projectiles(self, dt):
        for projectile in self.enemy_projectiles:
            projectile.update(dt, self.world_size, None)

            if not projectile.alive or not projectile.active:
                continue

            delta = self.player.pos - projectile.pos
            radius = PLAYER_HIT_RADIUS + projectile.radius

            if delta.length_squared() > radius * radius:
                continue

            incoming = projectile.vel.copy()

            projectile.explode()

            self.player.register_damage_hit(incoming, projectile.color)

            if incoming.length_squared() > 0.001:
                direction = incoming.normalize()
                side = pygame.Vector2(-direction.y, direction.x)

                if random.random() < 0.5:
                    side *= -1.0

                self.evade_direction = side
                self.evade_timer = random.uniform(0.45, 0.72)

        self.enemy_projectiles = [projectile for projectile in self.enemy_projectiles if projectile.alive]

    def resolve_close_calls(self):
        for enemy in self.enemies:
            if not enemy.alive or getattr(enemy, "spawn_intro_active", False):
                continue

            delta = self.player.pos - enemy.pos
            radius = PLAYER_HIT_RADIUS + enemy.hit_radius

            if delta.length_squared() > radius * radius:
                continue

            if delta.length_squared() <= 0.001:
                delta = pygame.Vector2(random.uniform(-1.0, 1.0), random.uniform(-1.0, 1.0))

            direction = delta.normalize()

            self.player.vel += direction * 115.0

            self.evade_direction = direction
            self.evade_timer = max(self.evade_timer, 0.55)

    def update(self, dt):
        self.time += dt

        self.update_spawning(dt)
        self.update_player(dt)
        self.update_enemies(dt)
        self.update_player_projectiles(dt)
        self.update_enemy_projectiles(dt)
        self.resolve_close_calls()

        self.enemy_death_fx.update(dt, self.world_size, None)

    def draw(self, screen, fx):
        for projectile in self.player_projectiles:
            projectile.draw(screen, fx, self.camera, self.scale)

        for projectile in self.enemy_projectiles:
            projectile.draw(screen, fx, self.camera, self.scale)

        for enemy in self.enemies:
            draw_enemy_spawn_fx(fx, enemy, self.camera, self.scale)
            enemy.draw(screen, fx, self.camera, self.scale)

        self.enemy_death_fx.draw(screen, fx, self.camera, self.scale)

        self.player.draw(screen, fx, self.camera, self.scale)