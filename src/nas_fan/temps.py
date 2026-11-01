import glob
import os
import re
import stat
import subprocess
from dataclasses import replace

from nas_fan.config import Config
from nas_fan.models import Reading

SLEEPY = re.compile(r"\b(STANDBY|SLEEP|IDLE_B|IDLE_C)\b")
TEMPERATURE = re.compile(r"^\s*194\s+Temperature_Celsius\b.*?(\d+)\s*$", re.MULTILINE)
NVME_TEMPERATURE = re.compile(r"^\s*Temperature:\s+(\d+)\s+Celsius\b", re.MULTILINE)


def discover_drives(cfg: Config) -> list[str]:
    """Return the disks to read: the override, or the local spinning disks.

    Only rotating disks are discovered. An SSD has no platters to spin down
    and no reason for case airflow, so it must not set the fan speed.
    """
    if cfg.drives:
        return list(cfg.drives)
    candidates = glob.glob("/dev/sd[a-z]")
    return sorted(
        path for path in candidates if _is_block_device(path) and _is_rotational(path)
    )


def _is_rotational(path: str) -> bool:
    name = os.path.basename(path)
    try:
        with open(f"/sys/block/{name}/queue/rotational") as handle:
            return handle.read().strip() == "1"
    except OSError:
        return False


def _is_block_device(path: str) -> bool:
    try:
        return stat.S_ISBLK(os.stat(path).st_mode)
    except OSError:
        return False


def is_asleep(returncode: int, output: str) -> bool:
    """A disk is asleep only when smartctl names a low-power mode.

    Exit code 2 alone is not enough: smartctl uses it for "device open
    failed" too, and a disk that cannot be opened is not asleep.
    """
    return SLEEPY.search(output) is not None


def parse_temperature(output: str) -> int | None:
    """Read the temperature from an ATA attribute table or an NVMe log."""
    match = TEMPERATURE.search(output) or NVME_TEMPERATURE.search(output)
    return int(match.group(1)) if match else None


def read_drive(device: str, timeout: float = 15.0) -> Reading:
    """Read one disk's temperature, without waking it."""
    info = _smartctl(["-i", "-n", "standby", device], timeout)
    if isinstance(info, Reading):
        return info
    if is_asleep(info.returncode, info.stdout):
        return Reading(device, None, None)

    attrs = _smartctl(["-A", device], timeout)
    if isinstance(attrs, Reading):
        return attrs
    temp = parse_temperature(attrs.stdout)
    if temp is None:
        return Reading(device, None, "no temperature")
    return Reading(device, temp, None)


def _smartctl(args: list[str], timeout: float) -> subprocess.CompletedProcess | Reading:
    try:
        return subprocess.run(
            ["smartctl", *args],
            timeout=timeout,
            text=True,
            capture_output=True,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return Reading(args[-1], None, "timeout")
    except OSError as exc:
        return Reading(args[-1], None, str(exc))


def split_drive(entry: str) -> tuple[str, str]:
    """Split a drive entry into a log label and a device path.

    The configuration may say `disk20=/dev/disk/by-id/...`, which keeps the
    log line short. An entry without `=` has no label.
    """
    label, sep, path = entry.partition("=")
    return (label, path) if sep else ("", entry)


def read_all(cfg: Config) -> list[Reading]:
    readings = []
    for entry in discover_drives(cfg):
        label, path = split_drive(entry)
        readings.append(replace(read_drive(path), label=label))
    return readings
