class TimeController:
    def __init__(self):
        self.mode = None
        self.timer = 0.0
        self.hit_stop = 0.0
        self.duration = 0.27
        self.hold_duration = 0.12
        self.min_scale = 0.18
        self.recovery_timer = 0.0
        self.recovery_duration = 0.26
        self.recovery_start_scale = 0.14

    def trigger_kill(self):
        if self.mode in ("player_death", "player_death_recovery"):
            return

        self.mode = "kill"
        self.hit_stop = max(self.hit_stop, 0.045)
        self.duration = 0.27
        self.hold_duration = 0.12
        self.min_scale = 0.18
        self.timer = self.duration

    def trigger_player_death(self):
        self.mode = "player_death"
        self.hit_stop = 0.045
        self.min_scale = 0.14
        self.timer = 0.0
        self.recovery_timer = 0.0
        self.recovery_start_scale = self.min_scale

    def update(self, dt):
        if self.hit_stop > 0:
            self.hit_stop = max(0.0, self.hit_stop - dt)

            if self.mode == "player_death":
                return dt * 0.035

            return dt * 0.04

        if self.mode == "player_death":
            return dt * self.min_scale

        if self.mode == "player_death_recovery":
            self.recovery_timer += dt
            progress = max(0.0, min(1.0, self.recovery_timer / self.recovery_duration))
            smooth = progress * progress * (3.0 - 2.0 * progress)
            scale = self.recovery_start_scale + (1.0 - self.recovery_start_scale) * smooth

            if progress >= 1.0:
                self.mode = None
                return dt

            return dt * scale

        if self.timer <= 0:
            self.mode = None
            return dt

        elapsed = self.duration - self.timer
        self.timer = max(0.0, self.timer - dt)

        if elapsed < self.hold_duration:
            return dt * self.min_scale

        recovery_duration = self.duration - self.hold_duration
        recovery = (elapsed - self.hold_duration) / recovery_duration
        smooth = self.smoothstep(recovery)
        scale = self.min_scale + (1.0 - self.min_scale) * smooth

        return dt * scale

    def finish_player_death(self):
        if self.mode == "player_death":
            self.mode = "player_death_recovery"
            self.recovery_timer = 0.0
            self.recovery_start_scale = self.min_scale

    @staticmethod
    def smoothstep(value):
        value = max(0.0, min(1.0, value))
        return value * value * (3.0 - 2.0 * value)