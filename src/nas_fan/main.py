import logging
import os
import signal
import sys
import time
from collections.abc import Callable, Sequence
from logging.handlers import RotatingFileHandler

from nas_fan.alerts import Alerter
from nas_fan.config import Config, load_config
from nas_fan.curve import decide_speed
from nas_fan.models import Reading
from nas_fan.serial_link import FanLink, LinkError, resolve_port
from nas_fan.temps import read_all

logger = logging.getLogger("nas_fan")
SERIAL_ALERT_AFTER = 3


def name_of(reading: Reading) -> str:
    """The short name of a disk for log lines and alerts."""
    return reading.label or os.path.basename(reading.device)


def format_status(speed: int, reason: str, readings: Sequence[Reading]) -> str:
    def state(reading: Reading) -> str:
        if reading.temp is not None:
            return str(reading.temp)
        return "error" if reading.error else "asleep"

    disks = " ".join(f"{name_of(r)}={state(r)}" for r in readings)
    return f'speed={speed}% reason="{reason}" {disks}'.rstrip()


def run_cycle(
    cfg: Config,
    link: FanLink,
    alerter: Alerter,
    read_all_fn: Callable[[Config], list[Reading]] = read_all,
) -> tuple[int, str]:
    readings = read_all_fn(cfg)
    speed, reason = decide_speed(readings, cfg)

    try:
        link.send(speed)
    except LinkError as exc:
        if link.failures >= SERIAL_ALERT_AFTER:
            alerter.notify(
                "fan-serial",
                f"fan controller cannot reach the board: {exc}",
            )

    failed = [name_of(r) for r in readings if r.error]
    if failed or not readings:
        detail = ", ".join(failed) if failed else "no disks found"
        alerter.notify(
            "fan-temps",
            f"fan controller cannot read disk temperatures: {detail}",
        )

    logger.info(format_status(speed, reason, readings))
    return speed, reason


def configure_logging(cfg: Config) -> logging.Logger:
    logger.setLevel(cfg.log_level)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    if cfg.log_file:
        if directory := os.path.dirname(cfg.log_file):
            os.makedirs(directory, exist_ok=True)
        files = RotatingFileHandler(cfg.log_file, maxBytes=1024 * 1024, backupCount=2)
        files.setFormatter(formatter)
        logger.addHandler(files)

    return logger


def _stop(signum: int, frame: object) -> None:
    raise KeyboardInterrupt


def main() -> int:
    try:
        cfg = load_config()
    except ValueError as exc:
        print(f"fan-control: {exc}", file=sys.stderr)
        return 2

    logger = configure_logging(cfg)
    alerter = Alerter(cfg.alert_cmd, cfg.alert_min_interval)
    signal.signal(signal.SIGTERM, _stop)
    link: FanLink | None = None
    missing_logged = False
    missing = 0

    try:
        while True:
            if link is None:
                try:
                    link = FanLink(resolve_port(cfg.serial_port), logger)
                except LinkError as exc:
                    missing += 1
                    if not missing_logged:
                        logger.warning("waiting for the board: %s", exc)
                        missing_logged = True
                    if missing >= SERIAL_ALERT_AFTER:
                        alerter.notify(
                            "fan-serial",
                            f"fan controller cannot find the board: {exc}",
                        )
                else:
                    missing = 0
            if link is not None:
                run_cycle(cfg, link, alerter)
                if link.failures >= SERIAL_ALERT_AFTER:
                    # The board may come back on a different port.
                    link.close()
                    link = None
            time.sleep(cfg.interval)
    except KeyboardInterrupt:
        logger.info("fan controller stopping")
    finally:
        if link is not None:
            link.close()

    return 0
