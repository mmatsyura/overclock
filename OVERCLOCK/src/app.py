import pygame
import random
import math
import sys

from src.core.camera import Camera
from src.core.time_controller import TimeController
from src.entities.player import Player
from src.entities.enemies.spawn_entry import update_edge_spawn
from src.rendering.border_fx import BorderFX
from src.rendering.cursor import draw_cursor
from src.rendering.enemy_death_fx import EnemyDeathFX
from src.rendering.player_death_fx import PlayerDeathFX
from src.rendering.spawn_fx import draw_enemy_spawn_fx
from src.rendering.hud import HUD
from src.modes.factory import create_mode
from src.world.walls import WallField
from src.settings import *
from src.ui.menu import MainMenu
from src.world.map import World


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("OVERCLOCK")
        desktop_size = pygame.display.get_desktop_sizes()[0]
        self.screen = pygame.display.set_mode(desktop_size, pygame.NOFRAME | pygame.DOUBLEBUF)
        self.clock = pygame.time.Clock()
        self.screen_size = self.screen.get_size()
        self.scale = render_scale(self.screen_size)
        self.hud = HUD(self.scale)
        self.world_size = pygame.Vector2(self.screen_size) / self.scale
        self.fx = pygame.Surface(self.screen_size, pygame.SRCALPHA).convert_alpha()
        self.running = True
        self.state = "menu"
        self.current_mode = None
        self.current_level = None
        self.mode_controller = None
        self.menu = MainMenu(self.screen_size, self.scale)
        self.reset_gameplay()
        self.menu.activate_cursor()

    def reset_gameplay(self):
        self.world = World(self.world_size)
        self.player = Player(self.world_size * 0.5)
        self.walls = WallField(self.world_size, auto_generate=False)
        self.camera = Camera(self.screen_size, self.world_size)
        self.time_controller = TimeController()
        self.border_fx = BorderFX()
        self.enemy_death_fx = EnemyDeathFX()
        self.player_death_fx = PlayerDeathFX()

        self.enemies = []
        self.projectiles = []
        self.enemy_projectiles = []
        self.player_alive = True
        self.enemy_roam_targets = {}
        self.enemy_roam_timers = {}

        self.player_max_hp = PLAYER_MAX_HP
        self.player_hp = float(PLAYER_MAX_HP)

        self.player_time_since_damage = 999.0
        self.player_regen_timer = 0.0
        self.damage_vignette = 0.0
        self.damage_vignette_surface = self.build_damage_vignette()

        self.fx.fill((0, 0, 0, 0))

        self.hud.set_score(0)
        self.hud.set_health(self.player_hp, self.player_max_hp, instant=True)
        self.hud.additions.clear()
        self.hud.pulse = 0.0

    def run(self):
        while self.running:
            real_dt = min(self.clock.tick(FPS) / 1000.0, 1.0 / 30.0)
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT: self.running = False
            if not self.running: break
            if self.state == "menu":
                action = self.menu.update(real_dt, events)
                self.handle_menu_action(action)
                if self.state == "menu":
                    self.menu.draw(self.screen)
                    pygame.display.flip()
                continue
            for event in events:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.state = "menu"
                    self.menu.reset()
                    self.menu.activate_cursor()
                    break
            if self.state != "playing": continue
            game_dt = self.time_controller.update(real_dt)
            self.update(game_dt, real_dt)
            self.draw()
        self.close()

    def handle_menu_action(self, action):
        if action is None: return
        action_type, mode, level = action
        if action_type == "quit":
            self.running = False
            return
        if action_type == "start": self.start_game(mode, level)

    def start_game(self, mode, level=None):
        self.current_mode = mode
        self.current_level = level
        self.mode_controller = create_mode(mode, self.world_size, level)
        self.reset_gameplay()
        self.mode_controller.on_start(self)
        self.menu.deactivate_cursor()
        self.state = "playing"

    def update(self, dt, real_dt):
        mouse_screen = pygame.mouse.get_pos()
        mouse_world = self.camera.screen_to_world(mouse_screen, self.scale)
        mouse_buttons = pygame.mouse.get_pressed(3)

        thrusting = mouse_buttons[0]
        shooting = mouse_buttons[2]

        wrap_event = None
        self.update_damage_vignette(real_dt)

        if self.player_alive:
            self.update_player_health(real_dt)
            wrap_event = self.player.update(dt, mouse_world, thrusting, self.world_size)
            wall_impact = self.walls.resolve_player(self.player, PLAYER_HIT_RADIUS + 6.0)

            if wall_impact > 70.0:
                self.camera.add_shake(min(0.38, 0.05 + wall_impact / 1100.0))

        if self.mode_controller is not None:
            self.mode_controller.update_interface(real_dt, self)
            self.mode_controller.update(dt, self)

        self.update_enemies(dt)
        self.resolve_radiant_enemy_collisions()
        self.resolve_hex_collisions()
        self.resolve_enemy_hazards()

        if self.player_alive:
            self.check_player_collision()

        projectile = None

        if self.player_alive:
            projectile = self.player.update_weapon(dt, shooting)

        if projectile:
            self.projectiles.append(projectile)

        self.update_projectiles(dt)
        self.update_enemy_projectiles(dt)

        self.projectiles = [projectile for projectile in self.projectiles if projectile.alive]
        self.enemy_projectiles = [projectile for projectile in self.enemy_projectiles if projectile.alive]
        self.enemies = [enemy for enemy in self.enemies if enemy.alive]
        self.enemy_death_fx.update(dt, self.world_size, self.walls)

        if self.player_death_fx.is_active():
            death_fx_dt = max(dt, real_dt * 0.32)
            self.player_death_fx.update(death_fx_dt, self.world_size, self.walls)

        if not self.player_alive and self.time_controller.mode == "player_death" and not self.player_death_fx.keeps_death_slowmo():
            self.time_controller.finish_player_death()

        if wrap_event:
            self.border_fx.trigger(*wrap_event)

        self.border_fx.update(dt)
        self.camera.update(real_dt)
        self.hud.update(real_dt)

    def get_enemy_roam_target(self, enemy, dt):
        key = id(enemy)

        if key not in self.enemy_roam_targets:
            self.enemy_roam_targets[key] = pygame.Vector2(random.uniform(0.0, self.world_size.x), random.uniform(0.0, self.world_size.y))
            self.enemy_roam_timers[key] = random.uniform(1.8, 5.5)

        self.enemy_roam_timers[key] -= dt

        target = self.enemy_roam_targets[key]
        delta = self.wrapped_delta(enemy.pos, target)

        if self.enemy_roam_timers[key] <= 0.0 or delta.length_squared() < 70.0 * 70.0:
            margin = 80.0

            self.enemy_roam_targets[key] = pygame.Vector2(random.uniform(margin, max(margin, self.world_size.x - margin)), random.uniform(margin, max(margin, self.world_size.y - margin)))
            self.enemy_roam_timers[key] = random.uniform(2.2, 6.5)

        return self.enemy_roam_targets[key]

    def cleanup_enemy_roam_targets(self):
        alive_ids = {id(enemy) for enemy in self.enemies if enemy.alive}

        for key in list(self.enemy_roam_targets):
            if key not in alive_ids:
                self.enemy_roam_targets.pop(key, None)
                self.enemy_roam_timers.pop(key, None)

    def get_enemy_roam_target(self, enemy, dt):
        key = id(enemy)

        if key not in self.enemy_roam_targets:
            self.enemy_roam_targets[key] = pygame.Vector2(random.uniform(60.0, self.world_size.x - 60.0), random.uniform(60.0, self.world_size.y - 60.0))
            self.enemy_roam_timers[key] = random.uniform(2.0, 5.5)

        self.enemy_roam_timers[key] -= dt

        target = self.enemy_roam_targets[key]
        delta = self.wrapped_delta(enemy.pos, target)

        if self.enemy_roam_timers[key] <= 0.0 or delta.length_squared() < 80.0 * 80.0:
            self.enemy_roam_targets[key] = pygame.Vector2(random.uniform(60.0, self.world_size.x - 60.0), random.uniform(60.0, self.world_size.y - 60.0))
            self.enemy_roam_timers[key] = random.uniform(2.0, 5.5)

        return self.enemy_roam_targets[key]

    def cleanup_enemy_roam_targets(self):
        alive_ids = {id(enemy) for enemy in self.enemies if enemy.alive}

        for key in list(self.enemy_roam_targets):
            if key not in alive_ids:
                self.enemy_roam_targets.pop(key, None)
                self.enemy_roam_timers.pop(key, None)

    def update_enemies(self, dt):
        for enemy in self.enemies:
            if not enemy.alive:
                continue

            if self.player_alive:
                if update_edge_spawn(enemy, dt):
                    continue

                target = self.player.pos
            else:
                target = self.get_enemy_roam_target(enemy, dt)

            enemy_wrap = enemy.update(dt, target, self.world_size, self.enemies, self.walls, self.projectiles)
            self.walls.resolve_enemy(enemy)

            if enemy_wrap:
                self.border_fx.trigger_enemy_wrap(*enemy_wrap)

            consume_projectiles = getattr(enemy, "consume_projectiles", None)

            if consume_projectiles is not None:
                self.enemy_projectiles.extend(consume_projectiles())

        if not self.player_alive:
            self.cleanup_enemy_roam_targets()

    def update_projectiles(self, dt):
        if dt <= 0: return

        for projectile in self.projectiles:
            border_hit = projectile.update(dt, self.world_size, self.walls)

            if border_hit:
                self.border_fx.trigger_bullet_hit(*border_hit)
                self.camera.add_shake(0.12)

            if not projectile.alive: continue

            for enemy in self.enemies:
                if not enemy.alive or getattr(enemy, "spawn_intro_active", False):
                    continue

                radius = BULLET_HIT_RADIUS + enemy.hit_radius

                if not projectile.collides_with(enemy.pos, radius):
                    continue

                projectile.alive = False

                register_hit = getattr(enemy, "register_hit", None)
                if register_hit is not None:
                    register_hit(projectile.vel)

                killed = enemy.take_damage(1)

                consume_children = getattr(enemy, "consume_children", None)
                if consume_children is not None:
                    spawned_children = consume_children()

                    if spawned_children:
                        self.enemies.extend(spawned_children)
                        self.camera.add_shake(0.20)

                if getattr(enemy, "is_radiant_enemy", False) and not killed:
                    self.camera.add_shake(0.24)

                if killed:
                    self.enemy_death_fx.spawn(enemy.pos, enemy.vel, getattr(enemy, "death_color", (255, 65, 65)), getattr(enemy, "death_core", (255, 175, 175)))
                    self.camera.add_shake(0.72)
                    self.time_controller.trigger_kill()
                    self.hud.add_score(getattr(enemy, "score_value", 0))

                break

    def update_enemy_projectiles(self, dt):
        if dt <= 0:
            return

        for projectile in self.enemy_projectiles:
            projectile.update(dt, self.world_size, self.walls)

            if not self.player_alive or not projectile.alive or not projectile.active:
                continue

            if projectile.wrap:
                delta = self.wrapped_delta(projectile.pos, self.player.pos)
            else:
                delta = self.player.pos - projectile.pos

            collision_radius = PLAYER_HIT_RADIUS + projectile.radius

            if delta.length_squared() > collision_radius * collision_radius:
                continue

            incoming_velocity = projectile.vel.copy()
            hit_color = projectile.color

            projectile.explode()
            self.damage_player(projectile.damage, incoming_velocity, hit_color)

    def update_damage_vignette(self, dt):
        if self.damage_vignette <= 0.0:
            return

        self.damage_vignette = max(0.0, self.damage_vignette - dt * 1.45)

    def update_player_health(self, dt):
        if not self.player_alive:
            return

        self.player_time_since_damage += dt

        if self.player_time_since_damage < PLAYER_REGEN_DELAY:
            self.player_regen_timer = 0.0
            return

        if self.player_hp >= self.player_max_hp:
            self.player_regen_timer = 0.0
            return

        self.player_regen_timer += dt

        while self.player_regen_timer >= PLAYER_REGEN_INTERVAL:
            self.player_regen_timer -= PLAYER_REGEN_INTERVAL
            self.player_hp = min(self.player_max_hp, self.player_hp + PLAYER_REGEN_AMOUNT)
            self.hud.set_health(self.player_hp, self.player_max_hp)

    def damage_player(self, damage, incoming_velocity=None, hit_color=None):
        if not self.player_alive:
            return

        damage = max(0, int(damage))

        if damage <= 0:
            return

        self.player_hp = max(0.0, self.player_hp - damage)
        self.player_time_since_damage = 0.0

        self.hud.set_health(self.player_hp, self.player_max_hp, hit=True)

        if incoming_velocity is not None:
            self.player.register_damage_hit(incoming_velocity, hit_color)

        self.damage_vignette = max(self.damage_vignette, min(0.82, 0.34 + damage / 55.0))
        self.camera.add_shake(0.32 + damage * 0.012)

        if self.player_hp <= 0.0:
            self.kill_player()

    def wrapped_delta(self, source, target):
        delta = pygame.Vector2(target) - pygame.Vector2(source)

        if delta.x > self.world_size.x * 0.5: delta.x -= self.world_size.x
        elif delta.x < -self.world_size.x * 0.5: delta.x += self.world_size.x
        if delta.y > self.world_size.y * 0.5: delta.y -= self.world_size.y
        elif delta.y < -self.world_size.y * 0.5: delta.y += self.world_size.y

        return delta

    def wrap_position(self, pos):
        pos.x %= self.world_size.x
        pos.y %= self.world_size.y

    def resolve_radiant_enemy_collisions(self):
        for _ in range(2):
            for i in range(len(self.enemies)):
                a = self.enemies[i]

                if not a.alive or getattr(a, "spawn_intro_active", False):
                    continue

                for j in range(i + 1, len(self.enemies)):
                    b = self.enemies[j]

                    if not b.alive or getattr(b, "spawn_intro_active", False):
                        continue

                    a_radiant = getattr(a, "is_radiant_enemy", False)
                    b_radiant = getattr(b, "is_radiant_enemy", False)

                    if not a_radiant and not b_radiant:
                        continue

                    delta = self.wrapped_delta(a.pos, b.pos)
                    min_distance = a.hit_radius + b.hit_radius
                    distance_sq = delta.length_squared()

                    if distance_sq >= min_distance * min_distance:
                        continue

                    if distance_sq > 0.001:
                        distance = math.sqrt(distance_sq)
                        normal = delta / distance
                    else:
                        distance = 0.0
                        normal = pygame.Vector2(1.0, 0.0)

                    penetration = min_distance - distance

                    if a_radiant and b_radiant:
                        a_share = 0.5
                        b_share = 0.5
                    elif a_radiant:
                        a_share = 0.32
                        b_share = 0.68
                    else:
                        a_share = 0.68
                        b_share = 0.32

                    a.pos -= normal * penetration * a_share
                    b.pos += normal * penetration * b_share

                    self.wrap_position(a.pos)
                    self.wrap_position(b.pos)

                    relative_velocity = b.vel - a.vel
                    closing_speed = -relative_velocity.dot(normal)

                    if closing_speed > 0.0:
                        impulse = normal * (closing_speed * 0.58 + 18.0)
                        a.vel -= impulse * a_share
                        b.vel += impulse * b_share

            for enemy in self.enemies:
                if enemy.alive and not getattr(enemy, "spawn_intro_active", False) and getattr(enemy, "is_radiant_enemy", False):
                    self.walls.resolve_enemy(enemy)

    def resolve_hex_collisions(self):
        hexes = [enemy for enemy in self.enemies if enemy.alive and not getattr(enemy, "spawn_intro_active", False) and getattr(enemy, "is_hex_splitter", False)]

        for i in range(len(hexes)):
            a = hexes[i]

            if not getattr(a, "split_collision_ready", True):
                continue

            for j in range(i + 1, len(hexes)):
                b = hexes[j]

                if not getattr(b, "split_collision_ready", True):
                    continue

                delta = self.wrapped_delta(a.pos, b.pos)
                min_distance = a.hit_radius + b.hit_radius
                distance_sq = delta.length_squared()

                if distance_sq >= min_distance * min_distance:
                    continue

                if distance_sq > 0.001:
                    distance = math.sqrt(distance_sq)
                    normal = delta / distance
                else:
                    distance = 0.0
                    normal = pygame.Vector2(1.0, 0.0)

                penetration = min_distance - distance

                a.pos -= normal * penetration * 0.5
                b.pos += normal * penetration * 0.5

                self.wrap_position(a.pos)
                self.wrap_position(b.pos)

                relative_velocity = b.vel - a.vel
                closing_speed = -relative_velocity.dot(normal)

                if closing_speed > 0.0:
                    impulse = normal * (closing_speed * 0.42 + 8.0)

                    a.vel -= impulse * 0.5
                    b.vel += impulse * 0.5

    def resolve_enemy_hazards(self):
        hazards = [enemy for enemy in self.enemies if enemy.alive and not getattr(enemy, "spawn_intro_active", False) and getattr(enemy, "kills_enemies_on_contact", False)]

        if not hazards:
            return

        killed_ids = set()

        for hazard in hazards:
            if not hazard.alive:
                continue

            hazard_points_method = getattr(hazard, "get_hazard_points", None)

            if hazard_points_method is None:
                hazard_points = [(hazard.pos, hazard.hit_radius)]
            else:
                hazard_points = hazard_points_method()

            for enemy in self.enemies:
                if enemy is hazard or not enemy.alive or getattr(enemy, "spawn_intro_active", False):
                    continue

                if id(enemy) in killed_ids:
                    continue

                hazard_family = getattr(hazard, "hazard_family", None)
                enemy_family = getattr(enemy, "hazard_family", None)

                if hazard_family is not None and hazard_family == enemy_family:
                    continue

                collided = False
                hit_orb_index = None

                for hazard_data in hazard_points:
                    hazard_pos = hazard_data[0]
                    hazard_radius = hazard_data[1]
                    orb_index = hazard_data[2] if len(hazard_data) > 2 else None
                    delta = self.wrapped_delta(hazard_pos, enemy.pos)
                    collision_radius = hazard_radius + enemy.hit_radius

                    if delta.length_squared() <= collision_radius * collision_radius:
                        collided = True
                        hit_orb_index = orb_index
                        break

                if not collided:
                    continue

                enemy.alive = False
                killed_ids.add(id(enemy))

                self.enemy_death_fx.spawn(enemy.pos, enemy.vel, getattr(enemy, "death_color", (255, 65, 65)), getattr(enemy, "death_core", (255, 175, 175)))
                self.camera.add_shake(0.12)

                break_orb = getattr(hazard, "break_orb", None)

                if break_orb is not None and hit_orb_index is not None:
                    depleted = break_orb(hit_orb_index)

                    if depleted:
                        self.enemy_death_fx.spawn(hazard.pos, hazard.vel, getattr(hazard, "death_color", (255, 255, 255)), getattr(hazard, "death_core", (255, 255, 255)))
                        self.camera.add_shake(0.30)
                        killed_ids.add(id(hazard))
                        break

    def check_player_collision(self):
        for enemy in self.enemies:
            if not enemy.alive or getattr(enemy, "spawn_intro_active", False):
                continue

            hazard_points_method = getattr(enemy, "get_hazard_points", None)

            if hazard_points_method is not None and getattr(enemy, "can_damage_player", False):
                for hazard_data in hazard_points_method():
                    hazard_pos = hazard_data[0]
                    hazard_radius = hazard_data[1]

                    delta = self.wrapped_delta(hazard_pos, self.player.pos)
                    collision_radius = hazard_radius + PLAYER_HIT_RADIUS

                    if delta.length_squared() <= collision_radius * collision_radius:
                        self.kill_player()
                        return

                continue

            if not getattr(enemy, "can_damage_player", True):
                if getattr(enemy, "push_player_on_contact", False):
                    self.resolve_player_enemy_push(enemy)

                continue

            delta = enemy.pos - self.player.pos

            if delta.x > self.world_size.x * 0.5:
                delta.x -= self.world_size.x
            elif delta.x < -self.world_size.x * 0.5:
                delta.x += self.world_size.x

            if delta.y > self.world_size.y * 0.5:
                delta.y -= self.world_size.y
            elif delta.y < -self.world_size.y * 0.5:
                delta.y += self.world_size.y

            radius = PLAYER_HIT_RADIUS + enemy.hit_radius

            if delta.length_squared() <= radius * radius:
                self.kill_player()
                return

    def resolve_player_enemy_push(self, enemy):
        delta = self.wrapped_delta(enemy.pos, self.player.pos)

        radius = PLAYER_HIT_RADIUS + enemy.hit_radius

        distance_sq = delta.length_squared()

        if distance_sq >= radius * radius:
            return

        if distance_sq > 0.001:
            distance = math.sqrt(distance_sq)
            normal = delta / distance
        else:
            distance = 0.0
            normal = pygame.Vector2(1.0, 0.0)

        penetration = radius - distance

        self.player.pos += normal * (penetration * 0.58 + 0.15)
        enemy.pos -= normal * (penetration * 0.42 + 0.15)

        self.wrap_position(self.player.pos)
        self.wrap_position(enemy.pos)

        relative_velocity = self.player.vel - enemy.vel

        closing_speed = max(0.0, -relative_velocity.dot(normal))

        impulse = 42.0 + closing_speed * 0.42

        self.player.vel += normal * impulse
        enemy.vel -= normal * impulse * 0.52
        player_limit = PLAYER_MAX_SPEED * 1.08

        if self.player.vel.length() > player_limit:
            self.player.vel.scale_to_length(player_limit)

        enemy_limit = getattr(enemy, "max_speed", enemy.vel.length()) * 1.55

        if enemy_limit > 0.0 and enemy.vel.length() > enemy_limit:
            enemy.vel.scale_to_length(enemy_limit)

        if hasattr(enemy, "angle") and enemy.vel.length_squared() > 1.0:
            enemy.angle = math.atan2(enemy.vel.y, enemy.vel.x)

    def kill_player(self):
        if not self.player_alive:
            return

        self.player_alive = False
        self.player_hp = 0.0
        self.hud.set_health(0.0, self.player_max_hp, hit=True)

        if self.mode_controller is not None:
            self.mode_controller.on_player_death(self)

        death_pos = self.player.pos.copy()
        death_velocity = self.player.vel.copy()

        self.player_death_fx.spawn(death_pos, death_velocity)

        self.prepare_enemy_drift()

        self.camera.add_shake(2.05)
        self.time_controller.trigger_player_death()

    def prepare_enemy_drift(self):
        for enemy in self.enemies:
            if not enemy.alive:
                continue

            if getattr(enemy, "spawn_intro_active", False):
                enemy.pos = enemy.spawn_intro_target.copy()
                enemy.spawn_intro_active = False

            angle = random.uniform(0.0, math.tau)
            direction = pygame.Vector2(math.cos(angle), math.sin(angle))

            current_speed = enemy.vel.length()

            if current_speed < 40.0:
                current_speed = random.uniform(80.0, 140.0)

            enemy.vel = direction * current_speed
            enemy.drift_turn = random.uniform(-0.32, 0.32)

            if hasattr(enemy, "angle"):
                enemy.angle = angle

            if hasattr(enemy, "speed"):
                enemy.speed = current_speed

    def build_damage_vignette(self):
        width = self.screen.get_width()
        height = self.screen.get_height()

        surface = pygame.Surface((width, height), pygame.SRCALPHA)

        edge_alpha = 30
        surface.fill((205, 18, 30, edge_alpha))

        center = (width // 2, height // 2)

        outer_width = int(width * 0.98)
        outer_height = int(height * 0.92)

        clear_width = int(width * 0.72)
        clear_height = int(height * 0.64)

        steps = 64

        for i in range(steps):
            t = i / max(1, steps - 1)
            smooth = t * t * (3.0 - 2.0 * t)

            ellipse_width = int(outer_width + (clear_width - outer_width) * smooth)
            ellipse_height = int(outer_height + (clear_height - outer_height) * smooth)

            alpha = int(edge_alpha * (1.0 - smooth))

            rect = pygame.Rect(0, 0, ellipse_width, ellipse_height)
            rect.center = center

            pygame.draw.ellipse(surface, (205, 18, 30, alpha), rect)

        clear_rect = pygame.Rect(0, 0, clear_width, clear_height)
        clear_rect.center = center

        pygame.draw.ellipse(surface, (0, 0, 0, 0), clear_rect)

        return surface

    def draw_damage_vignette(self):
        if self.damage_vignette <= 0.001:
            return

        strength = max(0.0, min(1.0, self.damage_vignette))

        self.damage_vignette_surface.set_alpha(int(255 * strength))
        self.screen.blit(self.damage_vignette_surface, (0, 0))

    def draw(self):
        self.fx.fill((0, 0, 0, 0))
        self.world.draw(self.screen, self.fx, self.camera, self.scale)
        self.walls.draw(self.screen, self.fx, self.camera, self.scale)

        for projectile in self.projectiles:
            projectile.draw(self.screen, self.fx, self.camera, self.scale)

        for projectile in self.enemy_projectiles:
            projectile.draw(self.screen, self.fx, self.camera, self.scale)

        for enemy in self.enemies:
            draw_enemy_spawn_fx(self.fx, enemy, self.camera, self.scale)
            enemy.draw(self.screen, self.fx, self.camera, self.scale)

        self.enemy_death_fx.draw(self.screen, self.fx, self.camera, self.scale)

        if self.player_alive:
            self.player.draw(self.screen, self.fx, self.camera, self.scale)

        self.player_death_fx.draw(self.screen, self.fx, self.camera, self.scale)

        self.border_fx.draw(self.screen, self.fx)
        self.screen.blit(self.fx, (0, 0))
        self.walls.draw_body_overlay(self.screen, self.camera, self.scale)

        self.draw_damage_vignette()

        if self.mode_controller is not None:
            self.hud.draw(self.screen, self.mode_controller.get_boss_progress(), self.mode_controller.get_boss_remaining())
        else:
            self.hud.draw(self.screen)

        draw_cursor(self.screen, pygame.mouse.get_pos(), self.scale)
        pygame.display.flip()

    def close(self):
        pygame.mouse.set_visible(True)
        pygame.quit()
        sys.exit()
