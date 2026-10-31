import subprocess
import time
from collections.abc import Callable


class Alerter:
    """Post an alert, at most once per key per interval."""

    def __init__(
        self,
        cmd: str,
        min_interval: int,
        now: Callable[[], float] = time.monotonic,
        run: Callable[..., object] = subprocess.run,
    ):
        self.cmd = cmd
        self.min_interval = min_interval
        self.now = now
        self.run = run
        self._last: dict[str, float] = {}

    def notify(self, key: str, message: str, priority: int = 4) -> bool:
        moment = self.now()
        last = self._last.get(key)
        throttled = (
            self.min_interval > 0
            and last is not None
            and moment - last < self.min_interval
        )
        if throttled:
            return False
        self._last[key] = moment
        try:
            self.run(
                [self.cmd, message, str(priority)], check=True, capture_output=True
            )
        except (OSError, subprocess.CalledProcessError):
            return False
        return True
