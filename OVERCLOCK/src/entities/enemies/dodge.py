import random
import pygame

DODGE_CHANCE = 0.30


def init_dodge_state(enemy):
    enemy.dodge_timer = 0.0
    enemy.dodge_cooldown = random.uniform(0.15, 0.45)
    enemy.dodge_direction = pygame.Vector2()
    enemy.dodge_tested_projectiles = set()


def get_dodge_vector(enemy, dt, projectiles, detect_radius=190.0, lookahead=0.42):
    if not projectiles:
        enemy.dodge_timer = max(0.0, enemy.dodge_timer - dt)
        enemy.dodge_cooldown = max(0.0, enemy.dodge_cooldown - dt)
        enemy.dodge_tested_projectiles.clear()
        return enemy.dodge_direction if enemy.dodge_timer > 0.0 else pygame.Vector2()

    alive_ids = {id(projectile) for projectile in projectiles if projectile.alive}
    enemy.dodge_tested_projectiles.intersection_update(alive_ids)
    enemy.dodge_timer = max(0.0, enemy.dodge_timer - dt)
    enemy.dodge_cooldown = max(0.0, enemy.dodge_cooldown - dt)

    if enemy.dodge_timer > 0.0:
        return enemy.dodge_direction

    if enemy.dodge_cooldown > 0.0:
        return pygame.Vector2()

    best = None

    for projectile in projectiles:
        if not projectile.alive:
            continue

        projectile_id = id(projectile)
        if projectile_id in enemy.dodge_tested_projectiles:
            continue

        relative_pos = projectile.pos - enemy.pos
        distance_sq = relative_pos.length_squared()
        if distance_sq > detect_radius * detect_radius:
            continue

        relative_vel = projectile.vel - enemy.vel
        speed_sq = relative_vel.length_squared()
        if speed_sq <= 1.0:
            continue

        time_to_closest = -relative_pos.dot(relative_vel) / speed_sq
        if time_to_closest < 0.0 or time_to_closest > lookahead:
            continue

        closest = relative_pos + relative_vel * time_to_closest
        safe_radius = enemy.hit_radius + 24.0
        if closest.length_squared() > safe_radius * safe_radius:
            continue

        score = time_to_closest + distance_sq / max(1.0, detect_radius * detect_radius) * 0.12
        if best is None or score < best[0]:
            best = (score, projectile)

    if best is None:
        return pygame.Vector2()

    projectile = best[1]
    projectile_id = id(projectile)
    enemy.dodge_tested_projectiles.add(projectile_id)
    enemy.dodge_cooldown = random.uniform(0.42, 0.72)

    if random.random() >= DODGE_CHANCE:
        return pygame.Vector2()

    bullet_dir = pygame.Vector2(projectile.vel)
    if bullet_dir.length_squared() <= 0.001:
        return pygame.Vector2()

    bullet_dir = bullet_dir.normalize()
    side = pygame.Vector2(-bullet_dir.y, bullet_dir.x)
    to_enemy = enemy.pos - projectile.pos
    sign = 1.0 if side.dot(to_enemy) >= 0.0 else -1.0

    if random.random() < 0.22:
        sign *= -1.0

    enemy.dodge_direction = side * sign
    enemy.dodge_timer = random.uniform(0.34, 0.58)
    return enemy.dodge_direction
