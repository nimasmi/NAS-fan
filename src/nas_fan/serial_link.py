import glob
import logging
import os
import termios

BY_ID = "/dev/serial/by-id/usb-MicroPython*"
FALLBACK = "/dev/ttyACM*"


class LinkError(Exception):
    """The board could not be reached or written to."""


def resolve_port(pinned: str) -> str:
    """Return the pinned port, or the first board that is plugged in."""
    if pinned:
        return pinned
    for pattern in (BY_ID, FALLBACK):
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[0]
    raise LinkError(f"no MicroPython board at {BY_ID}")


class FanLink:
    """One-way serial link: an integer speed and a newline per send."""

    def __init__(self, port: str, logger: logging.Logger):
        self.port = port
        self.logger = logger
        self.failures = 0
        self._fd: int | None = None

    def send(self, speed: int) -> None:
        try:
            if self._fd is None:
                self._fd = _open(self.port)
            os.write(self._fd, f"{speed}\n".encode())
        except OSError as exc:
            self.close()
            self.failures += 1
            raise LinkError(f"write to {self.port} failed: {exc}") from exc
        self.failures = 0

    def close(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None


def _open(path: str) -> int:
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        attrs = termios.tcgetattr(fd)
        attrs[0] = 0
        attrs[1] = 0
        attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        attrs[3] = 0
        attrs[4] = termios.B115200
        attrs[5] = termios.B115200
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
    except termios.error:
        os.close(fd)
        raise
    return fd
