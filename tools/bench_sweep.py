"""Send a list of speeds to the board, one at a time, for a bench check."""

import argparse
import glob
import os
import sys
import termios
import time

BY_ID = "/dev/serial/by-id/usb-MicroPython*"
FALLBACK = "/dev/ttyACM*"


def resolve_port(pinned: str) -> str:
    if pinned:
        return pinned
    for pattern in (BY_ID, FALLBACK):
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[0]
    raise SystemExit(f"no MicroPython board at {BY_ID}")


def open_port(path: str) -> int:
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    attrs = termios.tcgetattr(fd)
    attrs[0] = 0
    attrs[1] = 0
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    attrs[3] = 0
    attrs[4] = termios.B115200
    attrs[5] = termios.B115200
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    return fd


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="", help="serial port, default autodetect")
    parser.add_argument(
        "--pause", type=float, default=5.0, help="seconds between speeds"
    )
    parser.add_argument("speeds", nargs="+", type=int, metavar="SPEED")
    args = parser.parse_args()

    path = resolve_port(args.port)
    fd = open_port(path)
    print(f"port {path}")
    try:
        for speed in args.speeds:
            print(f"speed {speed}%", flush=True)
            os.write(fd, f"{speed}\n".encode())
            time.sleep(args.pause)
    finally:
        os.close(fd)
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
