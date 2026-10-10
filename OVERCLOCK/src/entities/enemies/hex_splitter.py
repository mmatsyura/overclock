import math
import random
import pygame
import pygame.gfxdraw
from src.settings import HEX_ACCENT, HEX_CORE, HEX_DARK, HEX_HIT_RADIUS, HEX_MAX_SPEED, HEX_RADIUS, HEX_SPLIT_EXIT_SPEED, HEX_SPLIT_START_SCALE, HEX_SPLIT_TIME, HEX_TURN_SPEED


class HexSplitterEnemy:
    def __init__(self, pos, world_size, split_level=0, start_velocity=None, angle=None, split_birth=False):
        self.pos = pygame.Vector2(pos)
        self.world_size = pygame.Vector2(world_size)

        self.split_level = split_level
        self.scale = [1.00, 0.86, 0.70][min(split_level, 2)]

        self.radius = HEX_RADIUS * self.scale
        self.hit_radius = HEX_HIT_RADIUS * self.scale

        self.max_speed = HEX_MAX_SPEED * (1.0 + split_level * 0.08)
        self.vel = pygame.Vector2(start_velocity) if start_velocity is not None else pygame.Vector2()
        self.angle = random.uniform(0.0, math.tau) if angle is None else angle

        self.alive = True
        self.health = 1
        self.can_damage_player = True
        self.is_hex_splitter = True

        self.score_value = [12, 8, 4][min(split_level, 2)]
        self.death_color = HEX_ACCENT
        self.death_core = HEX_CORE

        self.waypoint = self.random_waypoint()
        self.waypoint_timer = random.uniform(6.0, 10.5)

        self.anim_time = random.uniform(0.0, 100.0)
        self.outer_rotation = random.uniform(0.0, math.tau)
        self.inner_rotation = random.uniform(0.0, math.tau)
        self.spin_direction = random.choice((-1.0, 1.0))

        self.split_birth = split_birth
        self.split_birth_timer = 0.0
        self.split_visual_scale = HEX_SPLIT_START_SCALE if split_birth else 1.0
        self.split_collision_ready = not split_birth
        self.split_travel = 0.0
        self.pending_children = []
        self.last_hit_dir = pygame.Vector2(1.0, 0.0)

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
        margin = 110.0
        return pygame.Vector2(random.uniform(margin, self.world_size.x - margin), random.uniform(margin, self.world_size.y - margin))

    def choose_waypoint(self):
        for _ in range(12):
            waypoint = self.random_waypoint()

            if self.wrapped_delta(self.pos, waypoint, self.world_size).length() >= 200.0:
                self.waypoint = waypoint
                return

        self.waypoint = self.random_waypoint()

    def register_hit(self, incoming_velocity):
        hit_dir = pygame.Vector2(incoming_velocity)

        if hit_dir.length_squared() > 0.001:
            self.last_hit_dir = hit_dir.normalize()

    def take_damage(self, damage):
        self.health -= damage

        if self.health > 0:
            return False

        self.alive = False

        if self.split_level < 2:
            self.spawn_children()

        return True

    def spawn_children(self):
        forward = pygame.Vector2(self.last_hit_dir)

        if forward.length_squared() <= 0.001:
            forward = pygame.Vector2(1.0, 0.0)
        else:
            forward = forward.normalize()

        side = pygame.Vector2(-forward.y, forward.x)

        for sign in (-1.0, 1.0):
            child_velocity = side * HEX_SPLIT_EXIT_SPEED * sign
            child_angle = math.atan2(child_velocity.y, child_velocity.x)

            child = HexSplitterEnemy(self.pos.copy(), self.world_size, self.split_level + 1, child_velocity, child_angle, True)

            self.pending_children.append(child)

    def consume_children(self):
        children = self.pending_children
        self.pending_children = []
        return children

    def update_split_birth(self, dt, world_size):
        self.anim_time += dt
        self.split_birth_timer += dt

        progress = max(0.0, min(1.0, self.split_birth_timer / HEX_SPLIT_TIME))
        smooth = progress * progress * (3.0 - 2.0 * progress)

        self.split_visual_scale = HEX_SPLIT_START_SCALE + (1.0 - HEX_SPLIT_START_SCALE) * smooth

        movement = self.vel * dt
        self.pos += movement
        self.split_travel += movement.length()

        self.outer_rotation += dt * 1.8 * self.spin_direction
        self.inner_rotation -= dt * 2.5 * self.spin_direction

        if self.split_travel >= self.hit_radius * 1.08:
            self.split_collision_ready = True

        if progress >= 1.0:
            self.split_birth = False
            self.split_visual_scale = 1.0
            self.split_collision_ready = True

            if self.vel.length_squared() > 0.001:
                self.angle = math.atan2(self.vel.y, self.vel.x)

            self.choose_waypoint()
            self.waypoint_timer = random.uniform(4.5, 8.0)

    def update(self, dt, target, world_size, enemies=None, walls=None, player_projectiles=None):
        if self.split_birth:
            self.update_split_birth(dt, world_size)
            return self.wrap(world_size)
        
        self.anim_time += dt
        self.waypoint_timer -= dt

        delta = self.wrapped_delta(self.pos, self.waypoint, self.world_size)

        if delta.length() < 56.0 or self.waypoint_timer <= 0.0:
            self.choose_waypoint()
            self.waypoint_timer = random.uniform(6.0, 10.5)
            delta = self.wrapped_delta(self.pos, self.waypoint, self.world_size)

        if delta.length_squared() > 0.001:
            desired_dir = delta.normalize()
        elif self.vel.length_squared() > 0.001:
            desired_dir = self.vel.normalize()
        else:
            desired_dir = pygame.Vector2(math.cos(self.angle), math.sin(self.angle))

        if walls is not None:
            desired_dir = walls.avoidance_direction(self.pos, desired_dir, self.vel, self.hit_radius)

        desired_angle = math.atan2(desired_dir.y, desired_dir.x)
        diff = self.angle_diff(desired_angle, self.angle)
        max_turn = HEX_TURN_SPEED * dt
        self.angle += max(-max_turn, min(diff, max_turn))

        forward = pygame.Vector2(math.cos(self.angle), math.sin(self.angle))
        desired_velocity = forward * self.max_speed
        blend = 1.0 - math.exp(-3.2 * dt)

        self.vel += (desired_velocity - self.vel) * blend

        if self.vel.length() > self.max_speed:
            self.vel.scale_to_length(self.max_speed)

        self.pos += self.vel * dt

        self.outer_rotation += dt * 0.52 * self.spin_direction
        self.inner_rotation -= dt * 0.78 * self.spin_direction

        return self.wrap(world_size)

    def hex_points(self, center, radius, rotation):
        points = []

        for i in range(6):
            angle = rotation + math.tau * i / 6.0
            points.append((int(center.x + math.cos(angle) * radius), int(center.y + math.sin(angle) * radius)))

        return points

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
        if getattr(self, "spawn_intro_active", False):
            center = camera.world_to_screen_raw(self.pos, scale)
            self.draw_at(screen, fx, center, camera.render_scale(scale))
            return

        margin = self.radius * 2.5

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

    def draw_at(self, screen, fx, center, draw_scale):
        draw_scale *= self.split_visual_scale
        radius = max(11, int(self.radius * draw_scale))
        center_i = (int(center.x), int(center.y))

        outer = self.hex_points(center, radius, self.outer_rotation)
        inner = self.hex_points(center, radius * 0.63, -self.inner_rotation)
        core = self.hex_points(center, radius * 0.34, self.inner_rotation * 0.8)

        pygame.gfxdraw.filled_polygon(screen, outer, HEX_DARK)
        pygame.draw.polygon(screen, HEX_ACCENT, outer, max(2, int(2.2 * draw_scale)))
        pygame.draw.polygon(screen, HEX_CORE, outer, max(1, int(1.0 * draw_scale)))

        pygame.draw.polygon(screen, HEX_DARK, inner, max(1, int(7 * draw_scale)))
        pygame.draw.polygon(screen, HEX_ACCENT, inner, max(2, int(1.9 * draw_scale)))
        pygame.draw.polygon(screen, HEX_CORE, inner, max(1, int(1.0 * draw_scale)))

        pygame.gfxdraw.filled_polygon(screen, core, HEX_DARK)
        pygame.draw.polygon(screen, HEX_ACCENT, core, max(1, int(1.4 * draw_scale)))

        for i in range(6):
            a = pygame.Vector2(outer[i])
            b = pygame.Vector2(inner[i])
            pygame.draw.line(screen, HEX_CORE, a, b, max(1, int(1.0 * draw_scale)))