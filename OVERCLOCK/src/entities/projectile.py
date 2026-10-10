import pygame
from src.settings import BULLET_SPEED, BULLET_LIFETIME, BULLET_HIT_RADIUS


class Projectile:
    def __init__(self, pos, direction):
        self.pos = pygame.Vector2(pos)
        self.prev_pos = self.pos.copy()
        self.direction = pygame.Vector2(direction).normalize()
        self.vel = self.direction * BULLET_SPEED
        self.life = BULLET_LIFETIME
        self.alive = True
        self.ricocheted = False

    def update(self, dt, world_size, walls=None):
        self.prev_pos = self.pos.copy()
        self.pos += self.vel * dt
        self.life -= dt
        self.ricocheted = False

        if walls is not None:
            self.ricocheted = walls.ricochet_projectile(self, BULLET_HIT_RADIUS)

        if self.pos.x < 0:
            self.alive = False
            return "left", max(0.0, min(1.0, self.pos.y / world_size.y))

        if self.pos.x > world_size.x:
            self.alive = False
            return "right", max(0.0, min(1.0, self.pos.y / world_size.y))

        if self.pos.y < 0:
            self.alive = False
            return "top", max(0.0, min(1.0, self.pos.x / world_size.x))

        if self.pos.y > world_size.y:
            self.alive = False
            return "bottom", max(0.0, min(1.0, self.pos.x / world_size.x))

        if self.life <= 0:
            self.alive = False

        return None

    def collides_with(self, point, radius):
        point = pygame.Vector2(point)
        segment = self.pos - self.prev_pos
        length_sq = segment.length_squared()

        if length_sq <= 0.001:
            return self.pos.distance_squared_to(point) <= radius * radius

        t = (point - self.prev_pos).dot(segment) / length_sq
        t = max(0.0, min(1.0, t))

        closest = self.prev_pos + segment * t
        return closest.distance_squared_to(point) <= radius * radius

    def draw(self, screen, fx, camera, scale):
        pos = camera.world_to_screen(self.pos, scale)
        draw_scale = camera.render_scale(scale)

        tail_far = pos - self.direction * (36 * draw_scale)
        tail_mid = pos - self.direction * (23 * draw_scale)
        tail_core = pos - self.direction * (14 * draw_scale)

        glow = (255, 165, 25)
        yellow = (255, 205, 55)
        hot = (255, 235, 120)
        core = (255, 254, 225)

        pygame.draw.line(fx, (*glow, 18), tail_far, pos, max(8, int(17 * draw_scale)))
        pygame.draw.line(fx, (*glow, 42), tail_far, pos, max(5, int(10 * draw_scale)))
        pygame.draw.line(fx, (*yellow, 115), tail_mid, pos, max(3, int(6 * draw_scale)))
        pygame.draw.line(fx, (*hot, 220), tail_core, pos, max(2, int(4 * draw_scale)))
        pygame.draw.line(screen, core, tail_core, pos, max(2, int(2.5 * draw_scale)))

        pygame.draw.circle(fx, (*yellow, 75), pos, max(5, int(8 * draw_scale)))
        pygame.draw.circle(fx, (*hot, 150), pos, max(3, int(5 * draw_scale)))
        pygame.draw.circle(screen, core, pos, max(2, int(3 * draw_scale)))
