import math
import pygame

class Camera:
    def __init__(self, viewport_size, world_size):
        self.viewport_size = pygame.Vector2(viewport_size)
        self.world_size = pygame.Vector2(world_size)
        self.base_focus = self.world_size * 0.5
        self.focus = self.base_focus.copy()
        self.target_focus = self.base_focus.copy()
        self.zoom = 1.0
        self.target_zoom = 1.0
        self.focus_speed = 10.0
        self.zoom_speed = 10.0
        self.shake = 0.0
        self.shake_time = 0.0
        self.shake_offset = pygame.Vector2()

    def add_shake(self, amount):
        self.shake = min(2.4, self.shake + amount)

    def render_scale(self, scale):
        return scale * self.zoom

    def wrapped_delta(self, source, target):
        delta = pygame.Vector2(target) - pygame.Vector2(source)
        if delta.x > self.world_size.x * 0.5: delta.x -= self.world_size.x
        elif delta.x < -self.world_size.x * 0.5: delta.x += self.world_size.x
        if delta.y > self.world_size.y * 0.5: delta.y -= self.world_size.y
        elif delta.y < -self.world_size.y * 0.5: delta.y += self.world_size.y
        return delta

    def update(self, dt):
        focus_lerp = 1.0 - math.exp(-self.focus_speed * dt)
        zoom_lerp = 1.0 - math.exp(-self.zoom_speed * dt)
        self.focus += self.wrapped_delta(self.focus, self.target_focus) * focus_lerp

        self.focus.x %= self.world_size.x
        self.focus.y %= self.world_size.y

        self.zoom += (self.target_zoom - self.zoom) * zoom_lerp
        self.shake_time += dt
        self.shake = max(0.0, self.shake - dt * 3.35)
        shake_offset = pygame.Vector2()

        if self.shake > 0.0:
            strength = self.shake * 24.0
            shake_offset.x = (math.sin(self.shake_time * 44.0) + math.sin(self.shake_time * 81.0 + 1.1) * 0.42) * strength
            shake_offset.y = (math.sin(self.shake_time * 52.0 + 2.0) + math.sin(self.shake_time * 93.0) * 0.42) * strength

        self.shake_offset = shake_offset

    def world_to_screen(self, pos, scale):
        delta = self.wrapped_delta(self.focus, pos)
        return self.viewport_size * 0.5 + delta * self.render_scale(scale) + self.shake_offset

    def world_to_screen_unwrapped(self, pos, scale):
        delta = pygame.Vector2(pos) - self.focus
        return self.viewport_size * 0.5 + delta * self.render_scale(scale) + self.shake_offset

    def world_to_screen_raw(self, pos, scale):
        return self.world_to_screen_unwrapped(pos, scale)

    def screen_to_world(self, pos, scale):
        delta = (pygame.Vector2(pos) - self.viewport_size * 0.5 - self.shake_offset) / self.render_scale(scale)
        world = self.focus + delta
        world.x %= self.world_size.x
        world.y %= self.world_size.y
        return world

    def get_view(self, scale):
        render_scale = self.render_scale(scale)
        top_left = self.focus - self.viewport_size / (2.0 * render_scale)
        return top_left, render_scale
