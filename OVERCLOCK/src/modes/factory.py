from src.modes.sandbox.sandbox_mode import SandboxMode
from src.modes.scene.scene_mode import SceneMode


def create_mode(mode_name, world_size, level=None):
    if mode_name == "sandbox":
        return SandboxMode(world_size, level)

    if mode_name in ("story", "scene"):
        return SceneMode(world_size, level)

    raise ValueError(f"Unknown game mode: {mode_name}")
