from nas_fan.alerts import Alerter


class Clock:
    def __init__(self):
        self.value = 1000.0

    def __call__(self):
        return self.value


def test_first_alert_runs_the_command():
    calls = []
    alerter = Alerter(
        "/bin/true", 1800, now=Clock(), run=lambda *a, **k: calls.append(a)
    )
    assert alerter.notify("serial", "serial write failed", 4) is True
    assert calls == [(["/bin/true", "serial write failed", "4"],)]


def test_repeat_is_throttled_per_key():
    clock = Clock()
    alerter = Alerter("/bin/true", 1800, now=clock, run=lambda *a, **k: None)
    assert alerter.notify("serial", "first", 4) is True
    assert alerter.notify("serial", "second", 4) is False
    clock.value += 1801
    assert alerter.notify("serial", "third", 4) is True


def test_different_keys_do_not_throttle_each_other():
    alerter = Alerter("/bin/true", 1800, now=Clock(), run=lambda *a, **k: None)
    assert alerter.notify("serial", "a", 4) is True
    assert alerter.notify("temps", "b", 4) is True


def test_command_failure_is_reported_not_raised():
    def boom(*args, **kwargs):
        raise OSError("no curl")

    alerter = Alerter("/bin/false", 0, now=Clock(), run=boom)
    assert alerter.notify("serial", "a", 4) is False
