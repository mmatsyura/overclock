import math
import pygame


class HUD:
    def __init__(self, scale):
        self.scale = scale
        self.score = 0
        self.display_score = 0.0

        font_path = "assets/font/Orbitron-Black.ttf"
        self.font = pygame.font.Font(font_path, max(24, int(29 * scale)))
        self.add_font = pygame.font.Font(font_path, max(19, int(23 * scale)))
        self.boss_font = pygame.font.Font(font_path, max(18, int(22 * scale)))
        self.boss_time_font = pygame.font.Font(font_path, max(14, int(16 * scale)))
        self.hp_font = pygame.font.Font(font_path, max(14, int(16 * scale)))
        self.hp_title_font = pygame.font.Font(font_path, max(18, int(22 * scale)))

        self.color = (175, 255, 130)
        self.alpha = 145
        self.panel_alpha = 28
        self.corner_size = int(18 * scale)
        self.line_width = max(1, int(2 * scale))
        self.margin = int(18 * scale)

        self.health = 100.0
        self.max_health = 100.0
        self.display_health = 100.0
        self.health_pulse = 0.0
        self.health_alpha = 185
        self.critical_ratio = 0.25

        self.anim_time = 0.0
        self.additions = []
        self.pulse = 0.0

    @staticmethod
    def clamp01(value):
        return max(0.0, min(1.0, value))

    @staticmethod
    def lerp_color(a, b, t):
        t = max(0.0, min(1.0, t))
        return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

    def boss_color(self, progress):
        progress = self.clamp01(progress)
        green = (105, 245, 125)
        yellow = (245, 218, 72)
        red = (255, 76, 82)
        purple = (190, 82, 255)

        if progress < 1.0 / 3.0:
            return self.lerp_color(green, yellow, progress * 3.0)
        if progress < 2.0 / 3.0:
            return self.lerp_color(yellow, red, (progress - 1.0 / 3.0) * 3.0)
        return self.lerp_color(red, purple, (progress - 2.0 / 3.0) * 3.0)

    def health_color(self):
        ratio = self.clamp01(self.health / self.max_health)
        red = (255, 62, 72)
        orange = (255, 145, 62)
        yellow = (244, 218, 72)
        green = (100, 255, 125)

        if ratio <= 0.25:
            return self.lerp_color(red, orange, ratio / 0.25)
        if ratio <= 0.50:
            return self.lerp_color(orange, yellow, (ratio - 0.25) / 0.25)
        return self.lerp_color(yellow, green, (ratio - 0.50) / 0.50)

    def critical_pulse(self):
        ratio = self.health / max(1.0, self.max_health)

        if self.health <= 0.0 or ratio > self.critical_ratio:
            return 0.0

        wave = 0.5 + 0.5 * math.sin(self.anim_time * 8.5)
        return wave

    def set_score(self, score):
        self.score = max(0, int(score))
        self.display_score = float(self.score)

    def add_score(self, amount):
        amount = int(amount)

        if amount <= 0:
            return

        self.score += amount
        self.pulse = 1.0
        self.additions.append({"amount": amount, "age": 0.0, "life": 0.58})

    def set_health(self, health, max_health, hit=False, instant=False):
        self.max_health = max(1.0, float(max_health))
        self.health = max(0.0, min(self.max_health, float(health)))

        if instant:
            self.display_health = self.health

        if hit:
            self.health_pulse = 1.0

    def update(self, dt):
        self.anim_time += dt
        difference = self.score - self.display_score

        if abs(difference) < 0.01:
            self.display_score = float(self.score)
        else:
            self.display_score += difference * min(1.0, dt * 14.0)

        self.pulse = max(0.0, self.pulse - dt * 4.8)

        for addition in self.additions:
            addition["age"] += dt

        health_difference = self.health - self.display_health

        if abs(health_difference) < 0.01:
            self.display_health = self.health
        else:
            health_speed = 3.6 if health_difference < 0.0 else 8.0
            self.display_health += health_difference * min(1.0, dt * health_speed)

        self.health_pulse = max(0.0, self.health_pulse - dt * 3.4)
        self.additions = [addition for addition in self.additions if addition["age"] < addition["life"]]

    def draw_corner_panel(self, surface, color, alpha=None, background_alpha=None):
        width = surface.get_width()
        height = surface.get_height()
        alpha = self.alpha if alpha is None else alpha
        background_alpha = self.panel_alpha if background_alpha is None else background_alpha
        corner = min(self.corner_size, max(4, width // 4), max(4, height // 3))

        if background_alpha > 0:
            pygame.draw.rect(surface, (5, 9, 12, background_alpha), (0, 0, width, height))

        segments = (
            ((0, corner), (0, 0)),
            ((0, 0), (corner, 0)),
            ((width - corner, 0), (width - 1, 0)),
            ((width - 1, 0), (width - 1, corner)),
            ((0, height - corner), (0, height - 1)),
            ((0, height - 1), (corner, height - 1)),
            ((width - corner, height - 1), (width - 1, height - 1)),
            ((width - 1, height - 1), (width - 1, height - corner)),
        )

        for start, end in segments:
            pygame.draw.line(surface, (*color, alpha), start, end, self.line_width)

    def draw_score(self, screen):
        displayed_score = int(round(self.display_score))
        score_text = self.font.render(f"SCORE: {displayed_score:06d}", True, self.color)

        width = score_text.get_width() + int(42 * self.scale)
        height = score_text.get_height() + int(30 * self.scale)

        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        pulse_alpha = int(38 * self.pulse)

        self.draw_corner_panel(panel, self.color, min(220, self.alpha + pulse_alpha), self.panel_alpha)

        score_text.set_alpha(min(240, self.alpha + 45 + pulse_alpha))

        score_x = int(20 * self.scale)
        score_y = (height - score_text.get_height()) // 2

        panel.blit(score_text, (score_x, score_y))

        x = self.margin
        y = int(16 * self.scale)

        screen.blit(panel, (x, y))

        base_x = x + width + int(9 * self.scale)
        base_y = y + int(15 * self.scale)

        for index, addition in enumerate(self.additions):
            progress = addition["age"] / addition["life"]
            fade = 1.0 - progress
            rise = int(13 * self.scale * progress)

            addition_surface = self.add_font.render(f"+{addition['amount']}", True, self.color)
            addition_surface.set_alpha(int(175 * fade))

            screen.blit(addition_surface, (base_x + int(index * 4 * self.scale), base_y - rise - int(index * 3 * self.scale)))

    def draw_health(self, screen):
        ratio = self.clamp01(self.health / self.max_health)
        trail_ratio = self.clamp01(self.display_health / self.max_health)

        color = self.health_color()
        critical = self.critical_pulse()
        hit = self.health_pulse

        width = int(340 * self.scale)
        height = int(78 * self.scale)

        x = screen.get_width() - width - self.margin
        y = int(16 * self.scale)

        panel = pygame.Surface((width, height), pygame.SRCALPHA)

        panel_color = self.lerp_color(color, (255, 34, 46), critical * 0.95)

        line_alpha = min(255, self.alpha + int(35 * hit) + int(110 * critical))
        background_alpha = min(72, self.panel_alpha + int(8 * hit) + int(30 * critical))

        self.draw_corner_panel(panel, panel_color, line_alpha, background_alpha)

        padding = int(15 * self.scale)

        title_color = self.lerp_color(panel_color, (255, 255, 255), 0.32)
        value_color = self.lerp_color(panel_color, (245, 250, 255), 0.22)

        title_shadow = self.hp_title_font.render("HP", True, (0, 0, 0))
        title = self.hp_title_font.render("HP", True, title_color)

        value_text = f"{int(math.ceil(self.health)):03d} / {int(self.max_health):03d}"

        value_shadow = self.hp_font.render(value_text, True, (0, 0, 0))
        value = self.hp_font.render(value_text, True, value_color)

        title_alpha = min(255, 225 + int(18 * hit) + int(30 * critical))
        value_alpha = min(255, self.health_alpha + int(28 * hit) + int(60 * critical))

        title_shadow.set_alpha(int(title_alpha * 0.42))
        title.set_alpha(title_alpha)

        value_shadow.set_alpha(int(value_alpha * 0.42))
        value.set_alpha(value_alpha)

        title_x = padding
        title_y = int(9 * self.scale)

        value_x = width - padding - value.get_width()
        value_y = int(14 * self.scale)

        panel.blit(title_shadow, (title_x + 1, title_y + 1))
        panel.blit(title, (title_x, title_y))

        panel.blit(value_shadow, (value_x + 1, value_y + 1))
        panel.blit(value, (value_x, value_y))

        bar_x = padding
        bar_y = int(43 * self.scale)
        bar_width = width - padding * 2
        bar_height = max(11, int(13 * self.scale))

        if critical > 0.0:
            bar_height += int(2 * self.scale * critical)

        health_width = int(bar_width * ratio)
        trail_width = int(bar_width * trail_ratio)

        pygame.draw.rect(panel, (3, 7, 9, 105), (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(panel, (*panel_color, 110), (bar_x, bar_y, bar_width, bar_height), max(1, int(self.scale)))

        if trail_width > health_width:
            pygame.draw.rect(panel, (*panel_color, 42), (bar_x + health_width, bar_y, trail_width - health_width, bar_height))

        if health_width > 0:
            fill_alpha = min(255, 155 + int(28 * hit) + int(95 * critical))

            pygame.draw.rect(panel, (*panel_color, fill_alpha), (bar_x, bar_y, health_width, bar_height))
            pygame.draw.line(panel, (245, 255, 245, 82), (bar_x, bar_y + 1), (bar_x + health_width, bar_y + 1), max(1, int(self.scale)))

        for i in range(1, 10):
            segment_x = bar_x + int(bar_width * i / 10)
            pygame.draw.line(panel, (*panel_color, 42), (segment_x, bar_y + 1), (segment_x, bar_y + bar_height - 2), 1)

        if critical > 0.0:
            warning_alpha = int(95 * critical)

            pygame.draw.rect(panel, (255, 32, 44, warning_alpha), (bar_x - 4, bar_y - 4, bar_width + 8, bar_height + 8), max(1, int(2 * self.scale)))

        screen.blit(panel, (x, y))

    def draw_boss_progress(self, screen, progress, remaining):
        progress = self.clamp01(progress)
        color = self.boss_color(progress)

        width = int(470 * self.scale)
        height = int(78 * self.scale)

        x = self.margin
        y = screen.get_height() - height - self.margin

        panel = pygame.Surface((width, height), pygame.SRCALPHA)

        self.draw_corner_panel(panel, color, min(220, self.alpha + 5), self.panel_alpha)

        padding = int(20 * self.scale)

        label = self.boss_font.render("TO THE BOSS", True, color)

        label = self.boss_font.render("TO THE BOSS", True, color)

        total_seconds = max(0, int(math.ceil(remaining)))
        time_surface = self.boss_time_font.render(f"{total_seconds // 60:02d}:{total_seconds % 60:02d}", True, color)

        label.set_alpha(min(240, self.alpha + 40))
        time_surface.set_alpha(min(240, self.alpha + 40))

        bar_x = padding
        bar_y = int(45 * self.scale)
        bar_width = width - padding * 2
        bar_height = max(9, int(11 * self.scale))

        text_area_height = bar_y

        label_y = (text_area_height - label.get_height()) // 2
        time_y = (text_area_height - time_surface.get_height()) // 2

        panel.blit(label, (padding, label_y))
        panel.blit(time_surface, (width - padding - time_surface.get_width(), time_y))

        fill_width = int(bar_width * progress)

        pygame.draw.rect(panel, (3, 7, 9, 92), (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(panel, (*color, 100), (bar_x, bar_y, bar_width, bar_height), max(1, int(self.scale)))

        if fill_width > 0:
            pygame.draw.rect(panel, (*color, 145), (bar_x, bar_y, fill_width, bar_height))
            pygame.draw.line(panel, (245, 255, 245, 58), (bar_x, bar_y + 1), (bar_x + fill_width, bar_y + 1), 1)

        for i in range(1, 6):
            segment_x = bar_x + int(bar_width * i / 6)
            pygame.draw.line(panel, (*color, 42), (segment_x, bar_y + 1), (segment_x, bar_y + bar_height - 2), 1)

        screen.blit(panel, (x, y))

    def draw(self, screen, boss_progress=None, boss_remaining=None):
        self.draw_score(screen)
        self.draw_health(screen)

        if boss_progress is not None and boss_remaining is not None:
            self.draw_boss_progress(screen, boss_progress, boss_remaining)