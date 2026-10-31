from nas_fan.config import load_config
from nas_fan.main import format_status, run_cycle
from nas_fan.models import Reading
from nas_fan.serial_link import LinkError

CFG = load_config({})


class FakeLink:
    def __init__(self, failures=0):
        self.failures = failures
        self.sent = []

    def send(self, speed):
        self.sent.append(speed)


class FakeAlerter:
    def __init__(self):
        self.keys = []

    def notify(self, key, message, priority=4):
        self.keys.append(key)
        return True


def test_cycle_sends_the_speed():
    link, alerter = FakeLink(), FakeAlerter()
    speed, reason = run_cycle(
        CFG, link, alerter, read_all_fn=lambda cfg: [Reading("/dev/sda", 42, None)]
    )
    assert (speed, reason) == (54, "ramp")
    assert link.sent == [54]
    assert alerter.keys == []


def test_asleep_disks_send_zero_without_alert():
    link, alerter = FakeLink(), FakeAlerter()
    speed, _ = run_cycle(
        CFG, link, alerter, read_all_fn=lambda cfg: [Reading("/dev/sda", None, None)]
    )
    assert speed == 0
    assert link.sent == [0]
    assert alerter.keys == []


def test_unreadable_disks_alert():
    link, alerter = FakeLink(), FakeAlerter()
    speed, _ = run_cycle(
        CFG, link, alerter, read_all_fn=lambda cfg: [Reading("/dev/sda", None, "x")]
    )
    assert speed == 100
    assert alerter.keys == ["fan-temps"]


def test_serial_failure_alerts_after_three():
    class Failing(FakeLink):
        def send(self, speed):
            self.failures += 1
            raise LinkError("x")

    link, alerter = Failing(), FakeAlerter()
    for _ in range(3):
        run_cycle(
            CFG,
            link,
            alerter,
            read_all_fn=lambda cfg: [Reading("/dev/sda", None, None)],
        )
    assert alerter.keys == ["fan-serial"]


def test_status_line_format():
    line = format_status(
        38,
        "ramp",
        [Reading("/dev/disk20", 39, None), Reading("/dev/disk22", None, None)],
    )
    assert line == 'speed=38% reason="ramp" disk20=39 disk22=asleep'


def test_missing_board_alerts_after_three(monkeypatch):
    import logging

    from nas_fan import main as main_module

    cfg = load_config({})
    keys = []

    class Alerter:
        def __init__(self, *args, **kwargs):
            pass

        def notify(self, key, message, priority=4):
            keys.append(key)
            return True

    def no_board(pinned):
        raise LinkError("no board")

    attempts = {"count": 0}

    def sleep(seconds):
        attempts["count"] += 1
        if attempts["count"] >= 3:
            raise KeyboardInterrupt

    monkeypatch.setattr(main_module, "load_config", lambda: cfg)
    monkeypatch.setattr(
        main_module, "configure_logging", lambda cfg: logging.getLogger("test")
    )
    monkeypatch.setattr(main_module, "Alerter", Alerter)
    monkeypatch.setattr(main_module, "resolve_port", no_board)
    monkeypatch.setattr(main_module.time, "sleep", sleep)

    assert main_module.main() == 0
    assert keys == ["fan-serial"]


def test_status_line_marks_a_failed_read():
    line = format_status(100, "read failed", [Reading("/dev/sda", None, "timeout")])
    assert line == 'speed=100% reason="read failed" sda=error'


def test_a_partly_unreadable_set_of_disks_alerts():
    link, alerter = FakeLink(), FakeAlerter()
    speed, reason = run_cycle(
        CFG,
        link,
        alerter,
        read_all_fn=lambda cfg: [
            Reading("/dev/sda", None, "timeout"),
            Reading("/dev/sdb", 35, None),
        ],
    )
    assert (speed, reason) == (15, "cool")
    assert alerter.keys == ["fan-temps"]


def test_no_disks_at_all_alerts():
    link, alerter = FakeLink(), FakeAlerter()
    speed, _ = run_cycle(CFG, link, alerter, read_all_fn=lambda cfg: [])
    assert speed == 100
    assert alerter.keys == ["fan-temps"]


def test_main_resolves_the_port_again_after_a_disconnect(monkeypatch):
    import logging

    from nas_fan import main as main_module

    cfg = load_config({})
    resolved = []
    cycles = {"count": 0}

    class Link:
        def __init__(self, port, logger):
            self.port = port
            self.failures = 0

        def send(self, speed):
            self.failures += 1
            raise LinkError("gone")

        def close(self):
            pass

    def resolve(pinned):
        resolved.append(pinned)
        return f"/dev/ttyACM{len(resolved) - 1}"

    def sleep(seconds):
        cycles["count"] += 1
        if cycles["count"] >= 5:
            raise KeyboardInterrupt

    monkeypatch.setattr(main_module, "load_config", lambda: cfg)
    monkeypatch.setattr(
        main_module, "configure_logging", lambda cfg: logging.getLogger("test")
    )
    monkeypatch.setattr(main_module, "Alerter", lambda *a, **k: FakeAlerter())
    monkeypatch.setattr(main_module, "FanLink", Link)
    monkeypatch.setattr(main_module, "resolve_port", resolve)
    monkeypatch.setattr(
        main_module, "read_all", lambda cfg: [Reading("/dev/sda", 40, None)]
    )
    monkeypatch.setattr(main_module.time, "sleep", sleep)

    assert main_module.main() == 0
    assert len(resolved) >= 2


def test_a_log_file_without_a_directory_does_not_crash(tmp_path, monkeypatch):
    from nas_fan.main import configure_logging

    monkeypatch.chdir(tmp_path)
    cfg = load_config({"FAN_LOG_FILE": "fan.log"})
    logger = configure_logging(cfg)
    logger.info("hello")
    for handler in logger.handlers:
        handler.close()
    assert (tmp_path / "fan.log").read_text().strip().endswith("hello")
