import math
import random
import pygame
from src.entities.enemy_projectile import EnemyProjectile
from src.entities.enemies.dodge import get_dodge_vector, init_dodge_state
from src.settings import PINK_BULLET_COLOR, PINK_BULLET_CORE, PINK_BULLET_LIFETIME, PINK_BULLET_RADIUS, PINK_BULLET_SPEED, PINK_SHOOTER_ACCEL, PINK_SHOOTER_ACCENT, PINK_SHOOTER_CORE, PINK_SHOOTER_HIT_RADIUS, PINK_SHOOTER_HP, PINK_SHOOTER_MAX_SPEED, PINK_SHOOTER_MIN_DISTANCE, PINK_SHOOTER_RANGE, PINK_SHOOTER_SCALE, PINK_SHOOTER_SHOOT_MAX, PINK_SHOOTER_SHOOT_MIN, PINK_SHOOTER_TURN_SPEED

class PinkShooterEnemy:
    def __init__(self, pos, world_size):
        self.pos = pygame.Vector2(pos)
        self.world_size = pygame.Vector2(world_size)
        self.vel = pygame.Vector2()

        self.angle = random.uniform(0.0, math.tau)
        self.strafe_sign = random.choice((-1.0, 1.0))
        self.strafe_timer = random.uniform(3.0, 6.0)

        self.health = PINK_SHOOTER_HP
        self.alive = True
        self.hit_radius = PINK_SHOOTER_HIT_RADIUS
        self.can_damage_player = False
        self.push_player_on_contact = True

        self.score_value = 10
        self.death_color = PINK_SHOOTER_ACCENT
        self.death_core = PINK_SHOOTER_CORE

        self.shoot_timer = random.uniform(PINK_SHOOTER_SHOOT_MIN, PINK_SHOOTER_SHOOT_MAX)
        self.pending_projectiles = []

        self.anim_time = random.uniform(0.0, 100.0)
        init_dodge_state(self)

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

    def take_damage(self, damage):
        self.health -= damage

        if self.health <= 0:
            self.alive = False
            return True

        return False

    def update(self, dt, target, world_size, enemies=None, walls=None, player_projectiles=None):
        self.anim_time += dt
        self.shoot_timer -= dt
        self.strafe_timer -= dt

        to_player = self.wrapped_delta(self.pos, target, world_size)
        distance = to_player.length()

        if distance > 0.001:
            player_dir = to_player / distance
        else:
            player_dir = pygame.Vector2(math.cos(self.angle), math.sin(self.angle))

        if self.strafe_timer <= 0.0:
            self.strafe_timer = random.uniform(3.0, 6.0)

            if random.random() < 0.65:
                self.strafe_sign *= -1.0

        side = pygame.Vector2(-player_dir.y, player_dir.x)

        if distance > PINK_SHOOTER_RANGE * 0.88:
            desired_dir = player_dir + side * self.strafe_sign * 0.28
        elif distance < PINK_SHOOTER_MIN_DISTANCE:
            desired_dir = -player_dir + side * self.strafe_sign * 0.22
        else:
            desired_dir = side * self.strafe_sign + player_dir * 0.12

        if desired_dir.length_squared() > 0.001:
            desired_dir = desired_dir.normalize()

        dodge = get_dodge_vector(self, dt, player_projectiles, 230.0, 0.48)
        if dodge.length_squared() > 0.001:
            desired_dir = (desired_dir + dodge * 1.55).normalize()

        if walls is not None:
            desired_dir = walls.avoidance_direction(self.pos, desired_dir, self.vel, self.hit_radius)

        desired_velocity = desired_dir * PINK_SHOOTER_MAX_SPEED
        steering = desired_velocity - self.vel
        max_change = PINK_SHOOTER_ACCEL * dt

        if steering.length() > max_change:
            steering.scale_to_length(max_change)

        self.vel += steering

        if self.vel.length() > PINK_SHOOTER_MAX_SPEED:
            self.vel.scale_to_length(PINK_SHOOTER_MAX_SPEED)

        self.pos += self.vel * dt

        desired_angle = math.atan2(player_dir.y, player_dir.x)
        diff = self.angle_diff(desired_angle, self.angle)
        max_turn = PINK_SHOOTER_TURN_SPEED * dt
        self.angle += max(-max_turn, min(diff, max_turn))

        if distance <= PINK_SHOOTER_RANGE and self.shoot_timer <= 0.0:
            self.fire(player_dir)
            self.shoot_timer = random.uniform(PINK_SHOOTER_SHOOT_MIN, PINK_SHOOTER_SHOOT_MAX)

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

    def fire(self, direction):
        direction = pygame.Vector2(direction)

        if direction.length_squared() <= 0.001:
            return

        direction = direction.normalize()
        spawn_pos = self.pos + direction * (25.0 * PINK_SHOOTER_SCALE)

        projectile = EnemyProjectile(spawn_pos, direction, speed=PINK_BULLET_SPEED, lifetime=PINK_BULLET_LIFETIME, radius=PINK_BULLET_RADIUS, color=PINK_BULLET_COLOR, core=PINK_BULLET_CORE, wrap=False, particle_count=(14, 19))
        self.pending_projectiles.append(projectile)

    def consume_projectiles(self):
        projectiles = self.pending_projectiles
        self.pending_projectiles = []
        return projectiles

    def draw(self, screen, fx, camera, scale):
        if getattr(self, "spawn_intro_active", False):
            center = camera.world_to_screen_raw(self.pos, scale)
            self.draw_at(screen, fx, center, camera.render_scale(scale) * PINK_SHOOTER_SCALE)
            return

        margin = 45.0 * PINK_SHOOTER_SCALE

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
                self.draw_at(screen, fx, center, camera.render_scale(scale) * PINK_SHOOTER_SCALE)

    def draw_at(self, screen, fx, center, draw_scale):
        body = [
            (34, 0),
            (24, -4),
            (11, -9),
            (-2, -15),
            (-15, -22),
            (-27, -28),
            (-31, -21),
            (-24, -9),
            (-21, -2),
            (-26, 0),
            (-21, 2),
            (-24, 9),
            (-31, 21),
            (-27, 28),
            (-15, 22),
            (-2, 15),
            (11, 9),
            (24, 4),
        ]

        body_points = self.rotated(body, self.angle, center, draw_scale)
        glow_points = self.rotated(body, self.angle, center, draw_scale * 1.08)

        pygame.draw.polygon(fx, (*PINK_SHOOTER_ACCENT, 14), glow_points)
        pygame.draw.lines(fx, (*PINK_SHOOTER_ACCENT, 34), True, body_points, max(2, int(4 * draw_scale)))

        pygame.draw.lines(screen, (88, 18, 72), True, body_points, max(2, int(3 * draw_scale)))
        pygame.draw.lines(screen, PINK_SHOOTER_ACCENT, True, body_points, max(1, int(1.35 * draw_scale)))

    @staticmethod
    def rotated(points, angle, center, scale):
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        result = []

        for x, y in points:
            rx = (x * cos_a - y * sin_a) * scale
            ry = (x * sin_a + y * cos_a) * scale
            result.append((int(center.x + rx), int(center.y + ry)))

        return result