import pygame

from src.settings import PLAYER_ACCENT


def draw_cursor(screen, pos, scale):
    x, y = int(pos[0]), int(pos[1])
    radius = max(4, int(7 * scale))
    gap = max(4, int(6 * scale))
    length = max(4, int(5 * scale))
    width = max(1, int(1.5 * scale))

    pygame.draw.circle(screen, (38, 83, 94), (x, y), radius, width)
    pygame.draw.line(screen, PLAYER_ACCENT, (x - gap - length, y), (x - gap, y), width)
    pygame.draw.line(screen, PLAYER_ACCENT, (x + gap, y), (x + gap + length, y), width)
    pygame.draw.line(screen, PLAYER_ACCENT, (x, y - gap - length), (x, y - gap), width)
    pygame.draw.line(screen, PLAYER_ACCENT, (x, y + gap), (x, y + gap + length), width)