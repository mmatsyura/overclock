import math
import random
import pygame

from src.settings import PLAYER_ACCENT, PLAYER_CORE, PLAYER_MAX_SPEED


class PlayerDeathFX:
    def __init__(self):
        self.shards = []
        self.sparks = []
        self.motes = []
        self.bursts = []

    @staticmethod
    def random_direction():
        angle = random.uniform(0.0, math.tau)
        return pygame.Vector2(math.cos(angle), math.sin(angle))

    @staticmethod
    def cone_direction(forward, spread):
        angle = math.atan2(forward.y, forward.x) + random.uniform(-spread, spread)
        return pygame.Vector2(math.cos(angle), math.sin(angle))

    def spawn(self, pos, velocity):
        pos = pygame.Vector2(pos)
        velocity = pygame.Vector2(velocity)

        speed = velocity.length()
        speed_ratio = max(0.0, min(1.0, speed / PLAYER_MAX_SPEED))

        if speed > 10.0:
            forward = velocity.normalize()
        else:
            forward = self.random_direction()

        self.bursts.append({"pos": pos.copy(), "age": 0.0, "life": 0.42})

        shard_impulse = 120.0 + 380.0 * speed_ratio
        spark_impulse = 220.0 + 560.0 * speed_ratio
        mote_impulse = 60.0 + 180.0 * speed_ratio

        for _ in range(76):
            direction = self.cone_direction(forward, random.uniform(0.45, 1.25)) if speed > 10.0 else self.random_direction()
            inherited = velocity * random.uniform(0.42, 0.82)
            impulse = direction * random.uniform(shard_impulse * 0.55, shard_impulse)
            self.shards.append({"pos": pos.copy(), "vel": inherited + impulse, "age": 0.0, "life": random.uniform(0.85, 1.55) + speed_ratio * 0.35, "size": random.uniform(3.5, 9.5), "angle": random.uniform(0.0, math.tau), "spin": random.uniform(-9.0, 9.0)})

        for _ in range(48):
            direction = self.cone_direction(forward, random.uniform(0.25, 0.90)) if speed > 10.0 else self.random_direction()
            inherited = velocity * random.uniform(0.50, 0.90)
            impulse = direction * random.uniform(spark_impulse * 0.55, spark_impulse)
            self.sparks.append({"pos": pos.copy(), "vel": inherited + impulse, "age": 0.0, "life": random.uniform(0.45, 0.85) + speed_ratio * 0.18, "length": random.uniform(13.0, 30.0)})

        for _ in range(34):
            direction = self.cone_direction(forward, random.uniform(0.75, 1.55)) if speed > 10.0 else self.random_direction()
            inherited = velocity * random.uniform(0.30, 0.65)
            impulse = direction * random.uniform(mote_impulse * 0.45, mote_impulse)
            self.motes.append({"pos": pos.copy(), "vel": inherited + impulse, "age": 0.0, "life": random.uniform(1.0, 1.8), "size": random.uniform(1.8, 4.8)})

        for _ in range(18):
            direction = -forward + self.random_direction() * 0.45 if speed > 10.0 else self.random_direction()
            if direction.length_squared() > 0:
                direction = direction.normalize()
            self.shards.append({"pos": pos.copy(), "vel": velocity * random.uniform(0.10, 0.30) + direction * random.uniform(70.0, 150.0), "age": 0.0, "life": random.uniform(0.75, 1.20), "size": random.uniform(3.0, 7.0), "angle": random.uniform(0.0, math.tau), "spin": random.uniform(-8.0, 8.0)})

    def update(self, dt, world_size, walls=None):
        for burst in self.bursts:
            burst["age"] += dt

        self.bursts = [burst for burst in self.bursts if burst["age"] < burst["life"]]

        shard_drag = 0.984 ** (dt * 60.0)
        spark_drag = 0.975 ** (dt * 60.0)
        mote_drag = 0.991 ** (dt * 60.0)

        for shard in self.shards:
            shard["age"] += dt

            prev_pos = shard["pos"].copy()
            next_pos = shard["pos"] + shard["vel"] * dt

            if walls is not None:
                shard_radius = max(2.5, shard["size"] * 0.40)
                shard["pos"], shard["vel"] = walls.bounce_particle(prev_pos, next_pos, shard["vel"], shard_radius, 0.72)
            else:
                shard["pos"] = next_pos

            shard["vel"] *= shard_drag
            shard["angle"] += shard["spin"] * dt
            self.wrap(shard["pos"], world_size)

        for spark in self.sparks:
            spark["age"] += dt

            prev_pos = spark["pos"].copy()
            next_pos = spark["pos"] + spark["vel"] * dt

            if walls is not None:
                spark["pos"], spark["vel"] = walls.bounce_particle(prev_pos, next_pos, spark["vel"], 1.5, 0.68)
            else:
                spark["pos"] = next_pos

            spark["vel"] *= spark_drag
            self.wrap(spark["pos"], world_size)

        for mote in self.motes:
            mote["age"] += dt

            prev_pos = mote["pos"].copy()
            next_pos = mote["pos"] + mote["vel"] * dt

            if walls is not None:
                mote_radius = max(1.2, mote["size"] * 0.30)
                mote["pos"], mote["vel"] = walls.bounce_particle(prev_pos, next_pos, mote["vel"], mote_radius, 0.55)
            else:
                mote["pos"] = next_pos

            mote["vel"] *= mote_drag
            self.wrap(mote["pos"], world_size)

        self.shards = [shard for shard in self.shards if shard["age"] < shard["life"]]
        self.sparks = [spark for spark in self.sparks if spark["age"] < spark["life"]]
        self.motes = [mote for mote in self.motes if mote["age"] < mote["life"]]

    def draw(self, screen, fx, camera, scale):
        for burst in self.bursts:
            self.draw_burst(screen, fx, camera, scale, burst)

        for shard in self.shards:
            self.draw_shard(screen, fx, camera, scale, shard)

        for spark in self.sparks:
            self.draw_spark(screen, fx, camera, scale, spark)

        for mote in self.motes:
            self.draw_mote(screen, fx, camera, scale, mote)

    def draw_burst(self, screen, fx, camera, scale, burst):
        progress = max(0.0, min(1.0, burst["age"] / burst["life"]))
        fade = (1.0 - progress) ** 2
        center = camera.world_to_screen(burst["pos"], scale)
        draw_scale = camera.render_scale(scale)
        radius = max(3, int((8.0 + progress * 42.0) * draw_scale))

        pygame.draw.circle(fx, (65, 175, 255, int(85 * fade)), center, radius, max(2, int(5 * draw_scale)))
        pygame.draw.circle(fx, (175, 230, 255, int(175 * fade)), center, max(2, int(radius * 0.72)), max(1, int(2 * draw_scale)))

    def draw_shard(self, screen, fx, camera, scale, shard):
        life = max(0.0, 1.0 - shard["age"] / shard["life"])
        pos = camera.world_to_screen_raw(shard["pos"], scale)
        draw_scale = camera.render_scale(scale)
        direction = pygame.Vector2(math.cos(shard["angle"]), math.sin(shard["angle"]))
        side = pygame.Vector2(-direction.y, direction.x)
        size = shard["size"] * draw_scale
        tip = pos + direction * size
        left = pos - direction * size * 0.62 + side * size * 0.42
        right = pos - direction * size * 0.62 - side * size * 0.42
        points = [(int(tip.x), int(tip.y)), (int(left.x), int(left.y)), (int(right.x), int(right.y))]

        pygame.draw.polygon(fx, (65, 175, 255, int(38 * life)), points)
        pygame.draw.polygon(screen, (4, 20, 32), points)
        pygame.draw.lines(screen, PLAYER_ACCENT, True, points, max(1, int(draw_scale)))

    def draw_spark(self, screen, fx, camera, scale, spark):
        if spark["vel"].length_squared() <= 1.0:
            return

        life = max(0.0, 1.0 - spark["age"] / spark["life"])
        pos = camera.world_to_screen_raw(spark["pos"], scale)
        draw_scale = camera.render_scale(scale)
        direction = spark["vel"].normalize()
        tail = pos - direction * spark["length"] * draw_scale

        pygame.draw.line(fx, (55, 155, 255, int(45 * life)), tail, pos, max(3, int(7 * draw_scale)))
        pygame.draw.line(fx, (95, 205, 255, int(125 * life)), tail, pos, max(2, int(4 * draw_scale)))
        pygame.draw.line(screen, PLAYER_CORE, tail, pos, max(1, int(2 * draw_scale)))

    def draw_mote(self, screen, fx, camera, scale, mote):
        life = max(0.0, 1.0 - mote["age"] / mote["life"])
        pos = camera.world_to_screen_raw(mote["pos"], scale)
        draw_scale = camera.render_scale(scale)
        radius = max(1, int(mote["size"] * draw_scale))

        pygame.draw.circle(fx, (55, 165, 255, int(30 * life)), pos, radius * 2)
        pygame.draw.circle(screen, PLAYER_ACCENT, pos, radius)

    @staticmethod
    def wrap(pos, world_size):
        pos.x %= world_size.x
        pos.y %= world_size.y

    def keeps_death_slowmo(self):
        return bool(self.shards)

    def is_active(self):
        return bool(self.bursts or self.shards or self.sparks or self.motes)