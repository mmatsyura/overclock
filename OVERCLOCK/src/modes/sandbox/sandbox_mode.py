from src.modes.base_mode import GameMode
from src.modes.sandbox.sandbox_config import BOSS_COUNTDOWN
from src.modes.sandbox.sandbox_spawner import SandboxSpawner


class SandboxMode(GameMode):
    name = "sandbox"

    def __init__(self, world_size, level=None):
        super().__init__(world_size, level)
        self.elapsed_time = 0.0
        self.boss_countdown = BOSS_COUNTDOWN
        self.spawner = SandboxSpawner(world_size)

    def on_start(self, game):
        super().on_start(game)
        self.elapsed_time = 0.0
        game.walls.generate(game.player.pos)

    def update(self, dt, game):
        self.elapsed_time += dt

        if game.player_alive:
            self.spawner.update(dt, game.enemies, game.player.pos, game.walls)