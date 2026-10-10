import math
import random

import pygame
import pygame.gfxdraw

from src.entities.enemy_projectile import EnemyProjectile
from src.settings import RADIANT_ACCEL, RADIANT_ACCENT, RADIANT_CORE, RADIANT_HIT_RADIUS, RADIANT_HP, RADIANT_MAX_SPEED, RADIANT_RADIUS, RADIANT_SEPARATION_FORCE, RADIANT_SEPARATION_RADIUS, RADIANT_SHOOT_MAX, RADIANT_SHOOT_MIN, RADIANT_TURN_SPEED


class RadiantEnemy:
    def __init__(self, pos, world_size):
        self.pos = pygame.Vector2(pos)
        self.world_size = pygame.Vector2(world_size)

        self.vel = pygame.Vector2()

        self.angle = random.uniform(0.0, math.tau)

        self.speed = random.uniform(RADIANT_MAX_SPEED * 0.45, RADIANT_MAX_SPEED * 0.70)
        self.max_speed = RADIANT_MAX_SPEED

        self.health = RADIANT_HP
        self.alive = True

        self.hit_radius = RADIANT_HIT_RADIUS
        self.score_value = 8
        self.death_color = RADIANT_ACCENT
        self.death_core = RADIANT_CORE

        self.can_damage_player = False
        self.push_player_on_contact = True

        self.is_radiant_enemy = True

        self.waypoint = self.random_waypoint()
        self.waypoint_timer = random.uniform(5.5, 9.5)
        self.shoot_timer = random.uniform(1.8, 3.2)
        self.pending_projectiles = []
        self.anim_time = random.uniform(0.0, 100.0)

        self.outer_rotation = random.uniform(0.0, math.tau)
        self.inner_rotation = random.uniform(0.0, math.tau)

        self.spin_direction = random.choice((-1.0, 1.0))
        self.hit_flash = 0.0
        self.hit_particles = []

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

    def random_waypoint(self):
        margin = 105.0

        return pygame.Vector2(
            random.uniform(margin, self.world_size.x - margin),
            random.uniform(margin, self.world_size.y - margin)
        )

    def choose_waypoint(self):
        for _ in range(12):
            waypoint = self.random_waypoint()

            if self.wrapped_delta(self.pos, waypoint, self.world_size).length() >= 220.0:
                self.waypoint = waypoint
                return

        self.waypoint = self.random_waypoint()

    def separation(self, enemies):
        force = pygame.Vector2()

        for other in enemies:
            if other is self:
                continue

            if not getattr(other, "is_radiant_enemy", False):
                continue

            if not other.alive:
                continue

            delta = self.wrapped_delta(other.pos, self.pos, self.world_size)

            distance_sq = delta.length_squared()

            if distance_sq <= 0.001:
                continue

            if distance_sq >= RADIANT_SEPARATION_RADIUS * RADIANT_SEPARATION_RADIUS:
                continue

            distance = math.sqrt(distance_sq)

            force += delta.normalize() * (1.0 - distance / RADIANT_SEPARATION_RADIUS)

        if force.length_squared() > 1.0:
            force = force.normalize()

        return force

    def register_hit(self, incoming_velocity):
        self.hit_flash = 1.0

        impact_dir = pygame.Vector2(incoming_velocity)
        if impact_dir.length_squared() > 0.001:
            impact_dir = impact_dir.normalize()
            self.vel += impact_dir * 24.0
        else:
            impact_dir = pygame.Vector2(1.0, 0.0)

        impact_angle = math.atan2(-impact_dir.y, -impact_dir.x)

        for _ in range(random.randint(8, 12)):
            angle = impact_angle + random.uniform(-1.05, 1.05)
            life = random.uniform(0.16, 0.28)

            self.hit_particles.append({
                "dir": pygame.Vector2(math.cos(angle), math.sin(angle)),
                "distance": random.uniform(3.0, 7.0),
                "speed": random.uniform(55.0, 120.0),
                "life": life,
                "max_life": life,
                "size": random.uniform(1.0, 2.6),
            })

    def take_damage(self, damage):
        self.health -= damage

        if self.health <= 0:
            self.alive = False
            return True

        return False

    def update(self, dt, target, world_size, enemies=None, walls=None, player_projectiles=None):
        self.anim_time += dt
        self.hit_flash = max(0.0, self.hit_flash - dt * 6.0)

        alive_hit_particles = []

        for particle in self.hit_particles:
            particle["life"] -= dt

            if particle["life"] <= 0.0:
                continue

            particle["distance"] += particle["speed"] * dt
            particle["speed"] *= 0.88 ** (dt * 60.0)
            alive_hit_particles.append(particle)

        self.hit_particles = alive_hit_particles

        self.waypoint_timer -= dt
        self.shoot_timer -= dt

        delta = self.wrapped_delta(self.pos, self.waypoint, self.world_size)

        if delta.length() < 58.0 or self.waypoint_timer <= 0.0:
            self.choose_waypoint()

            self.waypoint_timer = random.uniform(5.5, 9.5)

            delta = self.wrapped_delta(self.pos, self.waypoint, self.world_size)

        if delta.length_squared() > 0.001:
            desired_dir = delta.normalize()
        else:
            desired_dir = pygame.Vector2(math.cos(self.angle), math.sin(self.angle))

        if enemies is not None:
            desired_dir += self.separation(enemies) * RADIANT_SEPARATION_FORCE

        if desired_dir.length_squared() > 0.001:
            desired_dir = desired_dir.normalize()

        if walls is not None:
            desired_dir = walls.avoidance_direction(self.pos, desired_dir, self.vel, self.hit_radius)

        desired_angle = math.atan2(desired_dir.y, desired_dir.x)

        difference = self.angle_diff(desired_angle, self.angle)

        max_turn = RADIANT_TURN_SPEED * dt

        self.angle += max(-max_turn, min(difference, max_turn))

        self.speed = min(RADIANT_MAX_SPEED, self.speed + RADIANT_ACCEL * dt)

        forward = pygame.Vector2(math.cos(self.angle), math.sin(self.angle))

        desired_velocity = forward * self.speed

        blend = 1.0 - math.exp(-4.8 * dt)

        self.vel += (desired_velocity - self.vel) * blend

        if self.vel.length() > RADIANT_MAX_SPEED:
            self.vel.scale_to_length(RADIANT_MAX_SPEED)

        self.pos += self.vel * dt

        self.outer_rotation += dt * 0.62 * self.spin_direction
        self.inner_rotation -= dt * 0.92 * self.spin_direction

        if self.shoot_timer <= 0.0:
            self.fire_triplet()

            self.shoot_timer = random.uniform(RADIANT_SHOOT_MIN, RADIANT_SHOOT_MAX)

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

    def fire_triplet(self):
        base_angle = random.uniform(0.0, math.tau)
        forward = pygame.Vector2(math.cos(base_angle), math.sin(base_angle))
        side = pygame.Vector2(-forward.y, forward.x)

        spread = 0.20
        side_spacing = 6.0

        for index in range(3):
            offset_index = index - 1
            angle = base_angle + offset_index * spread
            direction = pygame.Vector2(math.cos(angle), math.sin(angle))
            spawn_pos = self.pos + forward * (RADIANT_RADIUS + 8.0) + side * (offset_index * side_spacing)
            self.pending_projectiles.append(EnemyProjectile(spawn_pos, direction))

    def consume_projectiles(self):
        if not self.pending_projectiles:
            return []

        projectiles = self.pending_projectiles

        self.pending_projectiles = []

        return projectiles

    def draw(self, screen, fx, camera, scale):
        if getattr(self, "spawn_intro_active", False):
            center = camera.world_to_screen_raw(self.pos, scale)
            self.draw_at(screen, fx, center, camera.render_scale(scale))
            return

        world_size = camera.world_size

        margin = RADIANT_RADIUS * 2.2

        x_offsets = [0.0]
        y_offsets = [0.0]

        if self.pos.x < margin:
            x_offsets.append(world_size.x)
        elif self.pos.x > world_size.x - margin:
            x_offsets.append(-world_size.x)

        if self.pos.y < margin:
            y_offsets.append(world_size.y)
        elif self.pos.y > world_size.y - margin:
            y_offsets.append(-world_size.y)

        for x_offset in x_offsets:
            for y_offset in y_offsets:
                draw_pos = self.pos + pygame.Vector2(x_offset, y_offset)

                center = camera.world_to_screen_raw(draw_pos, scale)

                self.draw_at(
                    screen,
                    fx,
                    center,
                    camera.render_scale(scale)
                )

    def draw_at(self, screen, fx, center, draw_scale):
        radius = max(10, int(RADIANT_RADIUS * draw_scale * (1.0 + self.hit_flash * 0.065)))

        center_i = int(center.x), int(center.y)
        pulse = 0.5 + 0.5 * math.sin(self.anim_time * 2.8)

        pygame.draw.circle(screen, (5, 5, 4), center_i, int(radius * 1.05))
        pygame.draw.circle(screen, (116, 75, 14), center_i, radius, max(2, int(3 * draw_scale)))
        pygame.draw.circle(screen, RADIANT_ACCENT, center_i, radius, max(1, int(1.25 * draw_scale)))
        pygame.draw.circle(screen, (55, 39, 10), center_i, int(radius * 0.79), max(1, int(1.1 * draw_scale)))

        for index in range(12):
            angle = self.outer_rotation + math.tau * index / 12.0

            inner = radius * 0.84
            outer = radius * (0.94 if index % 2 else 1.01)

            start = center + pygame.Vector2(math.cos(angle), math.sin(angle)) * inner
            end = center + pygame.Vector2(math.cos(angle), math.sin(angle)) * outer

            color = RADIANT_CORE if index % 2 == 0 else RADIANT_ACCENT

            pygame.draw.line(screen, color, start, end, max(1, int(1.25 * draw_scale)))

        star_points = []

        point_count = 8

        for index in range(point_count * 2):
            angle = self.inner_rotation + math.tau * index / (point_count * 2)

            distance = radius * (0.70 if index % 2 == 0 else 0.36)

            star_points.append((
                int(center.x + math.cos(angle) * distance),
                int(center.y + math.sin(angle) * distance)
            ))

        pygame.gfxdraw.filled_polygon(screen, star_points, (36, 23, 4))
        pygame.gfxdraw.aapolygon(screen, star_points, RADIANT_ACCENT)
        pygame.draw.lines(screen, RADIANT_ACCENT, True, star_points, max(1, int(2.0 * draw_scale)))

        core_radius = max(3, int(radius * 0.18))

        pygame.draw.circle(screen, (7, 7, 5), center_i, core_radius + 1)
        pygame.draw.circle(screen, RADIANT_CORE, center_i, core_radius, max(1, int(1.2 * draw_scale)))

        if self.hit_flash > 0.0:
            flash = self.hit_flash
            flash_radius = int(radius * (1.04 + (1.0 - flash) * 0.16))
            pygame.draw.circle(screen, RADIANT_CORE, center_i, flash_radius, max(1, int((1.0 + flash * 2.6) * draw_scale)))

        for particle in self.hit_particles:
            life = particle["life"] / particle["max_life"]
            particle_pos = center + particle["dir"] * particle["distance"] * draw_scale
            tail = particle_pos - particle["dir"] * particle["size"] * 4.0 * draw_scale
            width = max(1, int(particle["size"] * draw_scale * life))
            pygame.draw.line(screen, RADIANT_CORE, tail, particle_pos, width)