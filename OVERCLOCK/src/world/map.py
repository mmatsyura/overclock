import math
import pygame
from src.settings import *


class World:
    def __init__(self, size):
        self.size = pygame.Vector2(size)

    def draw(self, screen, fx, camera, scale, shockwave=None):
        self.draw_grid(screen, camera, scale)

    def draw_grid(self, screen, camera, scale):
        screen.fill(BG)

        sw, sh = screen.get_size()
        view_pos, render_scale = camera.get_view(scale)

        left = view_pos.x
        top = view_pos.y
        right = left + sw / render_scale
        bottom = top + sh / render_scale

        offset_x = camera.shake_offset.x
        offset_y = camera.shake_offset.y

        major_size = GRID_SIZE * 5

        x = math.floor(left / major_size) * major_size

        while x <= right + major_size:
            sx = int((x - left) * render_scale + offset_x)
            pygame.draw.line(screen, GRID_MAJOR, (sx, -20), (sx, sh + 20), max(1, int(render_scale)))
            x += major_size

        y = math.floor(top / major_size) * major_size

        while y <= bottom + major_size:
            sy = int((y - top) * render_scale + offset_y)
            pygame.draw.line(screen, GRID_MAJOR, (-20, sy), (sw + 20, sy), max(1, int(render_scale)))
            y += major_size