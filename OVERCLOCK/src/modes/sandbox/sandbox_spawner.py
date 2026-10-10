import random
import pygame

from src.entities.enemies.chaser import ChaserEnemy
from src.entities.enemies.hex_splitter import HexSplitterEnemy
from src.entities.enemies.orb import OrbEnemy
from src.entities.enemies.pink_shooter import PinkShooterEnemy
from src.entities.enemies.radiant import RadiantEnemy
from src.entities.enemies.smiler import SmilerEnemy
from src.entities.enemies.spawn_entry import begin_edge_spawn
from src.modes.sandbox import sandbox_config as cfg
from src.settings import CHASER_ACCENT, HEX_ACCENT, ORB_ACCENT, PINK_SHOOTER_ACCENT, RADIANT_ACCENT


class SandboxSpawner:
    def __init__(self, world_size):
        self.world_size = pygame.Vector2(world_size)
        self.chaser_timer = random.uniform(cfg.CHASER_SPAWN_MIN, cfg.CHASER_SPAWN_MAX)
        self.chaser_group = []
        self.chaser_group_locked = False
        self.chaser_group_age = 0.0
        self.chaser_pending_count = 0
        self.chaser_member_timer = 0.0
        self.chaser_member_interval = 0.0
        self.orb_timer = random.uniform(cfg.ORB_SPAWN_MIN, cfg.ORB_SPAWN_MAX)
        self.smiler_timer = random.uniform(cfg.SMILER_SPAWN_MIN, cfg.SMILER_SPAWN_MAX)
        self.radiant_timer = random.uniform(cfg.RADIANT_SPAWN_MIN, cfg.RADIANT_SPAWN_MAX)
        self.hex_timer = random.uniform(cfg.HEX_SPAWN_MIN, cfg.HEX_SPAWN_MAX)
        self.pink_shooter_timer = random.uniform(cfg.PINK_SHOOTER_SPAWN_MIN, cfg.PINK_SHOOTER_SPAWN_MAX)

    def update(self, dt, enemies, player_pos, walls=None):
        self.update_chaser(dt, enemies, player_pos)
        self.update_orb(dt, enemies, player_pos)
        self.update_smilers(dt, enemies, player_pos, walls)
        self.update_radiants(dt, enemies, player_pos)
        self.update_hexes(dt, enemies, player_pos)
        self.update_pink_shooters(dt, enemies, player_pos)

    def update_chaser(self, dt, enemies, player_pos):
        if self.chaser_pending_count > 0:
            self.chaser_member_timer -= dt
            if self.chaser_member_timer <= 0.0:
                self.spawn_chaser_member(enemies, player_pos)
            return

        if self.chaser_group_locked:
            alive_group_members = [enemy for enemy in self.chaser_group if enemy.alive]
            if not alive_group_members:
                self.chaser_group_locked = False
                self.chaser_group = []
                self.chaser_group_age = 0.0
                self.chaser_timer = random.uniform(cfg.CHASER_SPAWN_MIN, cfg.CHASER_SPAWN_MAX)
                return

            self.chaser_group_age += dt
            if self.chaser_group_age < cfg.CHASER_GROUP_MAX_LOCK_TIME:
                return

            self.chaser_group_locked = False
            self.chaser_group_age = 0.0
            self.chaser_timer = random.uniform(cfg.CHASER_SPAWN_MIN, cfg.CHASER_SPAWN_MAX)
            return

        self.chaser_timer -= dt
        if self.chaser_timer > 0.0:
            return

        chaser_count = sum(isinstance(enemy, ChaserEnemy) and enemy.alive for enemy in enemies)
        available_slots = cfg.CHASER_MAX_TOTAL_ENEMIES - chaser_count
        if available_slots < cfg.CHASER_GROUP_MIN:
            self.chaser_timer = 1.0
            return

        group_size = min(random.randint(cfg.CHASER_GROUP_MIN, cfg.CHASER_GROUP_MAX), available_slots)
        self.chaser_group = []
        self.chaser_pending_count = group_size
        self.chaser_member_interval = cfg.CHASER_GROUP_SPAWN_DURATION / max(1, group_size - 1)
        self.chaser_member_timer = 0.0
        self.spawn_chaser_member(enemies, player_pos)

    def spawn_chaser_member(self, enemies, player_pos):
        spawn = self.find_edge_spawn_data(enemies, player_pos, cfg.CHASER_SPAWN_MARGIN, cfg.CHASER_SPAWN_SEPARATION, 24)
        if spawn is None:
            self.chaser_member_timer = 0.35
            return

        target, side = spawn
        enemy = ChaserEnemy(target, self.world_size)
        begin_edge_spawn(enemy, target, side, self.world_size, "chaser", CHASER_ACCENT, 0.64)
        enemies.append(enemy)
        self.chaser_group.append(enemy)
        self.chaser_pending_count -= 1

        if self.chaser_pending_count > 0:
            self.chaser_member_timer = self.chaser_member_interval
        else:
            self.chaser_member_timer = 0.0
            self.chaser_group_locked = True
            self.chaser_group_age = 0.0

    def update_orb(self, dt, enemies, player_pos):
        orb_count = sum(isinstance(enemy, OrbEnemy) and enemy.alive for enemy in enemies)
        if orb_count >= cfg.ORB_MAX_ALIVE:
            return

        self.orb_timer -= dt
        if self.orb_timer > 0.0:
            return

        spawn = self.find_edge_spawn_data(enemies, player_pos, cfg.ORB_SPAWN_MARGIN, cfg.ORB_SPAWN_SEPARATION, 24)
        if spawn is None:
            self.orb_timer = 2.0
            return

        target, side = spawn
        enemy = OrbEnemy(target, player_pos, self.world_size)
        begin_edge_spawn(enemy, target, side, self.world_size, "orb", ORB_ACCENT, 0.82)
        enemies.append(enemy)
        self.orb_timer = random.uniform(cfg.ORB_SPAWN_MIN, cfg.ORB_SPAWN_MAX)

    def update_smilers(self, dt, enemies, player_pos, walls=None):
        smiler_count = sum(isinstance(enemy, SmilerEnemy) and enemy.alive for enemy in enemies)
        if smiler_count >= cfg.SMILER_MAX_ALIVE:
            return

        self.smiler_timer -= dt
        if self.smiler_timer > 0.0:
            return

        group_size = min(random.randint(cfg.SMILER_GROUP_MIN, cfg.SMILER_GROUP_MAX), cfg.SMILER_MAX_ALIVE - smiler_count)
        spawned_positions = []
        spawned = 0

        for _ in range(group_size):
            position = self.find_smiler_spawn(enemies, spawned_positions, player_pos, walls)
            if position is None:
                continue
            enemies.append(SmilerEnemy(position, self.world_size))
            spawned_positions.append(position)
            spawned += 1

        self.smiler_timer = random.uniform(cfg.SMILER_SPAWN_MIN, cfg.SMILER_SPAWN_MAX) if spawned > 0 else 2.0

    def find_smiler_spawn(self, enemies, spawned_positions, player_pos, walls):
        margin = 100.0
        for _ in range(80):
            position = pygame.Vector2(random.uniform(margin, self.world_size.x - margin), random.uniform(margin, self.world_size.y - margin))
            if self.wrapped_distance(position, player_pos) < cfg.SMILER_SPAWN_PLAYER_CLEARANCE:
                continue
            if any(self.wrapped_distance(position, other_position) < cfg.SMILER_SPAWN_SIBLING_CLEARANCE for other_position in spawned_positions):
                continue

            blocked = False
            for enemy in enemies:
                if not enemy.alive:
                    continue
                enemy_pos = getattr(enemy, "spawn_intro_target", enemy.pos) if getattr(enemy, "spawn_intro_active", False) else enemy.pos
                distance = self.wrapped_distance(position, enemy_pos)
                clearance = cfg.SMILER_SPAWN_SIBLING_CLEARANCE if isinstance(enemy, SmilerEnemy) else cfg.SMILER_SPAWN_OTHER_CLEARANCE
                if distance < clearance:
                    blocked = True
                    break
            if blocked:
                continue

            if walls is not None:
                for wall in walls.walls:
                    if walls.point_segment_distance(position, wall["a"], wall["b"]) < cfg.SMILER_SPAWN_WALL_CLEARANCE:
                        blocked = True
                        break
            if not blocked:
                return position

        return None

    def update_radiants(self, dt, enemies, player_pos):
        radiant_count = sum(isinstance(enemy, RadiantEnemy) and enemy.alive for enemy in enemies)
        if radiant_count >= cfg.RADIANT_MAX_ALIVE:
            return

        self.radiant_timer -= dt
        if self.radiant_timer > 0.0:
            return

        group_size = min(random.randint(cfg.RADIANT_GROUP_MIN, cfg.RADIANT_GROUP_MAX), cfg.RADIANT_MAX_ALIVE - radiant_count)
        base_target, side = self.random_edge_target(cfg.RADIANT_SPAWN_MARGIN)
        spawned = 0

        for index in range(group_size):
            offset = (index - (group_size - 1) * 0.5) * cfg.RADIANT_GROUP_SPACING
            target = self.offset_edge_target(base_target, side, offset, cfg.RADIANT_SPAWN_MARGIN)
            if not self.is_valid_position(target, enemies, player_pos, cfg.RADIANT_SPAWN_SEPARATION):
                spawn = self.find_edge_spawn_data(enemies, player_pos, cfg.RADIANT_SPAWN_MARGIN, cfg.RADIANT_SPAWN_SEPARATION, 20)
                if spawn is None:
                    continue
                target, enemy_side = spawn
            else:
                enemy_side = side

            enemy = RadiantEnemy(target, self.world_size)
            begin_edge_spawn(enemy, target, enemy_side, self.world_size, "radiant", RADIANT_ACCENT, 0.92)
            enemies.append(enemy)
            spawned += 1

        self.radiant_timer = random.uniform(cfg.RADIANT_SPAWN_MIN, cfg.RADIANT_SPAWN_MAX) if spawned > 0 else 2.0

    def update_hexes(self, dt, enemies, player_pos):
        hex_count = sum(isinstance(enemy, HexSplitterEnemy) and enemy.alive for enemy in enemies)
        if hex_count >= cfg.HEX_MAX_ALIVE:
            return

        self.hex_timer -= dt
        if self.hex_timer > 0.0:
            return

        spawn = self.find_edge_spawn_data(enemies, player_pos, cfg.HEX_SPAWN_MARGIN, cfg.HEX_SPAWN_SEPARATION, 30)
        if spawn is None:
            self.hex_timer = 2.0
            return

        target, side = spawn
        enemy = HexSplitterEnemy(target, self.world_size)
        begin_edge_spawn(enemy, target, side, self.world_size, "hex", HEX_ACCENT, 1.0)
        enemies.append(enemy)
        self.hex_timer = random.uniform(cfg.HEX_SPAWN_MIN, cfg.HEX_SPAWN_MAX)

    def update_pink_shooters(self, dt, enemies, player_pos):
        alive_count = sum(isinstance(enemy, PinkShooterEnemy) and enemy.alive for enemy in enemies)
        if alive_count >= cfg.PINK_SHOOTER_MAX_ALIVE:
            return

        self.pink_shooter_timer -= dt
        if self.pink_shooter_timer > 0.0:
            return

        group_size = min(random.randint(cfg.PINK_SHOOTER_GROUP_MIN, cfg.PINK_SHOOTER_GROUP_MAX), cfg.PINK_SHOOTER_MAX_ALIVE - alive_count)
        base_target, side = self.random_edge_target(cfg.PINK_SHOOTER_SPAWN_MARGIN)
        spawned = 0

        for index in range(group_size):
            offset = (index - (group_size - 1) * 0.5) * cfg.PINK_SHOOTER_GROUP_SPACING
            target = self.offset_edge_target(base_target, side, offset, cfg.PINK_SHOOTER_SPAWN_MARGIN)
            if not self.is_valid_position(target, enemies, player_pos, cfg.PINK_SHOOTER_SPAWN_SEPARATION):
                spawn = self.find_edge_spawn_data(enemies, player_pos, cfg.PINK_SHOOTER_SPAWN_MARGIN, cfg.PINK_SHOOTER_SPAWN_SEPARATION, 28)
                if spawn is None:
                    continue
                target, enemy_side = spawn
            else:
                enemy_side = side

            enemy = PinkShooterEnemy(target, self.world_size)
            begin_edge_spawn(enemy, target, enemy_side, self.world_size, "pink", PINK_SHOOTER_ACCENT, 0.74)
            enemies.append(enemy)
            spawned += 1

        self.pink_shooter_timer = random.uniform(cfg.PINK_SHOOTER_SPAWN_MIN, cfg.PINK_SHOOTER_SPAWN_MAX) if spawned > 0 else 2.0

    def find_edge_spawn_data(self, enemies, player_pos, margin, separation, attempts):
        for _ in range(attempts):
            target, side = self.random_edge_target(margin)
            if self.is_valid_position(target, enemies, player_pos, separation):
                return target, side
        return None

    def random_edge_target(self, margin, side=None):
        width, height = self.world_size
        side = side or random.choice(("left", "right", "top", "bottom"))
        if side == "left":
            return pygame.Vector2(margin, random.uniform(margin, height - margin)), side
        if side == "right":
            return pygame.Vector2(width - margin, random.uniform(margin, height - margin)), side
        if side == "top":
            return pygame.Vector2(random.uniform(margin, width - margin), margin), side
        return pygame.Vector2(random.uniform(margin, width - margin), height - margin), side

    def offset_edge_target(self, base_target, side, offset, margin):
        target = base_target.copy()
        if side in ("left", "right"):
            target.y = max(margin, min(self.world_size.y - margin, target.y + offset))
        else:
            target.x = max(margin, min(self.world_size.x - margin, target.x + offset))
        return target

    def is_valid_position(self, position, enemies, player_pos, separation):
        if self.wrapped_distance(position, player_pos) < separation * 1.5:
            return False
        for enemy in enemies:
            if not enemy.alive:
                continue
            enemy_pos = getattr(enemy, "spawn_intro_target", enemy.pos) if getattr(enemy, "spawn_intro_active", False) else enemy.pos
            if self.wrapped_distance(position, enemy_pos) < separation:
                return False
        return True

    def wrapped_distance(self, a, b):
        delta = pygame.Vector2(b) - pygame.Vector2(a)
        if abs(delta.x) > self.world_size.x * 0.5:
            delta.x = self.world_size.x - abs(delta.x)
        if abs(delta.y) > self.world_size.y * 0.5:
            delta.y = self.world_size.y - abs(delta.y)
        return delta.length()
