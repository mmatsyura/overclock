import math
import random

import pygame
import pygame.gfxdraw

from src.settings import CHASER_MAX_SPEED, CHASER_ACCEL, CHASER_TURN_SPEED
from src.settings import CHASER_BODY, CHASER_ACCENT, CHASER_CORE, CHASER_SCALE, CHASER_HP
from src.settings import CHASER_SEPARATION_RADIUS, CHASER_SEPARATION_FORCE, CHASER_HIT_RADIUS
from src.entities.enemies.dodge import get_dodge_vector, init_dodge_state


class ChaserEnemy:
    def __init__(self, pos, world_size=None):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2()
        self.angle = random.uniform(0.0, math.tau)
        self.world_size = pygame.Vector2(world_size) if world_size is not None else None

        self.health = CHASER_HP
        self.alive = True

        self.hit_radius = CHASER_HIT_RADIUS
        self.score_value = 2
        self.death_color = CHASER_ACCENT
        self.death_core = CHASER_CORE

        self.behavior_time = random.uniform(0.0, 20.0)
        self.behavior_timer = random.uniform(3.5, 7.5)

        self.flank_sign = random.choice((-1.0, 1.0))
        self.flank_distance = random.uniform(45.0, 115.0)

        self.weave_phase = random.uniform(0.0, math.tau)
        self.weave_speed = random.uniform(0.65, 1.35)
        self.weave_distance = random.uniform(14.0, 42.0)

        self.speed_factor = random.uniform(0.90, 1.06)
        self.accel_factor = random.uniform(0.88, 1.12)
        self.turn_factor = random.uniform(0.86, 1.14)
        self.close_pull_factor = random.uniform(0.42, 0.68)
        init_dodge_state(self)

    @staticmethod
    def angle_diff(target, current):
        return (target - current + math.pi) % math.tau - math.pi

    @staticmethod
    def rotated(points, angle, center, scale):
        c, s = math.cos(angle), math.sin(angle)

        return [
            (
                int(center.x + x * scale * c - y * scale * s),
                int(center.y + x * scale * s + y * scale * c),
            )
            for x, y in points
        ]

    @staticmethod
    def wrapped_delta(source, target, world_size):
        delta = pygame.Vector2(target) - pygame.Vector2(source)

        if delta.x > world_size.x * 0.5:
            delta.x -= world_size.x
        elif delta.x < -world_size.x * 0.5:
            delta.x += world_size.x

        if delta.y > world_size.y * 0.5:
            delta.y -= world_size.y
        elif delta.y < -world_size.y * 0.5:
            delta.y += world_size.y

        return delta

    def get_separation(self, enemies, world_size):
        force = pygame.Vector2()

        for other in enemies:
            if other is self:
                continue

            away = self.wrapped_delta(other.pos, self.pos, world_size)
            distance_sq = away.length_squared()

            if distance_sq <= 0.001:
                continue

            distance = math.sqrt(distance_sq)

            if distance >= CHASER_SEPARATION_RADIUS:
                continue

            strength = 1.0 - distance / CHASER_SEPARATION_RADIUS
            force += away.normalize() * strength * strength

        if force.length_squared() > 1:
            force = force.normalize()

        return force

    def update(self, dt, target, world_size, enemies, walls=None, player_projectiles=None):
        self.world_size = pygame.Vector2(world_size)

        self.behavior_time += dt
        self.behavior_timer -= dt

        if self.behavior_timer <= 0.0:
            self.behavior_timer = random.uniform(3.5, 7.5)
            self.flank_distance = random.uniform(45.0, 115.0)
            self.weave_distance = random.uniform(14.0, 42.0)

            if random.random() < 0.42:
                self.flank_sign *= -1.0

        to_player = self.wrapped_delta(self.pos, target, world_size)
        distance_to_player = to_player.length()

        if distance_to_player > 0.001:
            chase_dir = to_player / distance_to_player
        else:
            chase_dir = pygame.Vector2(math.cos(self.angle), math.sin(self.angle))

        perpendicular = pygame.Vector2(-chase_dir.y, chase_dir.x)

        flank_fade = max(0.0, min(1.0, (distance_to_player - 65.0) / 210.0))
        flank_offset = self.flank_sign * self.flank_distance * flank_fade
        weave_offset = math.sin(self.behavior_time * self.weave_speed + self.weave_phase) * self.weave_distance * flank_fade

        approach_vector = to_player + perpendicular * (flank_offset + weave_offset)

        if approach_vector.length_squared() > 0.001:
            approach_dir = approach_vector.normalize()
        else:
            approach_dir = chase_dir

        separation = self.get_separation(enemies, world_size)
        separation_strength = min(1.0, max(0.10, (distance_to_player - 30.0) / 155.0))

        desired_dir = approach_dir + separation * CHASER_SEPARATION_FORCE * separation_strength
        dodge = get_dodge_vector(self, dt, player_projectiles, 215.0, 0.46)
        if dodge.length_squared() > 0.001:
            desired_dir += dodge * 1.45

        if desired_dir.length_squared() > 0.001:
            desired_dir = desired_dir.normalize()
        else:
            desired_dir = chase_dir

        if walls is not None:
            desired_dir = walls.avoidance_direction(self.pos, desired_dir, self.vel, self.hit_radius)

        desired_angle = math.atan2(desired_dir.y, desired_dir.x)
        diff = self.angle_diff(desired_angle, self.angle)

        close_turn_bonus = max(0.0, 1.0 - distance_to_player / 150.0)
        turn_speed = (CHASER_TURN_SPEED + close_turn_bonus * 0.75) * self.turn_factor
        max_turn = turn_speed * dt

        self.angle += max(-max_turn, min(diff, max_turn))

        forward = pygame.Vector2(math.cos(self.angle), math.sin(self.angle))

        personal_max_speed = CHASER_MAX_SPEED * self.speed_factor
        desired_velocity = forward * personal_max_speed

        steering = desired_velocity - self.vel
        max_change = CHASER_ACCEL * self.accel_factor * dt

        if steering.length() > max_change:
            steering.scale_to_length(max_change)

        self.vel += steering

        if distance_to_player < 90.0:
            direct_pull = chase_dir * CHASER_ACCEL * self.close_pull_factor * dt
            self.vel += direct_pull

        if self.vel.length() > personal_max_speed:
            self.vel.scale_to_length(personal_max_speed)

        self.pos += self.vel * dt

        wrap_event = None

        if self.pos.x >= world_size.x:
            wrap_event = ("right", max(0.0, min(1.0, self.pos.y / world_size.y)))
            self.pos.x -= world_size.x
        elif self.pos.x < 0.0:
            wrap_event = ("left", max(0.0, min(1.0, self.pos.y / world_size.y)))
            self.pos.x += world_size.x

        if self.pos.y >= world_size.y:
            wrap_event = ("bottom", max(0.0, min(1.0, self.pos.x / world_size.x)))
            self.pos.y -= world_size.y
        elif self.pos.y < 0.0:
            wrap_event = ("top", max(0.0, min(1.0, self.pos.x / world_size.x)))
            self.pos.y += world_size.y

        return wrap_event

    def draw(self, screen, fx, camera, scale):
        if getattr(self, "spawn_intro_active", False):
            self.draw_at(screen, fx, camera, scale, self.pos, True)
            return

        if self.world_size is None or not hasattr(camera, "world_to_screen_raw"):
            self.draw_at(screen, fx, camera, scale, self.pos, False)
            return

        margin = 42.0

        x_offsets = [0.0]
        y_offsets = [0.0]

        if self.pos.x < margin:
            x_offsets.append(self.world_size.x)
        elif self.pos.x > self.world_size.x - margin:
            x_offsets.append(-self.world_size.x)

        if self.pos.y < margin:
            y_offsets.append(self.world_size.y)
        elif self.pos.y > self.world_size.y - margin:
            y_offsets.append(-self.world_size.y)

        for x_offset in x_offsets:
            for y_offset in y_offsets:
                draw_pos = self.pos + pygame.Vector2(x_offset, y_offset)
                self.draw_at(screen, fx, camera, scale, draw_pos, True)

    def draw_at(self, screen, fx, camera, scale, world_pos, raw):
        center = camera.world_to_screen_raw(world_pos, scale) if raw else camera.world_to_screen(world_pos, scale)
        enemy_scale = camera.render_scale(scale) * CHASER_SCALE

        body = [(27, 0), (-15, -17), (-8, 0), (-15, 17)]
        body_points = self.rotated(body, self.angle, center, enemy_scale)

        pygame.gfxdraw.filled_polygon(screen, body_points, CHASER_BODY)
        pygame.draw.lines(screen, (105, 20, 20), True, body_points, max(2, int(3 * enemy_scale)))
        pygame.draw.lines(screen, CHASER_ACCENT, True, body_points, max(1, int(1.5 * enemy_scale)))
        pygame.gfxdraw.aapolygon(screen, body_points, CHASER_CORE)

    def take_damage(self, damage):
        self.health -= damage

        if self.health <= 0:
            self.alive = False
            return True

        return False