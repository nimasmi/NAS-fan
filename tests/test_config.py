import pytest

from nas_fan.config import load_config


def test_defaults():
    cfg = load_config({})
    assert cfg.idle_speed == 0
    assert cfg.min_speed == 15
    assert cfg.temp_low == 35
    assert cfg.temp_high == 50
    assert cfg.interval == 30
    assert cfg.serial_port == ""
    assert cfg.drives == ()
    assert cfg.log_file == ""
    assert cfg.log_level == "INFO"
    assert cfg.alert_cmd == "/usr/local/bin/notify-nas-alert.sh"
    assert cfg.alert_min_interval == 1800


def test_overrides():
    cfg = load_config(
        {
            "FAN_IDLE_SPEED": "15",
            "FAN_TEMP_HIGH": "48",
            "FAN_DRIVES": "/dev/sda, /dev/sdb",
            "FAN_LOG_LEVEL": "debug",
        }
    )
    assert cfg.idle_speed == 15
    assert cfg.temp_high == 48
    assert cfg.drives == ("/dev/sda", "/dev/sdb")
    assert cfg.log_level == "DEBUG"


@pytest.mark.parametrize(
    "name, value",
    [
        ("FAN_IDLE_SPEED", " "),
        ("FAN_IDLE_SPEED", "fast"),
        ("FAN_IDLE_SPEED", "101"),
        ("FAN_MIN_SPEED", "-1"),
        ("FAN_CHECK_INTERVAL", "0"),
        ("FAN_ALERT_MIN_INTERVAL", "-5"),
    ],
)
def test_invalid_int_is_rejected(name, value):
    with pytest.raises(ValueError, match=name):
        load_config({name: value})


def test_low_must_be_below_high():
    with pytest.raises(ValueError, match="FAN_TEMP_LOW"):
        load_config({"FAN_TEMP_LOW": "50", "FAN_TEMP_HIGH": "50"})


def test_unknown_log_level_is_rejected():
    with pytest.raises(ValueError, match="FAN_LOG_LEVEL"):
        load_config({"FAN_LOG_LEVEL": "LOUD"})
