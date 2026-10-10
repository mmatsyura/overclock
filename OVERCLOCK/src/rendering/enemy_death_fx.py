import math
import random

import pygame


def rgba(color, alpha):
    return color[0], color[1], color[2], max(0, min(255, int(alpha)))


class EnemyDeathFX:
    def __init__(self):
        self.bursts = []
        self.shards = []
        self.sparks = []
        self.embers = []

    def spawn(self, pos, inherited_velocity, color=(255, 65, 65), core=(255, 175, 175)):
        pos = pygame.Vector2(pos)
        inherited_velocity = pygame.Vector2(inherited_velocity)
        self.bursts.append({"pos": pos.copy(), "age": 0.0, "duration": 0.62, "color": color, "core": core})

        for _ in range(random.randint(44, 58)):
            angle = random.uniform(0.0, math.tau)
            direction = pygame.Vector2(math.cos(angle), math.sin(angle))
            life = random.uniform(0.75, 1.25)
            self.shards.append({
                "pos": pos.copy(), "vel": direction * random.uniform(105, 250) + inherited_velocity * 0.28,
                "angle": angle, "spin": random.uniform(-9.0, 9.0), "size": random.uniform(4.0, 10.5),
                "life": life, "max_life": life, "color": color, "core": core
            })

        for _ in range(random.randint(26, 36)):
            angle = random.uniform(0.0, math.tau)
            direction = pygame.Vector2(math.cos(angle), math.sin(angle))
            life = random.uniform(0.45, 0.75)
            self.sparks.append({
                "pos": pos.copy(), "vel": direction * random.uniform(190, 370) + inherited_velocity * 0.18,
                "life": life, "max_life": life, "length": random.uniform(12.0, 28.0), "color": color, "core": core
            })

        for _ in range(random.randint(18, 26)):
            angle = random.uniform(0.0, math.tau)
            direction = pygame.Vector2(math.cos(angle), math.sin(angle))
            life = random.uniform(0.9, 1.45)
            self.embers.append({
                "pos": pos.copy(), "vel": direction * random.uniform(55, 120) + inherited_velocity * 0.22,
                "life": life, "max_life": life, "size": random.uniform(2.5, 6.5), "color": color, "core": core
            })

    def update(self, dt, world_size, walls=None):
        for burst in self.bursts:
            burst["age"] += dt

        self.update_particles(self.shards, dt, world_size, 0.982, walls, "shard", spin=True)
        self.update_particles(self.sparks, dt, world_size, 0.972, walls, "spark")
        self.update_particles(self.embers, dt, world_size, 0.990, walls, "ember")

        self.bursts = [burst for burst in self.bursts if burst["age"] < burst["duration"]]
        self.shards = [particle for particle in self.shards if particle["life"] > 0]
        self.sparks = [particle for particle in self.sparks if particle["life"] > 0]
        self.embers = [particle for particle in self.embers if particle["life"] > 0]

    def update_particles(self, particles, dt, world_size, drag, walls=None, particle_type="spark", spin=False):
        frame_drag = drag ** (dt * 60.0)

        for particle in particles:
            particle["life"] -= dt

            prev_pos = particle["pos"].copy()
            next_pos = particle["pos"] + particle["vel"] * dt

            if walls is not None:
                if particle_type == "shard":
                    radius = max(2.5, particle["size"] * 0.42)
                    restitution = 0.74
                elif particle_type == "ember":
                    radius = max(1.5, particle["size"] * 0.32)
                    restitution = 0.58
                else:
                    radius = 1.5
                    restitution = 0.68

                particle["pos"], particle["vel"] = walls.bounce_particle(prev_pos, next_pos, particle["vel"], radius, restitution)
            else:
                particle["pos"] = next_pos

            particle["vel"] *= frame_drag

            if spin:
                particle["angle"] += particle["spin"] * dt

            self.wrap(particle["pos"], world_size)

    @staticmethod
    def wrap(pos, world_size):
        if pos.x < 0:
            pos.x += world_size.x
        elif pos.x > world_size.x:
            pos.x -= world_size.x
        if pos.y < 0:
            pos.y += world_size.y
        elif pos.y > world_size.y:
            pos.y -= world_size.y

    def draw(self, screen, fx, camera, scale):
        draw_scale = camera.render_scale(scale)

        for burst in self.bursts:
            self.draw_burst(fx, camera, scale, draw_scale, burst)
        for ember in self.embers:
            self.draw_ember(fx, camera, scale, draw_scale, ember)
        for shard in self.shards:
            self.draw_shard(fx, camera, scale, draw_scale, shard)
        for spark in self.sparks:
            self.draw_spark(fx, camera, scale, draw_scale, spark)

    def draw_burst(self, fx, camera, scale, draw_scale, burst):
        t = max(0.0, min(1.0, burst["age"] / burst["duration"]))
        pos = camera.world_to_screen(burst["pos"], scale)
        color = burst["color"]
        core = burst["core"]
        flash = max(0.0, 1.0 - t * 6.5)
        ring_fade = (1.0 - t) ** 1.65

        if flash > 0:
            pygame.draw.circle(fx, rgba(color, 82 * flash), pos, max(12, int(36 * draw_scale)))
            pygame.draw.circle(fx, rgba(color, 145 * flash), pos, max(8, int(24 * draw_scale)))
            pygame.draw.circle(fx, rgba(core, 235 * flash), pos, max(4, int(11 * draw_scale)))
            pygame.draw.circle(fx, rgba(core, 255 * flash), pos, max(2, int(5 * draw_scale)))

        ring1 = int((10 + 58 * t) * draw_scale)
        ring2 = int((4 + 36 * t) * draw_scale)
        pygame.draw.circle(fx, rgba(color, 175 * ring_fade), pos, ring1, max(1, int(3 * draw_scale)))
        pygame.draw.circle(fx, rgba(core, 130 * ring_fade), pos, ring2, max(1, int(2 * draw_scale)))

    def draw_shard(self, fx, camera, scale, draw_scale, shard):
        life = shard["life"] / shard["max_life"]
        pos = camera.world_to_screen(shard["pos"], scale)
        direction = pygame.Vector2(math.cos(shard["angle"]), math.sin(shard["angle"]))
        side = pygame.Vector2(-direction.y, direction.x)
        length = shard["size"] * draw_scale * (0.85 + life)
        width = max(1.0, shard["size"] * draw_scale * 0.45 * life)
        tip = pos + direction * length
        left = pos - direction * length * 0.55 + side * width
        right = pos - direction * length * 0.55 - side * width
        points = [(int(tip.x), int(tip.y)), (int(left.x), int(left.y)), (int(right.x), int(right.y))]
        pygame.draw.polygon(fx, rgba(shard["color"], 225 * life), points)
        pygame.draw.lines(fx, rgba(shard["core"], 240 * life), True, points, 1)

    def draw_spark(self, fx, camera, scale, draw_scale, spark):
        life = spark["life"] / spark["max_life"]
        pos = camera.world_to_screen(spark["pos"], scale)

        if spark["vel"].length_squared() <= 0.01:
            return

        direction = spark["vel"].normalize()
        tail = pos - direction * spark["length"] * draw_scale * life
        pygame.draw.line(fx, rgba(spark["color"], 58 * life), tail, pos, max(4, int(7 * draw_scale)))
        pygame.draw.line(fx, rgba(spark["color"], 135 * life), tail, pos, max(2, int(4 * draw_scale)))
        pygame.draw.line(fx, rgba(spark["core"], 255 * life), tail, pos, max(1, int(2 * draw_scale)))

    def draw_ember(self, fx, camera, scale, draw_scale, ember):
        life = ember["life"] / ember["max_life"]
        pos = camera.world_to_screen(ember["pos"], scale)
        radius = max(1, int(ember["size"] * draw_scale * life))
        pygame.draw.circle(fx, rgba(ember["color"], 42 * life), pos, radius * 4)
        pygame.draw.circle(fx, rgba(ember["color"], 120 * life), pos, radius * 2)
        pygame.draw.circle(fx, rgba(ember["core"], 235 * life), pos, radius)
