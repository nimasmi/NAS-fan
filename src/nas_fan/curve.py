from collections.abc import Sequence

from nas_fan.config import Config
from nas_fan.models import Reading


def ramp(temp: int, low: int, high: int, min_speed: int) -> int:
    """Map a temperature to a speed between the floor and 100 %."""
    if temp <= low:
        return min_speed
    if temp >= high:
        return 100
    speed = min_speed + (temp - low) * (100 - min_speed) / (high - low)
    return max(0, min(100, int(speed)))


def decide_speed(readings: Sequence[Reading], cfg: Config) -> tuple[int, str]:
    """Return the speed for these readings and a short reason for the log."""
    if not readings:
        return 100, "no readings"

    temps = [r.temp for r in readings if r.temp is not None]
    if not temps:
        if any(r.error for r in readings):
            return 100, "read failed"
        return cfg.idle_speed, "all disks asleep"

    hottest = max(temps)
    if hottest <= cfg.temp_low:
        return ramp(hottest, cfg.temp_low, cfg.temp_high, cfg.min_speed), "cool"
    if hottest >= cfg.temp_high:
        return 100, "hot"
    return ramp(hottest, cfg.temp_low, cfg.temp_high, cfg.min_speed), "ramp"
