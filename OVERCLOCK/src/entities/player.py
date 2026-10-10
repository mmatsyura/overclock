import math
import random

import pygame
import pygame.gfxdraw

from src.entities.projectile import Projectile
from src.settings import PLAYER_ACCENT, PLAYER_ACCEL, PLAYER_BODY, PLAYER_BRAKE, PLAYER_CORE, PLAYER_DRAG, PLAYER_LOW_SPEED_TURN, PLAYER_MAX_SPEED, PLAYER_SCALE, PLAYER_TURN_SPEED, SHOT_DELAY


class Player:
    BODY_POINTS = [(0, -38), (8, -22), (11, -7), (31, 8), (38, 29), (14, 17), (8, 32), (0, 22), (-8, 32), (-14, 17), (-38, 29), (-31, 8), (-11, -7), (-8, -22)]

    def __init__(self, pos):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2()
        self.angle = -math.pi / 2
        self.engine_particles = []
        self.reverse_timer = 0.0
        self.shot_timer = 0.0

        self.hit_flash = 0.0
        self.hit_normal = pygame.Vector2(0.0, -1.0)
        self.hit_color = PLAYER_ACCENT
        self.hit_particles = []

    @staticmethod
    def angle_diff(target, current):
        return (target - current + math.pi) % math.tau - math.pi

    @staticmethod
    def rotated(points, angle, center, scale=1.0):
        c, s = math.cos(angle), math.sin(angle)
        return [(int(center.x + x * scale * c - y * scale * s), int(center.y + x * scale * s + y * scale * c)) for x, y in points]

    def update(self, dt, mouse_world, thrusting, world_size):
        self.reverse_timer = max(0.0, self.reverse_timer - dt)
        delta = pygame.Vector2(mouse_world) - self.pos
        wrap_event = None
        if delta.length_squared() > 20 * 20:
            target_dir = delta.normalize()
            desired_angle = math.atan2(target_dir.y, target_dir.x)
            diff = self.angle_diff(desired_angle, self.angle)
            speed01 = min(1.0, self.vel.length() / PLAYER_MAX_SPEED)
            turn_speed = PLAYER_LOW_SPEED_TURN + (PLAYER_TURN_SPEED - PLAYER_LOW_SPEED_TURN) * speed01
            max_turn = turn_speed * dt
            self.angle += max(-max_turn, min(diff, max_turn))
        forward = pygame.Vector2(math.cos(self.angle), math.sin(self.angle))
        speed = self.vel.length()
        if thrusting:
            if speed > 25:
                velocity_dir = self.vel.normalize()
                alignment = velocity_dir.dot(forward)
                if alignment < -0.35:
                    brake = PLAYER_BRAKE * 0.72
                    new_speed = max(0.0, speed - brake * dt)
                    if new_speed <= 35:
                        self.vel.xy = 0, 0
                        self.reverse_timer = 0.24
                    else:
                        self.vel.scale_to_length(new_speed)
                else:
                    accel = PLAYER_ACCEL
                    if self.reverse_timer > 0:
                        progress = 1.0 - self.reverse_timer / 0.24
                        accel *= 0.45 + 0.55 * progress
                    self.vel += forward * accel * dt
            else:
                accel = PLAYER_ACCEL
                if self.reverse_timer > 0:
                    progress = 1.0 - self.reverse_timer / 0.24
                    accel *= 0.45 + 0.55 * progress
                self.vel += forward * accel * dt
            if self.vel.length() > PLAYER_MAX_SPEED: self.vel.scale_to_length(PLAYER_MAX_SPEED)
            self.emit_engine_particles(dt, 1.0)
        elif speed > 0:
            new_speed = max(0.0, speed - PLAYER_DRAG * dt)
            if new_speed <= 0: self.vel.xy = 0, 0
            else: self.vel.scale_to_length(new_speed)
        self.pos += self.vel * dt
        if self.pos.x >= world_size.x:
            wrap_event = ("right", max(0.0, min(1.0, self.pos.y / world_size.y)))
            self.pos.x -= world_size.x
        elif self.pos.x < 0:
            wrap_event = ("left", max(0.0, min(1.0, self.pos.y / world_size.y)))
            self.pos.x += world_size.x
        if self.pos.y >= world_size.y:
            wrap_event = ("bottom", max(0.0, min(1.0, self.pos.x / world_size.x)))
            self.pos.y -= world_size.y
        elif self.pos.y < 0:
            wrap_event = ("top", max(0.0, min(1.0, self.pos.x / world_size.x)))
            self.pos.y += world_size.y

        self.update_particles(dt, world_size)
        self.update_hit_fx(dt, world_size)
        return wrap_event

    def emit_engine_particles(self, dt, power):
        speed01 = min(1.0, self.vel.length() / PLAYER_MAX_SPEED)
        count = max(1, int((12 + 18 * speed01) * power * dt * 60))
        back = pygame.Vector2(math.cos(self.angle + math.pi), math.sin(self.angle + math.pi))
        side = pygame.Vector2(-back.y, back.x)
        origin = self.pos + back * 25
        colors = [(55, 135, 255), (70, 170, 255), (110, 210, 255), (185, 238, 255), (235, 250, 255)]
        for _ in range(count):
            spread = random.uniform(-0.22, 0.22)
            direction = back + side * spread
            if direction.length_squared() > 0: direction = direction.normalize()
            speed = random.uniform(90, 175) * (0.85 + speed01 * 0.45)
            velocity = direction * speed + self.vel * 0.04
            velocity += side * random.uniform(-16, 16)
            life = random.uniform(0.16, 0.28)
            self.engine_particles.append({"pos": origin + side * random.uniform(-2.2, 2.2) + back * random.uniform(-1, 1), "vel": velocity, "life": life, "max_life": life, "length": random.uniform(12, 22) * (0.9 + speed01 * 0.35), "width": random.choice((1.8, 2.2, 2.6, 3.0)), "color": random.choice(colors)})
        if len(self.engine_particles) > 260: self.engine_particles = self.engine_particles[-260:]

    def update_particles(self, dt, world_size):
        alive = []

        for particle in self.engine_particles:
            particle["life"] -= dt

            if particle["life"] <= 0:
                continue

            particle["pos"] += particle["vel"] * dt
            particle["pos"].x %= world_size.x
            particle["pos"].y %= world_size.y
            particle["vel"] *= 0.965
            particle["length"] *= 0.985

            alive.append(particle)

        self.engine_particles = alive

    def register_damage_hit(self, incoming_velocity, color=None):
        incoming = pygame.Vector2(incoming_velocity)

        if incoming.length_squared() > 0.001:
            self.hit_normal = -incoming.normalize()
        else:
            self.hit_normal = pygame.Vector2(-math.cos(self.angle), -math.sin(self.angle))

        self.hit_color = tuple(color) if color is not None else PLAYER_ACCENT
        self.hit_flash = 1.0

        tangent = pygame.Vector2(-self.hit_normal.y, self.hit_normal.x)
        origin = self.pos + self.hit_normal * 22.0

        for _ in range(random.randint(18, 26)):
            direction = self.hit_normal * random.uniform(0.65, 1.20) + tangent * random.uniform(-0.85, 0.85)

            if direction.length_squared() > 0.001:
                direction = direction.normalize()

            life = random.uniform(0.22, 0.38)

            self.hit_particles.append({"pos": origin + tangent * random.uniform(-5.0, 5.0), "vel": direction * random.uniform(85.0, 175.0) + self.vel * 0.12, "life": life, "max_life": life, "length": random.uniform(5.0, 11.0), "color": self.hit_color})

        if len(self.hit_particles) > 60:
            self.hit_particles = self.hit_particles[-60:]

    def update_hit_fx(self, dt, world_size):
        self.hit_flash = max(0.0, self.hit_flash - dt * 4.1)
        drag = 0.84 ** (dt * 60.0)
        alive = []

        for particle in self.hit_particles:
            particle["life"] -= dt

            if particle["life"] <= 0.0:
                continue

            particle["pos"] += particle["vel"] * dt
            particle["pos"].x %= world_size.x
            particle["pos"].y %= world_size.y
            particle["vel"] *= drag
            particle["length"] *= 0.97

            alive.append(particle)

        self.hit_particles = alive

    def draw_engine_glow(self, fx, center, draw_scale):
        speed01 = min(1.0, self.vel.length() / PLAYER_MAX_SPEED)
        if speed01 < 0.03: return
        back = pygame.Vector2(math.cos(self.angle + math.pi), math.sin(self.angle + math.pi))
        pos = center + back * (18 * draw_scale)
        pygame.draw.circle(fx, (30, 120, 255, int(30 + 45 * speed01)), pos, max(3, int(8 * draw_scale)))
        pygame.draw.circle(fx, (100, 210, 255, int(80 + 80 * speed01)), pos, max(2, int(4 * draw_scale)))
        pygame.draw.circle(fx, (220, 250, 255, int(120 + 100 * speed01)), pos, max(1, int(2 * draw_scale)))

    def draw(self, screen, fx, camera, scale):
        self.draw_engine_particles(fx, camera, scale)
        self.draw_hit_particles(fx, camera, scale)
        world_size = camera.world_size
        margin = 58.0
        positions = [self.pos.copy()]
        x_offsets = [0.0]
        y_offsets = [0.0]
        if self.pos.x < margin: x_offsets.append(world_size.x)
        if self.pos.x > world_size.x - margin: x_offsets.append(-world_size.x)
        if self.pos.y < margin: y_offsets.append(world_size.y)
        if self.pos.y > world_size.y - margin: y_offsets.append(-world_size.y)
        positions = [self.pos + pygame.Vector2(x_offset, y_offset) for x_offset in x_offsets for y_offset in y_offsets]
        for world_pos in positions: self.draw_at(screen, fx, camera, scale, world_pos)

    def draw_at(self, screen, fx, camera, scale, world_pos):
        center = camera.world_to_screen_unwrapped(world_pos, scale)
        draw_scale = camera.render_scale(scale)

        self.draw_engine_glow(fx, center, draw_scale)

        angle = self.angle + math.pi / 2
        player_scale = draw_scale * PLAYER_SCALE
        glow_far = self.rotated(self.BODY_POINTS, angle, center, player_scale * 1.22)
        glow_near = self.rotated(self.BODY_POINTS, angle, center, player_scale * 1.10)
        body_points = self.rotated(self.BODY_POINTS, angle, center, player_scale)

        pygame.draw.polygon(fx, (*PLAYER_ACCENT, 12), glow_far)
        pygame.draw.polygon(fx, (*PLAYER_ACCENT, 28), glow_near)
        pygame.gfxdraw.filled_polygon(screen, body_points, PLAYER_BODY)
        pygame.draw.lines(screen, (27, 83, 120), True, body_points, max(3, int(4 * draw_scale)))
        pygame.draw.lines(screen, PLAYER_ACCENT, True, body_points, max(1, int(2 * draw_scale)))
        pygame.gfxdraw.aapolygon(screen, body_points, PLAYER_CORE)

        if self.hit_flash > 0.0:
            self.draw_hit_arc(fx, center, draw_scale)
            pygame.draw.lines(fx, (*self.hit_color, int(70 * self.hit_flash)), True, body_points, max(1, int(3 * draw_scale)))
            pygame.draw.lines(fx, (*PLAYER_CORE, int(145 * self.hit_flash)), True, body_points, max(1, int(2 * draw_scale)))

    def draw_hit_arc(self, fx, center, draw_scale):
        if self.hit_flash <= 0.0:
            return

        fade = self.hit_flash * self.hit_flash
        normal = self.hit_normal
        tangent = pygame.Vector2(-normal.y, normal.x)

        base = center + normal * (34.0 * draw_scale)
        width = 21.0 * draw_scale
        depth = 10.0 * draw_scale

        left = base - tangent * width
        middle = base + normal * depth
        right = base + tangent * width

        pygame.draw.lines(fx, (*self.hit_color, int(155 * fade)), False, (left, middle, right), max(2, int(4.0 * draw_scale)))
        pygame.draw.lines(fx, (*PLAYER_CORE, int(220 * fade)), False, (left, middle, right), max(1, int(1.8 * draw_scale)))

        left_tip = left + normal * (7.0 * draw_scale) - tangent * (4.0 * draw_scale)
        right_tip = right + normal * (7.0 * draw_scale) + tangent * (4.0 * draw_scale)

        pygame.draw.line(fx, (*self.hit_color, int(125 * fade)), left, left_tip, max(1, int(2.4 * draw_scale)))
        pygame.draw.line(fx, (*self.hit_color, int(125 * fade)), right, right_tip, max(1, int(2.4 * draw_scale)))

        inner_left = base - tangent * (width * 0.55)
        inner_right = base + tangent * (width * 0.55)
        inner_mid = base + normal * (depth * 0.55)

        pygame.draw.lines(fx, (*self.hit_color, int(95 * fade)), False, (inner_left, inner_mid, inner_right), max(1, int(2.0 * draw_scale)))

    def draw_hit_particles(self, fx, camera, scale):
        draw_scale = camera.render_scale(scale)

        for particle in self.hit_particles:
            life = particle["life"] / particle["max_life"]

            if particle["vel"].length_squared() <= 0.001:
                continue

            pos = camera.world_to_screen(particle["pos"], scale)
            direction = particle["vel"].normalize()
            length = particle["length"] * draw_scale * life
            tail = pos - direction * length
            color = particle["color"]

            pygame.draw.line(fx, (*color, int(125 * life)), tail, pos, max(1, int(2.1 * draw_scale)))
            pygame.draw.line(fx, (*PLAYER_CORE, int(190 * life)), pos - direction * length * 0.35, pos, max(1, int(draw_scale)))

    def draw_engine_particles(self, fx, camera, scale):
        draw_scale = camera.render_scale(scale)
        for particle in self.engine_particles:
            pos = camera.world_to_screen(particle["pos"], scale)
            life01 = particle["life"] / particle["max_life"]
            if particle["vel"].length_squared() < 0.01: continue
            direction = particle["vel"].normalize()
            length = particle["length"] * draw_scale * (0.75 + life01 * 0.45)
            tail = pos - direction * length
            middle = pos - direction * length * 0.45
            fade = life01 * life01
            color = particle["color"]
            glow_width = max(3, int((particle["width"] * 4.8) * draw_scale))
            main_width = max(2, int((particle["width"] * 2.8) * draw_scale))
            core_width = max(1, int((particle["width"] * 1.4) * draw_scale))
            pygame.draw.line(fx, (*color, int(42 * fade)), tail, pos, glow_width)
            pygame.draw.line(fx, (*color, int(165 * fade)), tail, pos, main_width)
            bright = (min(255, color[0] + 70), min(255, color[1] + 45), 255, int(255 * fade))
            pygame.draw.line(fx, bright, middle, pos, core_width)

    def update_weapon(self, dt, shooting):
        self.shot_timer = max(0.0, self.shot_timer - dt)
        if shooting and self.shot_timer <= 0:
            self.shot_timer = SHOT_DELAY
            return self.shoot()
        return None

    def shoot(self):
        direction = pygame.Vector2(math.cos(self.angle), math.sin(self.angle))
        spawn_pos = self.pos + direction * 32
        return Projectile(spawn_pos, direction)
