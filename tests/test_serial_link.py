import logging
import os
import pty

import pytest

from nas_fan.serial_link import FanLink, LinkError, resolve_port


@pytest.fixture
def pty_pair():
    master, slave = pty.openpty()
    yield os.ttyname(slave), master
    for fd in (master, slave):
        try:
            os.close(fd)
        except OSError:
            pass


def test_send_writes_one_line(pty_pair):
    path, master = pty_pair
    link = FanLink(path, logging.getLogger("test"))
    link.send(38)
    assert os.read(master, 64) == b"38\n"
    assert link.failures == 0


def test_missing_port_raises_with_the_pattern(monkeypatch):
    monkeypatch.setattr("nas_fan.serial_link.glob.glob", lambda pattern: [])
    with pytest.raises(LinkError, match="usb-MicroPython"):
        resolve_port("")


def test_write_failure_counts_and_reopens(pty_pair):
    path, master = pty_pair
    link = FanLink(path, logging.getLogger("test"))
    link.send(10)
    os.close(master)
    with pytest.raises(LinkError):
        link.send(20)
    assert link.failures == 1
