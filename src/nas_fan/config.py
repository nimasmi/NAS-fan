import os
from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_ALERT_CMD = "/usr/local/bin/notify-nas-alert.sh"
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


@dataclass(frozen=True)
class Config:
    idle_speed: int
    min_speed: int
    temp_low: int
    temp_high: int
    interval: int
    serial_port: str
    drives: tuple[str, ...]
    log_file: str
    log_level: str
    alert_cmd: str
    alert_min_interval: int


def parse_int(name: str, raw: str, low: int, high: int) -> int:
    try:
        value = int(raw)
    except ValueError:
        value = None
    if value is None or not low <= value <= high:
        raise ValueError(
            f"{name} must be an integer between {low} and {high}, got {raw!r}"
        )
    return value


def load_config(env: Mapping[str, str] | None = None) -> Config:
    if env is None:
        env = os.environ

    temp_low = parse_int("FAN_TEMP_LOW", env.get("FAN_TEMP_LOW", "35"), -20, 120)
    temp_high = parse_int("FAN_TEMP_HIGH", env.get("FAN_TEMP_HIGH", "50"), -20, 120)
    if temp_low >= temp_high:
        raise ValueError(
            f"FAN_TEMP_LOW must be below FAN_TEMP_HIGH, got {temp_low} and {temp_high}"
        )

    log_level = env.get("FAN_LOG_LEVEL", "INFO").strip().upper()
    if log_level not in LOG_LEVELS:
        raise ValueError(
            f"FAN_LOG_LEVEL must be one of {', '.join(LOG_LEVELS)}, got {log_level!r}"
        )

    drives = tuple(d.strip() for d in env.get("FAN_DRIVES", "").split(",") if d.strip())
    return Config(
        idle_speed=parse_int("FAN_IDLE_SPEED", env.get("FAN_IDLE_SPEED", "0"), 0, 100),
        min_speed=parse_int("FAN_MIN_SPEED", env.get("FAN_MIN_SPEED", "15"), 0, 100),
        temp_low=temp_low,
        temp_high=temp_high,
        interval=parse_int(
            "FAN_CHECK_INTERVAL", env.get("FAN_CHECK_INTERVAL", "30"), 1, 86400
        ),
        serial_port=env.get("FAN_SERIAL_PORT", "").strip(),
        drives=drives,
        log_file=env.get("FAN_LOG_FILE", "").strip(),
        log_level=log_level,
        alert_cmd=env.get("FAN_ALERT_CMD", DEFAULT_ALERT_CMD),
        alert_min_interval=parse_int(
            "FAN_ALERT_MIN_INTERVAL",
            env.get("FAN_ALERT_MIN_INTERVAL", "1800"),
            0,
            86400,
        ),
    )
