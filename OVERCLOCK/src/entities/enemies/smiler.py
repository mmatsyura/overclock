import math
import random

import pygame
import pygame.gfxdraw

from src.settings import SMILER_COLOR, SMILER_CORE_COLOR, SMILER_CORE_RADIUS, SMILER_DARK, SMILER_EMERGE_TIME, SMILER_HIT_RADIUS, SMILER_OPEN_TIME, SMILER_ORB_COUNT, SMILER_ORB_RADIUS, SMILER_ORBIT_RADIUS, SMILER_RAGE_ACCEL, SMILER_RAGE_SPEED, SMILER_RAGE_TURN_SPEED


class SmilerEnemy:
    def __init__(self, pos, world_size):
        self.pos = pygame.Vector2(pos)
        self.world_size = pygame.Vector2(world_size)
        self.vel = pygame.Vector2()

        self.angle = random.uniform(0.0, math.tau)
        self.orbit_rotation = random.uniform(0.0, math.tau)
        self.spin_direction = random.choice((-1.0, 1.0))

        self.alive = True
        self.health = 1
        self.score_value = 6

        self.death_color = SMILER_COLOR
        self.death_core = SMILER_CORE_COLOR

        self.hit_radius = SMILER_HIT_RADIUS

        self.state = "opening"
        self.orbs_alive = [True] * SMILER_ORB_COUNT

        self.can_damage_player = False
        self.kills_enemies_on_contact = False
        self.hazard_family = "white_orb_hazard"

        self.open_timer = 0.0
        self.open_progress = 0.0
        self.emerge_progress = 0.0

        self.waypoint = self.random_waypoint()
        self.waypoint_timer = random.uniform(3.5, 6.5)

        self.birth_particles = []
        self.birth_particle_timer = 0.0

        self.anim_time = random.uniform(0.0, 100.0)

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

    @staticmethod
    def angle_diff(target, current):
        return (target - current + math.pi) % math.tau - math.pi

    @staticmethod
    def smoothstep(value):
        value = max(0.0, min(1.0, value))
        return value * value * (3.0 - 2.0 * value)

    def random_waypoint(self):
        margin = 100.0
        return pygame.Vector2(random.uniform(margin, self.world_size.x - margin), random.uniform(margin, self.world_size.y - margin))

    def choose_waypoint(self):
        for _ in range(15):
            waypoint = self.random_waypoint()

            if self.wrapped_delta(self.pos, waypoint, self.world_size).length() > 280.0:
                self.waypoint = waypoint
                return

        self.waypoint = self.random_waypoint()

    def take_damage(self, damage):
        self.health -= damage

        if self.health <= 0:
            self.alive = False
            return True

        return False

    def orb_spawn_progress(self, index):
        if self.open_timer <= SMILER_EMERGE_TIME:
            return 0.0

        orb_duration = max(0.001, SMILER_OPEN_TIME - SMILER_EMERGE_TIME)
        orb_progress = max(0.0, min(1.0, (self.open_timer - SMILER_EMERGE_TIME) / orb_duration))
        value = orb_progress * SMILER_ORB_COUNT - index

        return self.smoothstep(max(0.0, min(1.0, value)))

    def get_orb_positions(self):
        result = []

        for index in range(SMILER_ORB_COUNT):
            if not self.orbs_alive[index]:
                continue

            progress = 1.0 if self.state == "rage" else self.orb_spawn_progress(index)

            if progress <= 0.0:
                continue

            angle = self.orbit_rotation + math.tau * index / SMILER_ORB_COUNT
            radius = SMILER_ORBIT_RADIUS * progress
            position = self.pos + pygame.Vector2(math.cos(angle), math.sin(angle)) * radius

            position.x %= self.world_size.x
            position.y %= self.world_size.y

            result.append((index, position, SMILER_ORB_RADIUS * progress))

        return result

    def break_orb(self, index):
        if index < 0 or index >= len(self.orbs_alive):
            return False

        if not self.orbs_alive[index]:
            return False

        self.orbs_alive[index] = False

        if not any(self.orbs_alive):
            self.alive = False
            return True

        return False

    def get_hazard_points(self):
        if not self.kills_enemies_on_contact:
            return []

        points = []

        for index, orb_pos, orb_radius in self.get_orb_positions():
            points.append((orb_pos, orb_radius, index))

        return points

    def update(self, dt, target, world_size, enemies=None, walls=None, player_projectiles=None):
        self.anim_time += dt
        self.update_birth_particles(dt)

        if self.state == "opening":
            self.update_opening(dt)
        else:
            self.update_rage(dt, walls)

        return self.wrap(world_size)

    def update_opening(self, dt):
        self.open_timer += dt
        self.open_progress = max(0.0, min(1.0, self.open_timer / SMILER_OPEN_TIME))
        self.emerge_progress = max(0.0, min(1.0, self.open_timer / SMILER_EMERGE_TIME))

        spin_speed = 0.4 + self.open_progress * 3.0
        self.orbit_rotation += dt * spin_speed * self.spin_direction

        self.birth_particle_timer -= dt

        if self.open_timer < 3.0 and self.birth_particle_timer <= 0.0:
            self.birth_particle_timer = random.uniform(0.045, 0.095)
            self.spawn_birth_particle()

        if self.open_progress >= 1.0:
            self.state = "rage"
            self.can_damage_player = True
            self.kills_enemies_on_contact = True

            direction = pygame.Vector2(random.uniform(-1.0, 1.0), random.uniform(-1.0, 1.0))

            if direction.length_squared() <= 0.001:
                direction = pygame.Vector2(1.0, 0.0)
            else:
                direction = direction.normalize()

            self.vel = direction * SMILER_RAGE_SPEED * 0.55
            self.angle = math.atan2(direction.y, direction.x)

            self.choose_waypoint()

    def update_rage(self, dt, walls):
        self.waypoint_timer -= dt

        delta = self.wrapped_delta(self.pos, self.waypoint, self.world_size)

        if delta.length() < 75.0 or self.waypoint_timer <= 0.0:
            self.choose_waypoint()
            self.waypoint_timer = random.uniform(2.8, 5.5)
            delta = self.wrapped_delta(self.pos, self.waypoint, self.world_size)

        if delta.length_squared() > 0.001:
            desired_dir = delta.normalize()
        elif self.vel.length_squared() > 0.001:
            desired_dir = self.vel.normalize()
        else:
            desired_dir = pygame.Vector2(math.cos(self.angle), math.sin(self.angle))

        if walls is not None:
            desired_dir = walls.avoidance_direction(self.pos, desired_dir, self.vel, SMILER_ORBIT_RADIUS + SMILER_ORB_RADIUS)

        desired_angle = math.atan2(desired_dir.y, desired_dir.x)
        diff = self.angle_diff(desired_angle, self.angle)
        max_turn = SMILER_RAGE_TURN_SPEED * dt

        self.angle += max(-max_turn, min(diff, max_turn))

        forward = pygame.Vector2(math.cos(self.angle), math.sin(self.angle))
        desired_velocity = forward * SMILER_RAGE_SPEED
        steering = desired_velocity - self.vel
        max_change = SMILER_RAGE_ACCEL * dt

        if steering.length() > max_change:
            steering.scale_to_length(max_change)

        self.vel += steering

        if self.vel.length() > SMILER_RAGE_SPEED:
            self.vel.scale_to_length(SMILER_RAGE_SPEED)

        self.pos += self.vel * dt
        self.orbit_rotation += dt * 6.7 * self.spin_direction

    def spawn_birth_particle(self):
        angle = random.uniform(0.0, math.tau)
        distance = random.uniform(SMILER_CORE_RADIUS * 0.4, SMILER_ORBIT_RADIUS * 0.55)
        life = random.uniform(0.25, 0.55)

        self.birth_particles.append({
            "pos": self.pos + pygame.Vector2(math.cos(angle), math.sin(angle)) * distance,
            "vel": pygame.Vector2(math.cos(angle), math.sin(angle)) * random.uniform(10.0, 32.0),
            "life": life,
            "max_life": life,
            "size": random.uniform(1.0, 2.6),
        })

    def update_birth_particles(self, dt):
        alive = []

        for particle in self.birth_particles:
            particle["life"] -= dt

            if particle["life"] <= 0.0:
                continue

            particle["pos"] += particle["vel"] * dt
            particle["vel"] *= 0.90 ** (dt * 60.0)
            alive.append(particle)

        self.birth_particles = alive

    def wrap(self, world_size):
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
        margin = SMILER_ORBIT_RADIUS + SMILER_ORB_RADIUS + 10.0

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
                center = camera.world_to_screen_raw(draw_pos, scale)
                self.draw_at(screen, fx, center, camera.render_scale(scale))

        self.draw_birth_particles(screen, fx, camera, scale)

    def draw_at(self, screen, fx, center, draw_scale):
        emerge = self.smoothstep(self.emerge_progress)

        core_radius = max(4, int(SMILER_CORE_RADIUS * draw_scale * (0.28 + 0.72 * emerge)))
        center_i = (int(center.x), int(center.y))

        points = []

        for index in range(6):
            angle = self.orbit_rotation * 0.18 + math.tau * index / 6.0
            points.append((int(center.x + math.cos(angle) * core_radius), int(center.y + math.sin(angle) * core_radius)))

        pygame.gfxdraw.filled_polygon(screen, points, SMILER_DARK)
        pygame.draw.lines(screen, (115, 120, 125), True, points, max(2, int(2.5 * draw_scale)))
        pygame.draw.lines(screen, SMILER_COLOR, True, points, max(1, int(1.2 * draw_scale)))

        for index in range(SMILER_ORB_COUNT):
            if not self.orbs_alive[index]:
                continue

            progress = 1.0 if self.state == "rage" else self.orb_spawn_progress(index)

            if progress <= 0.0:
                continue

            angle = self.orbit_rotation + math.tau * index / SMILER_ORB_COUNT
            orbit_radius = SMILER_ORBIT_RADIUS * draw_scale * progress
            orb_center = pygame.Vector2(center) + pygame.Vector2(math.cos(angle), math.sin(angle)) * orbit_radius

            self.draw_orb(screen, fx, orb_center, draw_scale, progress, angle)

    def draw_orb(self, screen, fx, center, draw_scale, progress, angle):
        radius = max(2, int(SMILER_ORB_RADIUS * draw_scale * progress))
        center_i = (int(center.x), int(center.y))

        points = []

        blade_count = 4

        for index in range(blade_count * 2):
            blade_angle = -angle * 1.7 + math.tau * index / (blade_count * 2)

            if index % 2 == 0:
                distance = radius * 1.55
            else:
                distance = radius * 0.68

            points.append((int(center.x + math.cos(blade_angle) * distance), int(center.y + math.sin(blade_angle) * distance)))

        pygame.gfxdraw.filled_polygon(screen, points, SMILER_DARK)
        pygame.draw.lines(screen, SMILER_COLOR, True, points, max(1, int(1.25 * draw_scale)))

        core_radius = max(1, int(radius * 0.32))

        pygame.draw.circle(screen, SMILER_CORE_COLOR, center_i, core_radius)

    def draw_birth_particles(self, screen, fx, camera, scale):
        draw_scale = camera.render_scale(scale)

        for particle in self.birth_particles:
            life = particle["life"] / particle["max_life"]
            pos = camera.world_to_screen(particle["pos"], scale)
            radius = max(1, int(particle["size"] * draw_scale * life))

            pygame.draw.circle(fx, (*SMILER_COLOR, int(55 * life)), pos, radius * 2)
            pygame.draw.circle(screen, (155, 160, 165), pos, radius)