from dataclasses import dataclass


@dataclass(frozen=True)
class Reading:
    """One disk's temperature, or why it could not be read.

    A temp of None with no error means the disk is asleep. `label` is the
    short name for log lines, when the configuration gives one.
    """

    device: str
    temp: int | None
    error: str | None
    label: str = ""
