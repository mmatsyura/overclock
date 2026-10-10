import math
import pygame
from pyvidplayer2 import Video
from src.settings import *
from src.ui.menu_action import MenuActionDirector
from src.rendering.cursor import draw_cursor


class MenuBackground:
    def __init__(self, screen_size, scale):
        self.screen_size = pygame.Vector2(screen_size)
        self.scale = scale

        self.video = Video("assets/video/menu_background.mp4", no_audio=True)
        self.video.resize((int(self.screen_size.x), int(self.screen_size.y)))

        self.video_layer = pygame.Surface((int(self.screen_size.x), int(self.screen_size.y))).convert()
        self.blur_size = (max(1, int(self.screen_size.x // 4)), max(1, int(self.screen_size.y // 4)))
        self.blur_small = pygame.Surface(self.blur_size).convert()
        self.blur_layer = pygame.Surface((int(self.screen_size.x), int(self.screen_size.y))).convert()

        self.dark_layer = pygame.Surface((int(self.screen_size.x), int(self.screen_size.y)), pygame.SRCALPHA).convert_alpha()
        self.dark_layer.fill((0, 0, 0, 95))

    def update(self, dt):
        if not self.video.active:
            self.video.restart()
            self.video.play()

    def draw(self, screen):
        self.video_layer.fill((0, 0, 0))

        self.video.draw(self.video_layer, (0, 0), force_draw=True)

        pygame.transform.smoothscale(self.video_layer, self.blur_size, self.blur_small)
        pygame.transform.smoothscale(self.blur_small, (int(self.screen_size.x), int(self.screen_size.y)), self.blur_layer)

        screen.blit(self.blur_layer, (0, 0))
        screen.blit(self.dark_layer, (0, 0))

    def close(self):
        self.video.close()

class MainMenu:
    PAGE_MAIN = "main"
    PAGE_MODE = "mode"
    PAGE_LEVELS = "levels"
    PAGE_SETTINGS = "settings"

    def __init__(self, screen_size, scale):
        self.screen_size = pygame.Vector2(screen_size)
        self.scale = scale
        self.page = self.PAGE_MAIN
        self.background = MenuBackground(screen_size, scale)

        font_path = "assets/font/Orbitron-Black.ttf"

        self.title_font = pygame.font.Font(font_path, max(44, int(66 * scale)))
        self.button_font = pygame.font.Font(font_path, max(20, int(27 * scale)))
        self.small_font = pygame.font.Font(font_path, max(11, int(14 * scale)))
        self.level_font = pygame.font.Font(font_path, max(22, int(31 * scale)))

        self.mouse_pos = pygame.Vector2()
        self.hovered = None
        self.anim_time = 0.0

        self.hover_anim = {}
        self.press_anim = {}

        self.transition_state = None
        self.transition_time = 0.0
        self.transition_target = None
        self.transition_result = None
        self.transition_direction = 1

        self.transition_out_time = 0.16
        self.transition_in_time = 0.24

        self.page_layer = pygame.Surface((int(self.screen_size.x), int(self.screen_size.y)), pygame.SRCALPHA).convert_alpha()

        self.cyan = (105, 225, 255)
        self.cyan_core = (205, 245, 255)

        self.purple = (146, 102, 255)
        self.purple_core = (205, 190, 255)

        self.dark_panel = (12, 10, 32)
        self.text_idle = (205, 200, 235)

    def reset(self):
        self.page = self.PAGE_MAIN
        self.hovered = None
        self.hover_anim.clear()
        self.press_anim.clear()

    def activate_cursor(self):
        pygame.mouse.set_visible(False)

    def deactivate_cursor(self):
        pygame.mouse.set_visible(True)

    @staticmethod
    def clamp01(value):
        return max(0.0, min(1.0, value))

    @staticmethod
    def lerp(a, b, t):
        return a + (b - a) * t

    @staticmethod
    def lerp_color(a, b, t):
        t = max(0.0, min(1.0, t))
        return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

    def ease_out_cubic(self, value):
        value = self.clamp01(value)
        return 1.0 - (1.0 - value) ** 3

    def ease_in_cubic(self, value):
        value = self.clamp01(value)
        return value ** 3

    def start_transition(self, target_page=None, result=None, direction=1):
        if self.transition_state is not None:
            return

        self.transition_state = "out"
        self.transition_time = 0.0
        self.transition_target = target_page
        self.transition_result = result
        self.transition_direction = direction
        self.hovered = None

    def update_transition(self, dt):
        if self.transition_state is None:
            return None

        self.transition_time += dt

        if self.transition_state == "out":
            if self.transition_time < self.transition_out_time:
                return None

            if self.transition_result is not None:
                result = self.transition_result

                self.transition_state = None
                self.transition_time = 0.0
                self.transition_target = None
                self.transition_result = None

                return result

            if self.transition_target is not None:
                self.page = self.transition_target

            self.hover_anim.clear()
            self.press_anim.clear()

            self.transition_state = "in"
            self.transition_time = 0.0

        elif self.transition_state == "in":
            if self.transition_time >= self.transition_in_time:
                self.transition_state = None
                self.transition_time = 0.0
                self.transition_target = None

        return None

    def update(self, dt, events):
        self.anim_time += dt
        self.background.update(dt)
        transition_result = self.update_transition(dt)

        if transition_result is not None:
            return transition_result

        self.mouse_pos = pygame.Vector2(pygame.mouse.get_pos())

        if self.transition_state is not None:
            return None

        buttons = self.get_buttons()
        self.hovered = next((button_id for button_id, rect, _ in buttons if rect.collidepoint(self.mouse_pos)), None)
        active_ids = {button_id for button_id, _, _ in buttons}

        for button_id in active_ids:
            current = self.hover_anim.get(button_id, 0.0)
            target = 1.0 if button_id == self.hovered else 0.0
            speed = 8.5 if target > current else 5.5

            self.hover_anim[button_id] = current + (target - current) * min(1.0, dt * speed)

            press = self.press_anim.get(button_id, 0.0)
            self.press_anim[button_id] = max(0.0, press - dt * 5.5)

        for button_id in list(self.hover_anim):
            if button_id not in active_ids:
                self.hover_anim.pop(button_id, None)
                self.press_anim.pop(button_id, None)

        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.page == self.PAGE_MAIN:
                    self.start_transition(result=("quit", None, None), direction=-1)

                elif self.page == self.PAGE_MODE:
                    self.start_transition(self.PAGE_MAIN, direction=-1)

                elif self.page == self.PAGE_LEVELS:
                    self.start_transition(self.PAGE_MODE, direction=-1)

                elif self.page == self.PAGE_SETTINGS:
                    self.start_transition(self.PAGE_MAIN, direction=-1)

                continue

            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue

            for button_id, rect, _ in buttons:
                if not rect.collidepoint(event.pos):
                    continue

                self.press_anim[button_id] = 1.0

                if button_id == "play":
                    self.start_transition(self.PAGE_MODE, direction=1)

                elif button_id == "settings":
                    self.start_transition(self.PAGE_SETTINGS, direction=1)

                elif button_id == "quit":
                    self.start_transition(result=("quit", None, None), direction=-1)

                elif button_id == "story":
                    self.start_transition(self.PAGE_LEVELS, direction=1)

                elif button_id == "sandbox":
                    self.start_transition(result=("start", "sandbox", None), direction=1)

                elif button_id == "back_main":
                    self.start_transition(self.PAGE_MAIN, direction=-1)

                elif button_id == "back_mode":
                    self.start_transition(self.PAGE_MODE, direction=-1)

                elif button_id.startswith("level_"):
                    level = int(button_id.split("_")[1])
                    self.start_transition(result=("start", "story", level), direction=1)

                break

        return None

    def get_transition_visual(self):
        alpha = 255
        offset_x = 0

        if self.transition_state == "out":
            progress = self.clamp01(self.transition_time / self.transition_out_time)
            eased = self.ease_in_cubic(progress)

            alpha = int(255 * (1.0 - progress))
            offset_x = int(-34 * self.scale * eased * self.transition_direction)

        elif self.transition_state == "in":
            progress = self.clamp01(self.transition_time / self.transition_in_time)
            eased = self.ease_out_cubic(progress)

            alpha = int(255 * eased)
            offset_x = int(42 * self.scale * (1.0 - eased) * self.transition_direction)

        return alpha, offset_x

    def draw_current_page(self, surface):
        if self.page == self.PAGE_MAIN:
            self.draw_main(surface)

        elif self.page == self.PAGE_MODE:
            self.draw_mode_select(surface)

        elif self.page == self.PAGE_LEVELS:
            self.draw_level_select(surface)

        elif self.page == self.PAGE_SETTINGS:
            self.draw_settings(surface)

    def draw_transition_flash(self, screen):
        if self.transition_state is None:
            return

        if self.transition_state == "out":
            progress = self.clamp01(self.transition_time / self.transition_out_time)
            strength = math.sin(progress * math.pi)
        else:
            progress = self.clamp01(self.transition_time / self.transition_in_time)
            strength = (1.0 - progress) * 0.75

        if strength <= 0.01:
            return

        cx = int(self.screen_size.x * 0.5)
        y = int(self.screen_size.y * 0.365)

        max_width = int(300 * self.scale)
        width = int(max_width * strength)

        if width <= 1:
            return

        alpha = int(120 * strength)

        pygame.draw.line(screen, (*self.cyan, alpha), (cx - width, y), (cx + width, y), max(1, int(self.scale)))

        core_width = int(width * 0.36)

        pygame.draw.line(screen, (*self.cyan_core, min(255, int(190 * strength))), (cx - core_width, y), (cx + core_width, y), max(1, int(2 * self.scale)))

    def draw(self, screen):
        self.background.draw(screen)
        self.draw_header(screen)
        self.page_layer.fill((0, 0, 0, 0))
        self.draw_current_page(self.page_layer)

        alpha, offset_x = self.get_transition_visual()

        self.page_layer.set_alpha(alpha)
        screen.blit(self.page_layer, (offset_x, 0))
        self.page_layer.set_alpha(255)

        self.draw_transition_flash(screen)

        draw_cursor(screen, pygame.mouse.get_pos(), self.scale)

    def draw_header(self, screen):
        cx = int(self.screen_size.x * 0.5)

        title_y = int(self.screen_size.y * 0.165)

        pulse = 0.5 + 0.5 * math.sin(self.anim_time * 1.75)
        micro = 0.5 + 0.5 * math.sin(self.anim_time * 3.6)

        title = self.title_font.render("OVERCLOCK", True, (218, 240, 255))

        title_glow = self.title_font.render("OVERCLOCK", True, self.cyan)

        title_rect = title.get_rect(center=(cx, title_y))

        glow = pygame.Surface((title_rect.width + 70, title_rect.height + 40), pygame.SRCALPHA)

        glow_title = title_glow.copy()
        glow_title.set_alpha(int(30 + 18 * pulse))

        glow.blit(glow_title, glow_title.get_rect(center=(glow.get_width() // 2, glow.get_height() // 2)))

        glow_big = pygame.transform.smoothscale(glow, (glow.get_width() + 14, glow.get_height() + 10))
        glow_big.set_alpha(65)

        screen.blit(glow_big, glow_big.get_rect(center=title_rect.center))
        screen.blit(title, title_rect)

        side_gap = int(28 * self.scale)
        side_h = int(42 * self.scale)

        left_x = title_rect.left - side_gap
        right_x = title_rect.right + side_gap

        top = title_rect.centery - side_h // 2
        bottom = title_rect.centery + side_h // 2

        pygame.draw.line(screen, (*self.cyan, 130), (left_x, top), (left_x, bottom), max(1, int(2 * self.scale)))
        pygame.draw.line(screen, (*self.cyan, 130), (right_x, top), (right_x, bottom), max(1, int(2 * self.scale)))

        pygame.draw.line(screen, (*self.cyan_core, 80), (left_x + int(4 * self.scale), top + int(6 * self.scale)), (left_x + int(4 * self.scale), bottom - int(6 * self.scale)), 1)
        pygame.draw.line(screen, (*self.cyan_core, 80), (right_x - int(4 * self.scale), top + int(6 * self.scale)), (right_x - int(4 * self.scale), bottom - int(6 * self.scale)), 1)

        line_y = title_rect.bottom + int(22 * self.scale)
        line_half = int(320 * self.scale)

        line_surface = pygame.Surface((line_half * 2 + 20, 12), pygame.SRCALPHA)

        center_local = line_surface.get_width() // 2

        pygame.draw.line(line_surface, (*self.cyan, 50), (10, 6), (line_surface.get_width() - 10, 6), 1)

        bright_half = int((145 + 40 * pulse) * self.scale)

        pygame.draw.line(line_surface, (*self.cyan, 115), (center_local - bright_half, 6), (center_local + bright_half, 6), 1)

        diamond_size = max(3, int(4 * self.scale))

        diamond = [
            (center_local, 6 - diamond_size),
            (center_local + diamond_size, 6),
            (center_local, 6 + diamond_size),
            (center_local - diamond_size, 6),
        ]

        pygame.draw.polygon(line_surface, (*self.cyan_core, 220), diamond)

        screen.blit(line_surface, (cx - line_surface.get_width() // 2, line_y))

        subtitle = self.small_font.render("SURVIVE  //  ADAPT  //  OVERCLOCK", True, (135, 175, 215))
        subtitle.set_alpha(180)

        subtitle_y = line_y + int(30 * self.scale)

        screen.blit(subtitle, subtitle.get_rect(center=(cx, subtitle_y)))

        spark_alpha = int(40 + 35 * micro)

        spark_y = line_y + 6
        pygame.draw.circle(screen, (*self.cyan_core, spark_alpha), (cx - int(245 * self.scale), spark_y), max(1, int(self.scale)))
        pygame.draw.circle(screen, (*self.cyan_core, spark_alpha), (cx + int(250 * self.scale), spark_y), max(1, int(self.scale)))

    def draw_main(self, screen):
        for button_id, rect, label in self.get_buttons():
            self.draw_button(screen, rect, label, button_id)

    def draw_mode_select(self, screen):
        label = self.small_font.render("SELECT MODE", True, (155, 180, 218))
        label.set_alpha(180)

        screen.blit(label, label.get_rect(center=(self.screen_size.x * 0.5, self.screen_size.y * 0.365)))

        for button_id, rect, text in self.get_buttons():
            self.draw_button(screen, rect, text, button_id)

    def draw_level_select(self, screen):
        label = self.small_font.render("SCENE MODE  //  SELECT LEVEL", True, (155, 180, 218))
        label.set_alpha(180)

        screen.blit(label, label.get_rect(center=(self.screen_size.x * 0.5, self.screen_size.y * 0.345)))

        for button_id, rect, text in self.get_buttons():
            if button_id.startswith("level_"):
                self.draw_level_button(screen, rect, text, button_id)
            else:
                self.draw_button(screen, rect, text, button_id)

    def draw_settings(self, screen):
        label = self.button_font.render("SETTINGS", True, self.cyan_core)

        screen.blit(label, label.get_rect(center=(self.screen_size.x * 0.5, self.screen_size.y * 0.40)))

        info = self.small_font.render("AUDIO  //  DISPLAY  //  GAMEPLAY", True, (135, 155, 205))
        info.set_alpha(170)

        screen.blit(info, info.get_rect(center=(self.screen_size.x * 0.5, self.screen_size.y * 0.455)))

        for button_id, rect, text in self.get_buttons():
            self.draw_button(screen, rect, text, button_id)

    def get_buttons(self):
        cx = int(self.screen_size.x * 0.5)
        sy = self.screen_size.y

        normal_w = int(540 * self.scale)
        normal_h = int(82 * self.scale)
        gap = int(22 * self.scale)

        if self.page == self.PAGE_MAIN:
            start_y = int(sy * 0.385)

            labels = [
                ("play", "PLAY"),
                ("settings", "SETTINGS"),
                ("quit", "QUIT"),
            ]

            return [
                (
                    button_id,
                    pygame.Rect(
                        cx - normal_w // 2,
                        start_y + i * (normal_h + gap),
                        normal_w,
                        normal_h,
                    ),
                    label,
                )
                for i, (button_id, label) in enumerate(labels)
            ]

        if self.page == self.PAGE_MODE:
            start_y = int(sy * 0.43)

            buttons = [
                ("story", pygame.Rect(cx - normal_w // 2, start_y, normal_w, normal_h), "SCENE MODE"),
                ("sandbox", pygame.Rect(cx - normal_w // 2, start_y + normal_h + gap, normal_w, normal_h), "SANDBOX"),
            ]

            back_y = start_y + (normal_h + gap) * 2 + int(42 * self.scale)

            buttons.append(("back_main", pygame.Rect(cx - normal_w // 2, back_y, normal_w, normal_h), "BACK"))

            return buttons

        if self.page == self.PAGE_LEVELS:
            level_w = int(118 * self.scale)
            level_h = int(76 * self.scale)
            level_gap = int(16 * self.scale)

            cols = 5

            total_w = cols * level_w + (cols - 1) * level_gap

            start_x = cx - total_w // 2
            start_y = int(sy * 0.42)

            buttons = []

            for level in range(1, 11):
                index = level - 1
                row = index // cols
                col = index % cols

                rect = pygame.Rect(
                    start_x + col * (level_w + level_gap),
                    start_y + row * (level_h + level_gap),
                    level_w,
                    level_h,
                )

                buttons.append((f"level_{level}", rect, f"{level:02d}"))

            back_y = start_y + 2 * (level_h + level_gap) + int(36 * self.scale)

            buttons.append(
                (
                    "back_mode",
                    pygame.Rect(cx - normal_w // 2, back_y, normal_w, normal_h),
                    "BACK",
                )
            )

            return buttons

        if self.page == self.PAGE_SETTINGS:
            y = int(sy * 0.56)

            return [
                (
                    "back_main",
                    pygame.Rect(cx - normal_w // 2, y, normal_w, normal_h),
                    "BACK",
                )
            ]

        return []

    def chamfer_points(self, width, height, cut):
        return [
            (cut, 0),
            (width - cut, 0),
            (width, cut),
            (width, height - cut),
            (width - cut, height),
            (cut, height),
            (0, height - cut),
            (0, cut),
        ]

    def draw_button(self, screen, rect, text, button_id):
        hover = self.hover_anim.get(button_id, 0.0)
        press = self.press_anim.get(button_id, 0.0)

        idle_color = self.purple
        active_color = self.cyan

        color = self.lerp_color(idle_color, active_color, hover)

        text_color = self.lerp_color(self.purple_core, self.cyan_core, hover)

        pulse = 0.5 + 0.5 * math.sin(self.anim_time * 3.0 + rect.y * 0.011)

        width = rect.width
        height = rect.height

        cut = max(10, int(14 * self.scale))

        offset_y = int(2 * self.scale * press)

        draw_rect = rect.move(0, offset_y)

        extra = int(36 * self.scale)

        layer = pygame.Surface((width + extra * 2, height + extra * 2), pygame.SRCALPHA)

        ox = extra
        oy = extra

        points = [(x + ox, y + oy) for x, y in self.chamfer_points(width, height, cut)]

        glow_alpha = int(10 + hover * 55)
        glow_width = max(2, int((5 + hover * 5) * self.scale))

        for spread, alpha in (
            (12, int(glow_alpha * 0.24)),
            (7, int(glow_alpha * 0.42)),
            (3, int(glow_alpha * 0.72)),
        ):
            glow_points = []

            for x, y in self.chamfer_points(width, height, cut):
                nx = x

                if x < width * 0.5:
                    nx -= spread
                else:
                    nx += spread

                ny = y

                if y < height * 0.5:
                    ny -= spread * 0.35
                else:
                    ny += spread * 0.35

                glow_points.append((int(nx + ox), int(ny + oy)))

            pygame.draw.lines(layer, (*color, alpha), True, glow_points, glow_width)

        fill_alpha = int(90 + hover * 55)
        pygame.draw.polygon(layer, (8, 8, 30, fill_alpha), points)
        border_alpha = int(125 + 100 * hover)
        pygame.draw.lines(layer, (*color, border_alpha), True, points, max(1, int(2 * self.scale)))
        highlight_width = int(width * (0.22 + 0.18 * hover))

        hx1 = ox + width // 2 - highlight_width // 2
        hx2 = ox + width // 2 + highlight_width // 2

        pygame.draw.line(layer, (*color, int(70 + 130 * hover)), (hx1, oy), (hx2, oy), max(1, int(2 * self.scale)))
        bottom_alpha = int(30 + 70 * hover)

        pygame.draw.line(
            layer,
            (*color, bottom_alpha),
            (ox + cut + int(18 * self.scale), oy + height - 1),
            (ox + width - cut - int(18 * self.scale), oy + height - 1),
            max(1, int(self.scale)),
        )

        side_len = int((18 + 16 * hover) * self.scale)
        side_gap = int(18 * self.scale)

        cy = oy + height // 2

        side_alpha = int(55 + 160 * hover)

        pygame.draw.line(
            layer,
            (*color, side_alpha),
            (ox - side_gap - side_len, cy),
            (ox - side_gap, cy),
            max(1, int(2 * self.scale)),
        )

        pygame.draw.line(
            layer,
            (*color, side_alpha),
            (ox + width + side_gap, cy),
            (ox + width + side_gap + side_len, cy),
            max(1, int(2 * self.scale)),
        )

        label = self.button_font.render(text, True, text_color)

        label_alpha = int(190 + 65 * hover)

        label.set_alpha(label_alpha)

        if hover > 0.0:
            label_glow = self.button_font.render(text, True, active_color)
            label_glow.set_alpha(int(38 * hover + 10 * pulse * hover))

            glow_rect = label_glow.get_rect(center=(ox + width // 2, oy + height // 2))

            layer.blit(label_glow, glow_rect.move(-1, 0))
            layer.blit(label_glow, glow_rect.move(1, 0))

        label_rect = label.get_rect(center=(ox + width // 2, oy + height // 2))

        layer.blit(label, label_rect)

        screen.blit(layer, (draw_rect.x - extra, draw_rect.y - extra))

    def draw_level_button(self, screen, rect, text, button_id):
        hover = self.hover_anim.get(button_id, 0.0)

        color = self.lerp_color(self.purple, self.cyan, hover)

        panel = pygame.Surface(rect.size, pygame.SRCALPHA)

        cut = max(7, int(10 * self.scale))

        points = self.chamfer_points(rect.width - 1, rect.height - 1, cut)

        pygame.draw.polygon(panel, (8, 7, 28, int(105 + 30 * hover)), points)

        pygame.draw.lines(panel, (*color, int(130 + 100 * hover)), True, points, max(1, int(2 * self.scale)))

        small = self.small_font.render("LEVEL", True, self.lerp_color((125, 115, 175), self.cyan, hover))
        number = self.level_font.render(text, True, self.lerp_color(self.purple_core, self.cyan_core, hover))

        small.set_alpha(int(150 + 80 * hover))
        number.set_alpha(int(190 + 65 * hover))

        panel.blit(small, small.get_rect(center=(rect.width // 2, int(rect.height * 0.28))))
        panel.blit(number, number.get_rect(center=(rect.width // 2, int(rect.height * 0.66))))

        screen.blit(panel, rect)