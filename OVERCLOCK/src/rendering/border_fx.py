import math
import random

import pygame

from src.settings import BORDER_GLOW, BORDER_HOT


def rgba(color, alpha):
    return (
        max(0, min(255, int(color[0]))),
        max(0, min(255, int(color[1]))),
        max(0, min(255, int(color[2]))),
        max(0, min(255, int(alpha))),
    )


class BorderFX:
    def __init__(self):
        self.flash = 0.0
        self.pulses = []
        self.sparks = []
        self.bullet_waves = []

    def trigger(self, side, position):
        opposite = {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}

        self.flash = 1.0

        self.spawn_pulse(side, position, 1.0)
        self.spawn_pulse(opposite[side], position, 1.12)

        self.spawn_sparks(side, position, 10)
        self.spawn_sparks(opposite[side], position, 14)

    def trigger_bullet_hit(self, side, position):
        self.bullet_waves.append({
            "side": side,
            "position": position,
            "age": 0.0,
            "duration": 0.62,
            "distance": 0.0,
        })

    def spawn_pulse(self, side, position, power):
        self.pulses.append({
            "side": side,
            "position": position,
            "life": 1.0,
            "power": power,
            "phase": random.uniform(0.0, math.tau),
        })

    def spawn_sparks(self, side, position, count):
        for _ in range(count):
            life = random.uniform(0.22, 0.42)

            self.sparks.append({
                "side": side,
                "position": position + random.uniform(-0.035, 0.035),
                "offset": random.uniform(-25, 25),
                "distance": random.uniform(12, 55),
                "speed": random.uniform(0.75, 1.25),
                "life": life,
                "max_life": life,
                "width": random.choice((1, 1, 1, 2)),
                "drift": random.uniform(-12, 12),
                "length": random.uniform(12, 28),
            })

    def update(self, dt):
        self.flash = max(0.0, self.flash - dt * 5.0)

        for pulse in self.pulses:
            pulse["life"] -= dt * 2.55

        for spark in self.sparks:
            spark["life"] -= dt
            spark["distance"] += 105 * spark["speed"] * dt
            spark["offset"] += spark["drift"] * dt

        for wave in self.bullet_waves:
            wave["age"] += dt
            wave["distance"] += 850 * dt

        self.pulses = [pulse for pulse in self.pulses if pulse["life"] > 0]
        self.sparks = [spark for spark in self.sparks if spark["life"] > 0]
        self.bullet_waves = [wave for wave in self.bullet_waves if wave["age"] < wave["duration"]]

    def draw(self, screen, fx):
        w, h = screen.get_size()
        self.draw_global_flash(fx, w, h)

        for wave in self.bullet_waves:
            self.draw_bullet_wave(fx, wave, w, h)
        for pulse in self.pulses:
            self.draw_pulse(fx, pulse, w, h)
        for spark in self.sparks:
            self.draw_spark(fx, spark, w, h)

    def draw_global_flash(self, fx, w, h):
        if self.flash <= 0:
            return

        power = self.flash * self.flash
        depth = 135
        steps = 18

        for i in range(steps):
            t = 1.0 - i / steps
            alpha = 15 * power * t * t
            inset = int(depth * i / steps)
            width = max(2, depth // steps)

            pygame.draw.line(fx, rgba(BORDER_GLOW, alpha), (0, inset), (w, inset), width)
            pygame.draw.line(fx, rgba(BORDER_GLOW, alpha), (0, h - 1 - inset), (w, h - 1 - inset), width)
            pygame.draw.line(fx, rgba(BORDER_GLOW, alpha), (inset, 0), (inset, h), width)
            pygame.draw.line(fx, rgba(BORDER_GLOW, alpha), (w - 1 - inset, 0), (w - 1 - inset, h), width)

        for i in range(7):
            alpha = (58 - i * 7) * power
            inset = i * 4
            pygame.draw.rect(fx, rgba(BORDER_GLOW, alpha), (inset, inset, w - inset * 2, h - inset * 2), max(1, 4 - i // 2))

    def draw_bullet_wave(self, fx, wave, w, h):
        progress = max(0.0, min(1.0, wave["age"] / wave["duration"]))
        fade = (1.0 - progress) ** 1.5

        perimeter = 2 * (w + h)
        origin = self.border_to_perimeter(wave["side"], wave["position"], w, h)
        distance = wave["distance"]

        impact = self.perimeter_point(origin, w, h)

        if wave["age"] < 0.27:
            self.draw_impact_glow(fx, impact, wave["side"], wave["age"])

        trail_length = 125 + 50 * fade

        for direction in (-1, 1):
            head = (origin + direction * distance) % perimeter
            self.draw_wave_trail(fx, head, direction, trail_length, fade, w, h)

    def draw_wave_trail(self, fx, head, direction, length, fade, w, h):
        segments = 22
        previous = self.perimeter_point(head, w, h)

        for i in range(1, segments + 1):
            t = i / segments
            current = self.perimeter_point(head - direction * length * t, w, h)

            strength = (1.0 - t) ** 2.1 * fade

            pygame.draw.line(fx, rgba((255, 155, 20), 12 * strength), previous, current, 14)
            pygame.draw.line(fx, rgba((255, 195, 40), 48 * strength), previous, current, 6)
            pygame.draw.line(fx, rgba((255, 235, 105), 175 * strength), previous, current, 2)

            previous = current

        head_pos = self.perimeter_point(head, w, h)

        pygame.draw.circle(fx, rgba((255, 180, 30), 28 * fade), head_pos, max(3, int(8 * fade)))
        pygame.draw.circle(fx, rgba((255, 235, 110), 130 * fade), head_pos, max(2, int(4 * fade)))
        pygame.draw.circle(fx, rgba((255, 255, 220), 230 * fade), head_pos, max(1, int(2 * fade)))

    def border_to_perimeter(self, side, position, w, h):
        position = max(0.0, min(1.0, position))

        if side == "top":
            return position * w

        if side == "right":
            return w + position * h

        if side == "bottom":
            return w + h + (1.0 - position) * w

        return w + h + w + (1.0 - position) * h

    def perimeter_point(self, distance, w, h):
        perimeter = 2 * (w + h)
        distance %= perimeter

        if distance < w:
            return pygame.Vector2(distance, 0)

        distance -= w

        if distance < h:
            return pygame.Vector2(w - 1, distance)

        distance -= h

        if distance < w:
            return pygame.Vector2(w - 1 - distance, h - 1)

        distance -= w
        return pygame.Vector2(0, h - 1 - distance)

    def draw_pulse(self, fx, pulse, w, h):
        life = pulse["life"]
        power = pulse["power"]
        side = pulse["side"]
        position = pulse["position"]

        fade = max(0.0, min(1.0, life * life * power))
        burst = math.sin((1.0 - life) * math.pi)
        wave = 0.92 + math.sin(pulse["phase"] + life * 13.0) * 0.08

        core = int((175 + 170 * burst) * wave)
        glow = int(core * 1.8)
        depth = int(105 + 120 * burst)

        if side in ("left", "right"):
            y = int(position * h)
            x = 0 if side == "left" else w - 1
            direction = 1 if side == "left" else -1
            self.draw_vertical_pulse(fx, x, y, direction, core, glow, depth, fade)
        else:
            x = int(position * w)
            y = 0 if side == "top" else h - 1
            direction = 1 if side == "top" else -1
            self.draw_horizontal_pulse(fx, x, y, direction, core, glow, depth, fade)

    def draw_vertical_pulse(self, fx, x, y, direction, core, glow, depth, fade):
        pygame.draw.line(fx, rgba(BORDER_GLOW, 18 * fade), (x, y - glow), (x, y + glow), 48)
        pygame.draw.line(fx, rgba(BORDER_GLOW, 45 * fade), (x, y - glow), (x, y + glow), 24)
        pygame.draw.line(fx, rgba(BORDER_GLOW, 155 * fade), (x, y - core), (x, y + core), 9)
        pygame.draw.line(fx, rgba(BORDER_HOT, 245 * fade), (x, y - core // 2), (x, y + core // 2), 3)

        for i in range(14):
            t = i / 13
            distance = int(depth * t)
            half = int(core * (1.0 - t) * 0.76)
            alpha = 38 * fade * (1.0 - t) ** 2
            px = x + direction * distance
            pygame.draw.line(fx, rgba(BORDER_GLOW, alpha), (px, y - half), (px, y + half), 8)

        tip = x + direction * depth

        pygame.draw.line(fx, rgba(BORDER_GLOW, 30 * fade), (x, y), (tip, y), 5)
        pygame.draw.circle(fx, rgba(BORDER_GLOW, 55 * fade), (x, y), 20)
        pygame.draw.circle(fx, rgba(BORDER_HOT, 150 * fade), (x, y), 7)
        pygame.draw.circle(fx, rgba((255, 235, 170), 220 * fade), (x, y), 3)

    def draw_horizontal_pulse(self, fx, x, y, direction, core, glow, depth, fade):
        pygame.draw.line(fx, rgba(BORDER_GLOW, 18 * fade), (x - glow, y), (x + glow, y), 48)
        pygame.draw.line(fx, rgba(BORDER_GLOW, 45 * fade), (x - glow, y), (x + glow, y), 24)
        pygame.draw.line(fx, rgba(BORDER_GLOW, 155 * fade), (x - core, y), (x + core, y), 9)
        pygame.draw.line(fx, rgba(BORDER_HOT, 245 * fade), (x - core // 2, y), (x + core // 2, y), 3)

        for i in range(14):
            t = i / 13
            distance = int(depth * t)
            half = int(core * (1.0 - t) * 0.76)
            alpha = 38 * fade * (1.0 - t) ** 2
            py = y + direction * distance
            pygame.draw.line(fx, rgba(BORDER_GLOW, alpha), (x - half, py), (x + half, py), 8)

        tip = y + direction * depth

        pygame.draw.line(fx, rgba(BORDER_GLOW, 30 * fade), (x, y), (x, tip), 5)
        pygame.draw.circle(fx, rgba(BORDER_GLOW, 55 * fade), (x, y), 20)
        pygame.draw.circle(fx, rgba(BORDER_HOT, 150 * fade), (x, y), 7)
        pygame.draw.circle(fx, rgba((255, 235, 170), 220 * fade), (x, y), 3)

    def draw_spark(self, fx, spark, w, h):
        life01 = max(0.0, min(1.0, spark["life"] / spark["max_life"]))
        alpha = 220 * life01 * life01

        side = spark["side"]
        position = spark["position"]
        distance = spark["distance"]
        offset = spark["offset"]
        length = spark["length"] * (0.6 + life01 * 0.4)

        if side == "left":
            start = pygame.Vector2(distance, position * h + offset)
            end = start + pygame.Vector2(length, 0)
        elif side == "right":
            start = pygame.Vector2(w - distance, position * h + offset)
            end = start - pygame.Vector2(length, 0)
        elif side == "top":
            start = pygame.Vector2(position * w + offset, distance)
            end = start + pygame.Vector2(0, length)
        else:
            start = pygame.Vector2(position * w + offset, h - distance)
            end = start - pygame.Vector2(0, length)

        pygame.draw.line(fx, rgba(BORDER_GLOW, alpha * 0.25), start, end, spark["width"] + 5)
        pygame.draw.line(fx, rgba(BORDER_HOT, alpha), start, end, spark["width"])

    def draw_impact_glow(self, fx, pos, side, age):
        x, y = int(pos.x), int(pos.y)

        duration = 0.27
        t = max(0.0, min(1.0, age / duration))
        fade = (1.0 - t) ** 1.35

        burst = math.sin(t * math.pi)
        depth = 18 + 38 * burst
        spread = 40 + 30 * burst

        if side == "left":
            for i in range(8):
                k = i / 7
                px = x + depth * k
                half = spread * (1.0 - k) ** 0.55
                alpha = 56 * fade * (1.0 - k) ** 1.35
                pygame.draw.line(fx, rgba((255, 195, 45), alpha), (px, y - half), (px, y + half), 5)

        elif side == "right":
            for i in range(8):
                k = i / 7
                px = x - depth * k
                half = spread * (1.0 - k) ** 0.55
                alpha = 56 * fade * (1.0 - k) ** 1.35
                pygame.draw.line(fx, rgba((255, 195, 45), alpha), (px, y - half), (px, y + half), 5)

        elif side == "top":
            for i in range(8):
                k = i / 7
                py = y + depth * k
                half = spread * (1.0 - k) ** 0.55
                alpha = 56 * fade * (1.0 - k) ** 1.35
                pygame.draw.line(fx, rgba((255, 195, 45), alpha), (x - half, py), (x + half, py), 5)

        else:
            for i in range(8):
                k = i / 7
                py = y - depth * k
                half = spread * (1.0 - k) ** 0.55
                alpha = 56 * fade * (1.0 - k) ** 1.35
                pygame.draw.line(fx, rgba((255, 195, 45), alpha), (x - half, py), (x + half, py), 5)

        if side in ("left", "right"):
            pygame.draw.line(fx, rgba((255, 220, 75), 150 * fade), (x, y - 24), (x, y + 24), 5)
            pygame.draw.line(fx, rgba((255, 250, 180), 235 * fade), (x, y - 8), (x, y + 8), 2)
        else:
            pygame.draw.line(fx, rgba((255, 220, 75), 150 * fade), (x - 24, y), (x + 24, y), 5)
            pygame.draw.line(fx, rgba((255, 250, 180), 235 * fade), (x - 8, y), (x + 8, y), 2)

    def trigger_enemy_wrap(self, side, position):
        opposite = {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}

        self.spawn_pulse(side, position, 0.22)
        self.spawn_pulse(opposite[side], position, 0.28)