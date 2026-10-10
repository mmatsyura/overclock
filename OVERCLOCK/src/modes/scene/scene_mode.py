from src.modes.sandbox.sandbox_mode import SandboxMode
from src.modes.scene.scene_config import BOSS_COUNTDOWN


class SceneMode(SandboxMode):
    """Future authored/story mode.

    For now it intentionally reuses Sandbox rules so the existing SCENE MODE menu stays playable.
    When story work starts, replace the Sandbox inheritance with level-specific scripts here.
    """

    name = "scene"

    def __init__(self, world_size, level=None):
        super().__init__(world_size, level)
        self.level = level
        self.boss_countdown = BOSS_COUNTDOWN
