from pathlib import Path

from nas_fan.config import load_config
from nas_fan.temps import discover_drives, is_asleep, parse_temperature

FIXTURES = Path(__file__).parent / "fixtures"


def test_standby_output_means_asleep_even_with_exit_zero():
    assert is_asleep(0, "Device is in STANDBY mode, exit(2)") is True


def test_exit_code_two_without_a_marker_is_not_asleep():
    # Exit 2 also means "device open failed", so the text must say so.
    assert (
        is_asleep(2, "Smartctl open device: /dev/sda failed: Permission denied")
        is False
    )
    assert is_asleep(2, "") is False


def test_sleep_output_means_asleep():
    assert is_asleep(0, "Power mode is: SLEEP") is True


def test_standby_in_the_output_means_asleep():
    out = (FIXTURES / "smartctl_standby.txt").read_text()
    assert is_asleep(0, out) is True


def test_idle_b_and_idle_c_mean_asleep():
    assert is_asleep(0, "Power mode is: IDLE_B") is True
    assert is_asleep(0, "Power mode is: IDLE_C") is True


def test_active_disk_is_awake():
    out = (FIXTURES / "smartctl_awake.txt").read_text()
    assert is_asleep(0, out) is False


def test_temperature_is_parsed():
    out = (FIXTURES / "smartctl_awake.txt").read_text()
    assert parse_temperature(out) == 38


def test_missing_temperature_gives_none():
    out = (FIXTURES / "smartctl_no_temp.txt").read_text()
    assert parse_temperature(out) is None


def test_discovery_override_wins():
    cfg = load_config({"FAN_DRIVES": "/dev/sdx,/dev/sdy"})
    assert discover_drives(cfg) == ["/dev/sdx", "/dev/sdy"]


def test_a_hanging_smartctl_times_out(monkeypatch):
    import subprocess

    from nas_fan import temps

    def hang(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="smartctl", timeout=1)

    monkeypatch.setattr(temps.subprocess, "run", hang)
    reading = temps.read_drive("/dev/sda", timeout=1)
    assert reading.temp is None
    assert reading.error == "timeout"


def test_nvme_temperature_is_parsed():
    out = (FIXTURES / "smartctl_nvme_awake.txt").read_text()
    assert parse_temperature(out) == 45


def test_discovery_reads_only_spinning_disks(monkeypatch):
    from nas_fan import temps

    def glob(pattern):
        return {
            "/dev/sd[a-z]": ["/dev/sda", "/dev/sdb"],
            "/dev/nvme[0-9]n[0-9]": ["/dev/nvme0n1"],
        }.get(pattern, [])

    monkeypatch.setattr(temps.glob, "glob", glob)
    monkeypatch.setattr(temps, "_is_block_device", lambda path: True)
    monkeypatch.setattr(temps, "_is_rotational", lambda path: path == "/dev/sdb")
    assert temps.discover_drives(load_config({})) == ["/dev/sdb"]
