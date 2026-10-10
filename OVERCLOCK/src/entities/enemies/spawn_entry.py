import math
import pygame


def begin_edge_spawn(enemy, target_pos, side, world_size, style, color, duration=0.78):
    target = pygame.Vector2(target_pos)
    world_size = pygame.Vector2(world_size)
    outside = target.copy()
    distance = max(52.0, enemy.hit_radius * 2.3)

    if side == "left":
        outside.x = -distance
    elif side == "right":
        outside.x = world_size.x + distance
    elif side == "top":
        outside.y = -distance
    else:
        outside.y = world_size.y + distance

    enemy.pos = outside.copy()
    enemy.spawn_intro_active = True
    enemy.spawn_intro_side = side
    enemy.spawn_intro_style = style
    enemy.spawn_intro_color = color
    enemy.spawn_intro_duration = duration
    enemy.spawn_intro_timer = 0.0
    enemy.spawn_intro_progress = 0.0
    enemy.spawn_intro_start = outside
    enemy.spawn_intro_target = target
    enemy.spawn_intro_seed = (id(enemy) * 1103515245 + 12345) & 0x7FFFFFFF
    inward = {"left": pygame.Vector2(1, 0), "right": pygame.Vector2(-1, 0), "top": pygame.Vector2(0, 1), "bottom": pygame.Vector2(0, -1)}[side]
    if hasattr(enemy, "angle"):
        enemy.angle = math.atan2(inward.y, inward.x)
    if hasattr(enemy, "vel"):
        enemy.vel = pygame.Vector2()


def update_edge_spawn(enemy, dt):
    if not getattr(enemy, "spawn_intro_active", False):
        return False

    enemy.spawn_intro_timer += dt
    progress = max(0.0, min(1.0, enemy.spawn_intro_timer / enemy.spawn_intro_duration))
    smooth = progress * progress * (3.0 - 2.0 * progress)
    enemy.spawn_intro_progress = progress
    enemy.pos = enemy.spawn_intro_start.lerp(enemy.spawn_intro_target, smooth)

    if hasattr(enemy, "anim_time"):
        enemy.anim_time += dt

    if progress >= 1.0:
        enemy.pos = enemy.spawn_intro_target.copy()
        enemy.spawn_intro_active = False
        enemy.spawn_intro_progress = 1.0
        return False

    return True
