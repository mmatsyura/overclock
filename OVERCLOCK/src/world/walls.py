import math
import random

import pygame

from src.settings import PLAYER_MAX_SPEED, WALL_COUNT_MIN, WALL_COUNT_MAX, WALL_LENGTH_MIN, WALL_LENGTH_MAX, WALL_THICKNESS_MIN, WALL_THICKNESS_MAX, WALL_EDGE_MARGIN, WALL_GAP, WALL_PLAYER_CLEARANCE


class WallField:
    def __init__(self, world_size, player_spawn=None, auto_generate=True):
        self.world_size = pygame.Vector2(world_size)
        self.walls = []

        if auto_generate and player_spawn is not None:
            self.generate(player_spawn)

    def generate(self, player_spawn):
        self.walls.clear()

        target_count = random.randint(WALL_COUNT_MIN, WALL_COUNT_MAX)
        attempts = 0

        while len(self.walls) < target_count and attempts < 300:
            attempts += 1

            length = random.uniform(WALL_LENGTH_MIN, WALL_LENGTH_MAX)
            thickness = random.uniform(WALL_THICKNESS_MIN, WALL_THICKNESS_MAX)
            angle = random.uniform(0.0, math.tau)

            direction = pygame.Vector2(math.cos(angle), math.sin(angle))
            center = pygame.Vector2(random.uniform(WALL_EDGE_MARGIN, self.world_size.x - WALL_EDGE_MARGIN), random.uniform(WALL_EDGE_MARGIN, self.world_size.y - WALL_EDGE_MARGIN))

            half = direction * (length * 0.5)

            wall = {"center": center, "a": center - half, "b": center + half, "thickness": thickness, "length": length, "angle": angle}

            if self.valid_spawn(wall, player_spawn):
                wall["sprite"], wall["glow_sprite"] = self.build_sprite(wall)
                self.walls.append(wall)

    def valid_spawn(self, wall, player_spawn):
        a = wall["a"]
        b = wall["b"]

        if a.x < WALL_EDGE_MARGIN or a.x > self.world_size.x - WALL_EDGE_MARGIN or a.y < WALL_EDGE_MARGIN or a.y > self.world_size.y - WALL_EDGE_MARGIN:
            return False

        if b.x < WALL_EDGE_MARGIN or b.x > self.world_size.x - WALL_EDGE_MARGIN or b.y < WALL_EDGE_MARGIN or b.y > self.world_size.y - WALL_EDGE_MARGIN:
            return False

        if self.point_segment_distance(player_spawn, a, b) < WALL_PLAYER_CLEARANCE:
            return False

        for other in self.walls:
            minimum_gap = WALL_GAP + wall["thickness"] * 0.5 + other["thickness"] * 0.5

            if self.segment_distance(wall["a"], wall["b"], other["a"], other["b"]) < minimum_gap:
                return False

        return True

    @staticmethod
    def closest_point_on_segment(point, a, b):
        point = pygame.Vector2(point)
        a = pygame.Vector2(a)
        b = pygame.Vector2(b)

        segment = b - a
        length_sq = segment.length_squared()

        if length_sq <= 0.0001:
            return a.copy()

        t = (point - a).dot(segment) / length_sq
        t = max(0.0, min(1.0, t))

        return a + segment * t

    @classmethod
    def point_segment_distance(cls, point, a, b):
        return pygame.Vector2(point).distance_to(cls.closest_point_on_segment(point, a, b))

    @staticmethod
    def segments_intersect(a, b, c, d):
        a = pygame.Vector2(a)
        b = pygame.Vector2(b)
        c = pygame.Vector2(c)
        d = pygame.Vector2(d)

        r = b - a
        s = d - c

        denominator = r.x * s.y - r.y * s.x

        if abs(denominator) < 0.000001:
            return False

        diff = c - a

        t = (diff.x * s.y - diff.y * s.x) / denominator
        u = (diff.x * r.y - diff.y * r.x) / denominator

        return 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0

    @classmethod
    def segment_distance(cls, a, b, c, d):
        if cls.segments_intersect(a, b, c, d):
            return 0.0

        return min(cls.point_segment_distance(a, c, d), cls.point_segment_distance(b, c, d), cls.point_segment_distance(c, a, b), cls.point_segment_distance(d, a, b))

    @classmethod
    def circle_contact(cls, wall, pos, radius):
        pos = pygame.Vector2(pos)

        closest = cls.closest_point_on_segment(pos, wall["a"], wall["b"])

        delta = pos - closest
        collision_radius = radius + wall["thickness"] * 0.5
        distance_sq = delta.length_squared()

        if distance_sq > collision_radius * collision_radius:
            return None

        if distance_sq > 0.0001:
            distance = math.sqrt(distance_sq)
            normal = delta / distance
            penetration = collision_radius - distance

            return normal, penetration

        wall_direction = wall["b"] - wall["a"]

        if wall_direction.length_squared() <= 0.0001:
            normal = pygame.Vector2(1.0, 0.0)
        else:
            wall_direction = wall_direction.normalize()
            normal = pygame.Vector2(-wall_direction.y, wall_direction.x)

        return normal, collision_radius

    def resolve_player(self, player, radius):
        strongest_impact = 0.0

        for _ in range(2):
            for wall in self.walls:
                contact = self.circle_contact(wall, player.pos, radius)

                if contact is None:
                    continue

                normal, penetration = contact

                if player.vel.dot(normal) > 0.0:
                    normal = -normal

                player.pos += normal * (penetration + 0.2)

                normal_speed = player.vel.dot(normal)

                if normal_speed >= 0.0:
                    continue

                impact = -normal_speed
                strongest_impact = max(strongest_impact, impact)

                speed_ratio = max(0.0, min(1.0, player.vel.length() / PLAYER_MAX_SPEED))
                restitution = 0.018 + 0.30 * (speed_ratio ** 1.40)
                tangent_velocity = player.vel - normal * normal_speed
                player.vel = tangent_velocity * 0.992 + normal * impact * restitution

        return strongest_impact

    def resolve_enemy(self, enemy):
        for _ in range(2):
            for wall in self.walls:
                contact = self.circle_contact(wall, enemy.pos, enemy.hit_radius)

                if contact is None:
                    continue

                normal, penetration = contact

                if enemy.vel.dot(normal) > 0.0:
                    normal = -normal

                enemy.pos += normal * (penetration + 0.2)

                normal_speed = enemy.vel.dot(normal)

                if normal_speed < 0.0:
                    tangent_velocity = enemy.vel - normal * normal_speed
                    enemy.vel = tangent_velocity * 0.994 + normal * (-normal_speed * 0.06)

                if enemy.vel.length_squared() > 1.0 and hasattr(enemy, "angle"):
                    enemy.angle = math.atan2(enemy.vel.y, enemy.vel.x)

                if hasattr(enemy, "speed"):
                    enemy.speed = enemy.vel.length()

    def avoidance_direction(self, pos, desired_dir, velocity, radius):
        pos = pygame.Vector2(pos)
        desired_dir = pygame.Vector2(desired_dir)

        if desired_dir.length_squared() <= 0.001:
            return desired_dir

        desired_dir = desired_dir.normalize()

        speed = pygame.Vector2(velocity).length()
        lookahead = 90.0 + min(110.0, speed * 0.45)

        future = pos + desired_dir * lookahead

        danger_wall = None
        danger_distance = float("inf")

        for wall in self.walls:
            clearance = radius + wall["thickness"] * 0.5 + 30.0
            distance = self.segment_distance(pos, future, wall["a"], wall["b"])

            if distance < clearance and distance < danger_distance:
                danger_distance = distance
                danger_wall = wall

        if danger_wall is None:
            return desired_dir

        wall_direction = danger_wall["b"] - danger_wall["a"]

        if wall_direction.length_squared() <= 0.001:
            return desired_dir

        wall_direction = wall_direction.normalize()
        side = pygame.Vector2(-wall_direction.y, wall_direction.x)

        clearance = radius + danger_wall["thickness"] * 0.5 + 42.0

        candidates = [danger_wall["a"] - wall_direction * clearance + side * clearance, danger_wall["a"] - wall_direction * clearance - side * clearance, danger_wall["b"] + wall_direction * clearance + side * clearance, danger_wall["b"] + wall_direction * clearance - side * clearance]

        best_direction = desired_dir
        best_score = float("inf")

        for point in candidates:
            offset = point - pos

            if offset.length_squared() <= 1.0:
                continue

            candidate = offset.normalize()

            angle_cost = 1.0 - max(-1.0, min(1.0, candidate.dot(desired_dir)))
            distance_cost = min(1.0, offset.length() / max(1.0, lookahead * 2.0))

            score = angle_cost * 2.2 + distance_cost * 0.22

            if score < best_score:
                best_score = score
                best_direction = candidate

        result = desired_dir * 0.15 + best_direction * 1.35

        if result.length_squared() > 0.001:
            result = result.normalize()

        return result

    def sweep_circle_wall(self, start, end, wall, radius):
        start = pygame.Vector2(start)
        end = pygame.Vector2(end)

        movement = end - start
        travel = movement.length()

        collision_radius = radius + wall["thickness"] * 0.5

        samples = max(8, min(96, int(travel / max(2.0, collision_radius * 0.35)) + 2))

        previous_t = 0.0

        for index in range(1, samples + 1):
            t = index / samples
            point = start.lerp(end, t)

            if self.point_segment_distance(point, wall["a"], wall["b"]) <= collision_radius:
                low = previous_t
                high = t

                for _ in range(8):
                    middle = (low + high) * 0.5
                    middle_point = start.lerp(end, middle)

                    if self.point_segment_distance(middle_point, wall["a"], wall["b"]) <= collision_radius:
                        high = middle
                    else:
                        low = middle

                hit_t = high
                hit = start.lerp(end, hit_t)

                closest = self.closest_point_on_segment(hit, wall["a"], wall["b"])
                normal = hit - closest

                if normal.length_squared() <= 0.0001:
                    wall_direction = wall["b"] - wall["a"]

                    if wall_direction.length_squared() <= 0.0001:
                        normal = pygame.Vector2(1.0, 0.0)
                    else:
                        wall_direction = wall_direction.normalize()
                        normal = pygame.Vector2(-wall_direction.y, wall_direction.x)
                else:
                    normal = normal.normalize()

                if movement.dot(normal) > 0.0:
                    normal = -normal

                return hit_t, hit, normal

            previous_t = t

        return None

    def ricochet_projectile(self, projectile, radius):
        best = None
        best_wall = None

        for wall in self.walls:
            result = self.sweep_circle_wall(projectile.prev_pos, projectile.pos, wall, radius)

            if result is None:
                continue

            if best is None or result[0] < best[0]:
                best = result
                best_wall = wall

        if best is None:
            return False

        hit_t, hit, normal = best

        incoming_velocity = projectile.vel
        normal_speed = incoming_velocity.dot(normal)

        if normal_speed < 0.0:
            projectile.vel = incoming_velocity - 2.0 * normal_speed * normal
            projectile.vel *= 0.96

        remaining = 1.0 - hit_t
        frame_movement = projectile.pos - projectile.prev_pos
        reflected_movement = frame_movement - 2.0 * frame_movement.dot(normal) * normal

        projectile.pos = hit + normal * 1.0 + reflected_movement * remaining * 0.96

        if projectile.vel.length_squared() > 0.001:
            projectile.direction = projectile.vel.normalize()

        return True

    def bounce_particle(self, prev_pos, pos, velocity, radius, restitution=0.70, max_bounces=3):
        start = pygame.Vector2(prev_pos)
        end = pygame.Vector2(pos)
        velocity = pygame.Vector2(velocity)

        for _ in range(max_bounces):
            best = None
            best_wall = None

            for wall in self.walls:
                result = self.sweep_circle_wall(start, end, wall, radius)

                if result is None:
                    continue

                if best is None or result[0] < best[0]:
                    best = result
                    best_wall = wall

            if best is None:
                return end, velocity

            hit_t, hit, normal = best

            normal_speed = velocity.dot(normal)

            if normal_speed < 0.0:
                velocity = velocity - (1.0 + restitution) * normal_speed * normal

            movement = end - start
            reflected_movement = movement - 2.0 * movement.dot(normal) * normal
            remaining = 1.0 - hit_t

            start = hit + normal * 1.2
            end = start + reflected_movement * remaining * restitution

        return end, velocity

    def build_sprite(self, wall):
        length = max(80, int(round(wall["length"])))
        thickness = max(8, int(round(wall["thickness"])))
        padding = max(20, thickness * 2)

        width = length + padding * 2
        height = max(36, thickness + padding * 2)

        ss = 4

        hi_width = width * ss
        hi_height = height * ss

        body_hi = pygame.Surface((hi_width, hi_height), pygame.SRCALPHA)
        glow_hi = pygame.Surface((hi_width, hi_height), pygame.SRCALPHA)

        center_y = hi_height // 2
        outer_h = max(thickness * ss + 20, 38)
        inner_h = max(8, outer_h - 16)

        outer_rect = pygame.Rect(padding * ss, center_y - outer_h // 2, length * ss, outer_h)
        inner_rect = pygame.Rect(outer_rect.left + 8, center_y - inner_h // 2, outer_rect.width - 16, inner_h)

        for inflate, alpha in ((56, 8), (38, 14), (22, 22), (10, 30)):
            glow_rect = outer_rect.inflate(inflate, inflate)
            pygame.draw.rect(glow_hi, (255, 55, 55, alpha), glow_rect, border_radius=max(16, glow_rect.height // 2))

        pygame.draw.rect(body_hi, (255, 70, 70), outer_rect, max(6, ss + 1), border_radius=max(14, outer_rect.height // 2))

        pygame.draw.rect(body_hi, (0, 0, 0, 0), inner_rect, border_radius=max(10, inner_rect.height // 2))

        body = pygame.transform.smoothscale(body_hi, (width, height)).convert_alpha()
        glow = pygame.transform.smoothscale(glow_hi, (width, height)).convert_alpha()

        return body, glow

    def draw(self, screen, fx, camera, scale):
        draw_scale = camera.render_scale(scale)

        for wall in self.walls:
            center = camera.world_to_screen(wall["center"], scale)
            angle = -math.degrees(wall["angle"])

            soft_glow = wall["glow_sprite"].copy()
            soft_glow.set_alpha(46)
            soft_glow = pygame.transform.rotozoom(soft_glow, angle, draw_scale * 1.015)
            soft_glow_rect = soft_glow.get_rect(center=(int(center.x), int(center.y)))

            edge_glow = wall["glow_sprite"].copy()
            edge_glow.set_alpha(78)
            edge_glow = pygame.transform.rotozoom(edge_glow, angle, draw_scale * 1.03)
            edge_glow_rect = edge_glow.get_rect(center=(int(center.x), int(center.y)))

            body_sprite = pygame.transform.rotozoom(wall["sprite"], angle, draw_scale)
            body_rect = body_sprite.get_rect(center=(int(center.x), int(center.y)))

            fx.blit(soft_glow, soft_glow_rect)
            fx.blit(edge_glow, edge_glow_rect)
            screen.blit(body_sprite, body_rect)

    def draw_body_overlay(self, screen, camera, scale):
        draw_scale = camera.render_scale(scale)

        for wall in self.walls:
            center = camera.world_to_screen(wall["center"], scale)
            angle = -math.degrees(wall["angle"])
            body_sprite = pygame.transform.rotozoom(wall["sprite"], angle, draw_scale)
            body_rect = body_sprite.get_rect(center=(int(center.x), int(center.y)))
            screen.blit(body_sprite, body_rect)