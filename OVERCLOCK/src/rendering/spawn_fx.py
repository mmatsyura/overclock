import math
import random
import pygame


def _rgba(color, alpha):
    return color[0], color[1], color[2], max(0, min(255, int(alpha)))


def draw_enemy_spawn_fx(fx, enemy, camera, scale):
    if not getattr(enemy, "spawn_intro_active", False):
        return

    progress = getattr(enemy, "spawn_intro_progress", 0.0)
    target = getattr(enemy, "spawn_intro_target", enemy.pos)
    side = getattr(enemy, "spawn_intro_side", "left")
    style = getattr(enemy, "spawn_intro_style", "slash")
    color = getattr(enemy, "spawn_intro_color", (255, 255, 255))
    center = camera.world_to_screen_raw(target, scale)
    draw_scale = camera.render_scale(scale)
    fade = math.sin(max(0.0, min(1.0, progress)) * math.pi) ** 0.72
    inward = {"left": pygame.Vector2(1, 0), "right": pygame.Vector2(-1, 0), "top": pygame.Vector2(0, 1), "bottom": pygame.Vector2(0, -1)}[side]
    tangent = pygame.Vector2(-inward.y, inward.x)
    if side == "left":
        border = pygame.Vector2(0, center.y)
    elif side == "right":
        border = pygame.Vector2(camera.viewport_size.x - 1, center.y)
    elif side == "top":
        border = pygame.Vector2(center.x, 0)
    else:
        border = pygame.Vector2(center.x, camera.viewport_size.y - 1)

    if style == "chaser":
        length = 42.0 * draw_scale
        for offset, alpha, width in ((0, 180, 2), (9, 70, 5), (-9, 70, 5)):
            a = border + tangent * (-length + offset) - inward * 4 * draw_scale
            b = border + tangent * (length + offset) + inward * 18 * draw_scale
            pygame.draw.line(fx, _rgba(color, alpha * fade), a, b, max(1, int(width * draw_scale)))
    elif style == "orb":
        radius = (12.0 + 28.0 * progress) * draw_scale
        pygame.draw.circle(fx, _rgba(color, 38 * fade), border, max(2, int(radius * 1.35)), max(1, int(5 * draw_scale)))
        pygame.draw.circle(fx, _rgba(color, 155 * fade), border, max(2, int(radius)), max(1, int(2 * draw_scale)))
        for i in range(6):
            angle = i * math.tau / 6.0 + progress * 2.0
            start = border + pygame.Vector2(math.cos(angle), math.sin(angle)) * radius * 0.75
            end = border + pygame.Vector2(math.cos(angle), math.sin(angle)) * radius * 1.28
            pygame.draw.line(fx, _rgba(color, 105 * fade), start, end, max(1, int(2 * draw_scale)))
    elif style == "radiant":
        width = 72.0 * draw_scale
        for i in range(5):
            t = (i - 2) / 2.0
            pos = border + tangent * width * t * 0.48
            a = pos - tangent * 7 * draw_scale
            b = pos + tangent * 7 * draw_scale + inward * (15 + 7 * abs(t)) * draw_scale
            pygame.draw.line(fx, _rgba(color, (65 + 105 * (1.0 - abs(t))) * fade), a, b, max(1, int(2 * draw_scale)))
    elif style == "hex":
        radius = 24.0 * draw_scale
        points = []
        for i in range(6):
            angle = progress * 1.5 + i * math.tau / 6.0
            points.append(border + pygame.Vector2(math.cos(angle), math.sin(angle)) * radius)
        pygame.draw.lines(fx, _rgba(color, 170 * fade), True, points, max(1, int(2 * draw_scale)))
        pygame.draw.lines(fx, _rgba(color, 40 * fade), True, [border + (p - border) * 1.45 for p in points], max(1, int(5 * draw_scale)))
    elif style == "pink":
        wing = 34.0 * draw_scale
        nose = border + inward * 24.0 * draw_scale
        left = border + tangent * wing - inward * 6.0 * draw_scale
        right = border - tangent * wing - inward * 6.0 * draw_scale
        pygame.draw.line(fx, _rgba(color, 175 * fade), left, nose, max(1, int(2 * draw_scale)))
        pygame.draw.line(fx, _rgba(color, 175 * fade), right, nose, max(1, int(2 * draw_scale)))
        pygame.draw.line(fx, _rgba(color, 42 * fade), left - tangent * 5, nose + inward * 6, max(1, int(6 * draw_scale)))
        pygame.draw.line(fx, _rgba(color, 42 * fade), right + tangent * 5, nose + inward * 6, max(1, int(6 * draw_scale)))

    rng = random.Random(getattr(enemy, "spawn_intro_seed", 0))
    for _ in range(7):
        offset = tangent * rng.uniform(-38.0, 38.0) * draw_scale
        depth = inward * rng.uniform(2.0, 24.0) * draw_scale * (0.4 + progress)
        pos = border + offset + depth
        pygame.draw.circle(fx, _rgba(color, rng.uniform(45, 115) * fade), (int(pos.x), int(pos.y)), max(1, int(rng.uniform(1.0, 2.1) * draw_scale)))
