import math
import random

import pygame

from src.settings import ENEMY_BULLET_COLOR, ENEMY_BULLET_CORE, ENEMY_BULLET_DAMAGE_MAX, ENEMY_BULLET_DAMAGE_MIN, ENEMY_BULLET_LIFETIME, ENEMY_BULLET_RADIUS, ENEMY_BULLET_SPEED


class EnemyProjectile:
    def __init__(self, pos, direction, speed=ENEMY_BULLET_SPEED, 
                 lifetime=ENEMY_BULLET_LIFETIME, radius=ENEMY_BULLET_RADIUS, color=ENEMY_BULLET_COLOR, core=ENEMY_BULLET_CORE, wrap=True, particle_count=(17, 23), damage=None):
        self.pos = pygame.Vector2(pos)
        self.prev_pos = self.pos.copy()
        self.direction = pygame.Vector2(direction)

        if self.direction.length_squared() <= 0.001:
            self.direction = pygame.Vector2(1.0, 0.0)
        else:
            self.direction = self.direction.normalize()

        self.vel = self.direction * speed
        self.life = lifetime
        self.radius = radius
        self.color = color
        self.core = core
        self.wrap = wrap
        self.particle_count = particle_count
        self.damage = random.randint(ENEMY_BULLET_DAMAGE_MIN, ENEMY_BULLET_DAMAGE_MAX) if damage is None else int(damage)

        self.active = True
        self.alive = True
        self.explosion_age = 0.0
        self.explosion_duration = 0.28
        self.particles = []

    def update(self, dt, world_size, walls=None):
        if self.active:
            self.prev_pos = self.pos.copy()
            next_pos = self.pos + self.vel * dt
            self.life -= dt

            if walls is not None:
                closest_hit = None

                for wall in walls.walls:
                    hit = walls.sweep_circle_wall(self.prev_pos, next_pos, wall, self.radius)

                    if hit is not None and (closest_hit is None or hit[0] < closest_hit[0]):
                        closest_hit = hit

                if closest_hit is not None:
                    self.pos = closest_hit[1]
                    self.explode()
                    return

            self.pos = next_pos

            if self.wrap:
                self.pos.x %= world_size.x
                self.pos.y %= world_size.y
            else:
                if self.pos.x < 0.0 or self.pos.x > world_size.x or self.pos.y < 0.0 or self.pos.y > world_size.y:
                    self.pos.x = max(0.0, min(world_size.x, self.pos.x))
                    self.pos.y = max(0.0, min(world_size.y, self.pos.y))
                    self.explode()
                    return

            if self.life <= 0.0:
                self.explode()

            return

        self.explosion_age += dt
        frame_drag = 0.86 ** (dt * 60.0)
        alive_particles = []

        for particle in self.particles:
            particle["life"] -= dt

            if particle["life"] <= 0.0:
                continue

            particle["pos"] += particle["vel"] * dt
            particle["pos"].x %= world_size.x
            particle["pos"].y %= world_size.y
            particle["vel"] *= frame_drag
            alive_particles.append(particle)

        self.particles = alive_particles

        if self.explosion_age >= self.explosion_duration and not self.particles:
            self.alive = False

    def explode(self):
        if not self.active:
            return

        self.active = False
        self.explosion_age = 0.0

        for _ in range(random.randint(self.particle_count[0], self.particle_count[1])):
            angle = random.uniform(0.0, math.tau)
            direction = pygame.Vector2(math.cos(angle), math.sin(angle))
            life = random.uniform(0.22, 0.38)

            self.particles.append({"pos": self.pos.copy(), "vel": direction * random.uniform(38.0, 92.0), "life": life, "max_life": life, "size": random.uniform(1.3, 3.2)})

    def draw(self, screen, fx, camera, scale):
        if self.active:
            self.draw_bullet(screen, fx, camera, scale)
        else:
            self.draw_explosion(screen, fx, camera, scale)

    def draw_bullet(self, screen, fx, camera, scale):
        draw_scale = camera.render_scale(scale)
        world_size = camera.world_size

        margin = 18.0

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
                pos = camera.world_to_screen_raw(draw_pos, scale)

                tail = pos - self.direction * (8.0 * draw_scale)

                radius = max(2, int(self.radius * draw_scale))

                pygame.draw.line(fx, (*self.color, 55), tail, pos, max(2, int(4 * draw_scale)))

                pygame.draw.circle(fx, (*self.color, 42), pos, radius * 3)
                pygame.draw.circle(fx, (*self.color, 110), pos, radius * 2)

                pygame.draw.circle(screen, self.color, pos, radius)
                pygame.draw.circle(screen, self.core, pos, max(1, radius // 2))

    def draw_explosion(self, screen, fx, camera, scale):
        draw_scale = camera.render_scale(scale)

        t = max(0.0, min(1.0, self.explosion_age / self.explosion_duration))
        fade = 1.0 - t

        center = camera.world_to_screen(self.pos, scale)

        ring_radius = max(2, int((4.0 + 11.0 * t) * draw_scale))

        pygame.draw.circle(fx, (*self.color, int(90 * fade)), center, ring_radius, max(1, int(1.4 * draw_scale)))

        for particle in self.particles:
            life = particle["life"] / particle["max_life"]

            pos = camera.world_to_screen(particle["pos"], scale)

            radius = max(1, int(particle["size"] * draw_scale * life))

            pygame.draw.circle(fx, (*self.color, int(120 * life)), pos, radius * 2)
            pygame.draw.circle(screen, self.core, pos, radius)