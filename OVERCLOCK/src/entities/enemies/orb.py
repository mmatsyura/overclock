import math
import random

import pygame

from src.settings import ORB_MAX_SPEED, ORB_ACCEL, ORB_TURN_SPEED
from src.settings import ORB_RADIUS, ORB_HIT_RADIUS
from src.settings import ORB_BODY, ORB_DARK, ORB_ACCENT, ORB_CORE
from src.entities.enemies.dodge import get_dodge_vector, init_dodge_state


class OrbEnemy:
    def __init__(self, pos, target, world_size):
        self.pos = pygame.Vector2(pos)
        self.world_size = pygame.Vector2(world_size)
        self.vel = pygame.Vector2()
        self.alive = True
        self.health = 1
        self.hit_radius = ORB_HIT_RADIUS
        self.score_value = 4
        self.death_color = (255, 105, 35)
        self.death_core = (255, 205, 120)

        delta = self.wrapped_delta(self.pos, target, world_size)

        if delta.length_squared() > 0:
            target_angle = math.atan2(delta.y, delta.x)
        else:
            target_angle = random.uniform(0.0, math.tau)

        self.angle = target_angle + random.uniform(-0.55, 0.55)
        self.speed = ORB_MAX_SPEED * random.uniform(0.65, 0.85)

        self.anim_time = random.uniform(0.0, 100.0)
        self.outer_rotation = random.uniform(0.0, math.tau)
        self.inner_rotation = random.uniform(0.0, math.tau)
        self.spin_dir = random.choice((-1.0, 1.0))
        init_dodge_state(self)

    @staticmethod
    def angle_diff(target, current):
        return (target - current + math.pi) % math.tau - math.pi

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

    def take_damage(self, damage):
        self.health -= damage

        if self.health <= 0:
            self.alive = False
            return True

        return False

    def update(self, dt, target, world_size, enemies=None, walls=None, player_projectiles=None):
        delta = self.wrapped_delta(self.pos, target, world_size)

        if delta.length_squared() > 1:
            desired_dir = delta.normalize()
            dodge = get_dodge_vector(self, dt, player_projectiles, 205.0, 0.50)
            if dodge.length_squared() > 0.001:
                desired_dir = (desired_dir + dodge * 1.30).normalize()

            if walls is not None:
                desired_dir = walls.avoidance_direction(self.pos, desired_dir, self.vel, self.hit_radius)

            target_angle = math.atan2(desired_dir.y, desired_dir.x)
            diff = self.angle_diff(target_angle, self.angle)
            max_turn = ORB_TURN_SPEED * dt
            self.angle += max(-max_turn, min(diff, max_turn))

        self.speed = min(ORB_MAX_SPEED, self.speed + ORB_ACCEL * dt)

        forward = pygame.Vector2(math.cos(self.angle), math.sin(self.angle))
        self.vel = forward * self.speed
        self.pos += self.vel * dt

        self.anim_time += dt
        self.outer_rotation += dt * 1.25 * self.spin_dir
        self.inner_rotation -= dt * 1.9 * self.spin_dir

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
            positions = [self.pos]
        else:
            margin = ORB_RADIUS * 1.8
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

            positions = [self.pos + pygame.Vector2(x, y) for x in x_offsets for y in y_offsets]

        draw_scale = camera.render_scale(scale)
        radius = max(7, int(ORB_RADIUS * draw_scale))
        pulse = 0.5 + 0.5 * math.sin(self.anim_time * 5.5)
        pulse2 = 0.5 + 0.5 * math.sin(self.anim_time * 3.4 + 1.7)

        for draw_pos in positions:
            center = camera.world_to_screen_raw(draw_pos, scale)
            center_i = int(center.x), int(center.y)

            self.draw_outer_shell(screen, fx, center, radius, pulse)
            self.draw_body(screen, center_i, radius)
            self.draw_inner_shell(screen, center_i, radius, pulse2)
            self.draw_rotating_cracks(screen, center_i, radius, draw_scale)
            self.draw_core(screen, fx, center_i, radius, pulse)

        pulse = 0.5 + 0.5 * math.sin(self.anim_time * 5.5)
        pulse2 = 0.5 + 0.5 * math.sin(self.anim_time * 3.4 + 1.7)

        self.draw_outer_shell(screen, fx, center, radius, pulse)
        self.draw_body(screen, center_i, radius)
        self.draw_inner_shell(screen, center_i, radius, pulse2)
        self.draw_rotating_cracks(screen, center_i, radius, draw_scale)
        self.draw_core(screen, fx, center_i, radius, pulse)

    def draw_outer_shell(self, screen, fx, center, radius, pulse):
        back_points = []
        front_points = []

        spike_count = 18

        for i in range(spike_count):
            angle = self.outer_rotation + math.tau * i / spike_count

            if i % 2 == 0:
                dist = radius * 1.58
            else:
                dist = radius * 1.18

            dist *= 0.95 + 0.08 * math.sin(self.anim_time * 4.2 + i * 0.9)
            px = center.x + math.cos(angle) * dist
            py = center.y + math.sin(angle) * dist
            front_points.append((int(px), int(py)))

            back_angle = angle + 0.16
            back_dist = dist * 0.88
            bx = center.x + math.cos(back_angle) * back_dist
            by = center.y + math.sin(back_angle) * back_dist
            back_points.append((int(bx), int(by)))

        pygame.draw.polygon(screen, (3, 3, 4), back_points)
        pygame.draw.polygon(screen, (8, 5, 6), front_points)
        pygame.draw.lines(screen, (105, 20, 20), True, front_points, 2)
        pygame.draw.lines(screen, ORB_ACCENT, True, front_points, 1)

    def draw_body(self, screen, center_i, radius):
        pygame.draw.circle(screen, ORB_BODY, center_i, radius)
        pygame.draw.circle(screen, (55, 12, 12), center_i, int(radius * 0.83))
        pygame.draw.circle(screen, ORB_DARK, center_i, radius, 3)
        pygame.draw.circle(screen, ORB_ACCENT, center_i, radius, 1)

    def draw_inner_shell(self, screen, center_i, radius, pulse):
        mid_r = max(4, int(radius * (0.56 + pulse * 0.03)))
        inner_r = max(3, int(radius * 0.34))

        pygame.draw.circle(screen, (18, 2, 4), center_i, mid_r)
        pygame.draw.circle(screen, ORB_ACCENT, center_i, mid_r, 2)

        pygame.draw.circle(screen, (8, 1, 2), center_i, inner_r)
        pygame.draw.circle(screen, ORB_CORE, center_i, inner_r, 1)

    def draw_rotating_cracks(self, screen, center_i, radius, draw_scale):
        cx, cy = center_i
        crack_r = radius * 0.42
        width = max(1, int(1.5 * draw_scale))

        for i in range(3):
            angle = self.inner_rotation + i * (math.tau / 3)
            angle2 = angle + 0.95

            x1 = cx + math.cos(angle) * crack_r * 0.25
            y1 = cy + math.sin(angle) * crack_r * 0.25
            x2 = cx + math.cos(angle2) * crack_r
            y2 = cy + math.sin(angle2) * crack_r

            pygame.draw.line(screen, (110, 12, 16), (x1, y1), (x2, y2), width)
            pygame.draw.line(screen, (255, 65, 65), (x1, y1), (x2, y2), 1)

    def draw_core(self, screen, fx, center_i, radius, pulse):
        core_r = max(2, int(radius * (0.11 + pulse * 0.03)))
        glow_r = max(4, int(radius * (0.24 + pulse * 0.03)))

        pygame.draw.circle(screen, (255, 110, 105), center_i, core_r + 1)
        pygame.draw.circle(screen, ORB_CORE, center_i, core_r)