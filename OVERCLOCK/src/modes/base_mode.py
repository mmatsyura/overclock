class GameMode:
    """Small interface for mode-specific rules. Core gameplay stays in src/app.py and shared systems."""

    name = "base"

    def __init__(self, world_size, level=None):
        self.world_size = world_size
        self.level = level
        self.boss_countdown = 90.0
        self.boss_elapsed = 0.0

    def on_start(self, game):
        self.boss_elapsed = 0.0

    def update(self, dt, game):
        pass

    def update_interface(self, real_dt, game):
        if game.player_alive and self.boss_elapsed < self.boss_countdown:
            self.boss_elapsed = min(self.boss_countdown, self.boss_elapsed + real_dt)

    def get_boss_progress(self):
        if self.boss_countdown <= 0.0:
            return 1.0
        return max(0.0, min(1.0, self.boss_elapsed / self.boss_countdown))

    def get_boss_remaining(self):
        return max(0.0, self.boss_countdown - self.boss_elapsed)

    def on_player_death(self, game):
        pass
