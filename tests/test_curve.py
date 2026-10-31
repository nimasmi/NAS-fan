from nas_fan.config import load_config
from nas_fan.curve import decide_speed, ramp
from nas_fan.models import Reading

CFG = load_config({})


def test_ramp_at_and_below_low_is_the_floor():
    assert ramp(20, 35, 50, 15) == 15
    assert ramp(35, 35, 50, 15) == 15


def test_ramp_at_or_above_high_is_full():
    assert ramp(50, 35, 50, 15) == 100
    assert ramp(70, 35, 50, 15) == 100


def test_ramp_is_linear_between():
    assert ramp(42, 35, 50, 15) == 54
    assert ramp(43, 35, 50, 15) == 60


def test_all_asleep_stops_the_fans():
    speed, reason = decide_speed(
        [Reading("/dev/sda", None, None), Reading("/dev/sdb", None, None)], CFG
    )
    assert (speed, reason) == (0, "all disks asleep")


def test_idle_speed_can_be_a_floor():
    cfg = load_config({"FAN_IDLE_SPEED": "15"})
    speed, _ = decide_speed([Reading("/dev/sda", None, None)], cfg)
    assert speed == 15


def test_cool_awake_disk_uses_the_floor():
    speed, reason = decide_speed([Reading("/dev/sda", 31, None)], CFG)
    assert (speed, reason) == (15, "cool")


def test_ramp_uses_the_hottest_disk():
    speed, reason = decide_speed(
        [Reading("/dev/sda", 31, None), Reading("/dev/sdb", 47, None)], CFG
    )
    assert (speed, reason) == (83, "ramp")


def test_one_asleep_disk_is_not_cold():
    speed, reason = decide_speed(
        [Reading("/dev/sda", None, None), Reading("/dev/sdb", 50, None)], CFG
    )
    assert (speed, reason) == (100, "hot")


def test_everything_unreadable_is_full_speed():
    speed, reason = decide_speed([Reading("/dev/sda", None, "timeout")], CFG)
    assert (speed, reason) == (100, "read failed")


def test_no_disks_is_full_speed():
    speed, reason = decide_speed([], CFG)
    assert (speed, reason) == (100, "no readings")


def test_one_error_does_not_hide_a_reading():
    speed, reason = decide_speed(
        [Reading("/dev/sda", None, "timeout"), Reading("/dev/sdb", 35, None)], CFG
    )
    assert (speed, reason) == (15, "cool")


def test_speed_is_clamped_to_the_range():
    cfg = load_config({"FAN_MIN_SPEED": "100"})
    speed, _ = decide_speed([Reading("/dev/sda", 40, None)], cfg)
    assert speed == 100
