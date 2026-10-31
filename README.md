# NAS fan controller

This project drives one or more 120 mm case fans from a Raspberry Pi Pico. The
fan speed follows the hottest disk that is awake. When every disk is asleep,
the fans stop.

The Pico receives one integer per line over USB serial. It waintains a PWM
signal at 25 kHz, and forces 100 % if the input stops talking. A Python service
on the host server reads disk temperatures with `smartctl -n standby`, so a
read never wakes a sleeping disk.

## Wiring

- The fans stay on the two 3-pin headers for 12 V and GND. Their
  PWM pins come off the headers and go to the Pico.
- The Pico is grounded to the main negative terminal as well as through
  USB.
- GPIO 0 goes through a 220 ohm resistor to the PWM pin of both fans.
- The full fan pin order, taken from the 4-pin socket, is GND, 12 V,
  TACH, PWM.

A 4-pin fan stops when the PWM duty reaches 0 %, because 12 V stays on.
Fans can stall below roughly 15 %, so the firmware clamps a small non-zero
speed up to 15 %.

## Settings

The service reads environment variables. Defaults live in
`src/nas_fan/config.py`.


| Variable | Default | Meaning |
| --- | --- | --- |
| `FAN_IDLE_SPEED` | `0` | Speed when every disk is asleep; `0` stops the fans |
| `FAN_MIN_SPEED` | `15` | Floor while a disk is awake |
| `FAN_TEMP_LOW` | `35` | At or below this °C, speed is `FAN_MIN_SPEED` |
| `FAN_TEMP_HIGH` | `50` | At or above this °C, speed is 100 % |
| `FAN_CHECK_INTERVAL` | `30` | Seconds between readings |
| `FAN_SERIAL_PORT` | empty | Empty: detect `/dev/serial/by-id/usb-MicroPython*` |
| `FAN_DRIVES` | empty | Empty: discover; else a comma-separated list |
| `FAN_LOG_FILE` | empty | Empty: log to stdout and journald |
| `FAN_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, or `ERROR` |
| `FAN_ALERT_CMD` | `/usr/local/bin/notify-nas-alert.sh` | Alert hook |
| `FAN_ALERT_MIN_INTERVAL` | `1800` | Seconds between repeated alerts |


An unparseable or out-of-range value stops the service at startup with a
clear error. If the service is stopped, the fan spins at 100% speed.

## Deploy the firmware

Copy the two files to the board, then reset it:

```bash
mpremote fs cp firmware/config.py firmware/main.py :
mpremote soft-reset
```

The Pico starts at 50 %, then waits for the first speed. If 60 seconds
pass with no line, it goes to 100 % and the LED blinks slowly. The board
LED is steady on when the board is ready, and it blinks off for a moment
when a line arrives. This build uses the single-colour board LED of a Pico
W, which MicroPython reaches as `machine.Pin("LED")`.

## Bench sweep

Send a series of speeds and listen to the fans:

```bash
python3 tools/bench_sweep.py 0 15 30 50 75 100
```

The tool pauses 5 seconds between speeds. Use `--port` to name the serial
port and `--pause` to change the pause.

## Tests

The speed code is pure and the disk and serial layers are faked, so the
suite needs no hardware:

```bash
uv run pytest
```

## Credit

The original project is
[corey-schneider/NAS-fan](https://github.com/corey-schneider/NAS-fan).
This fork rewrites the controller and the firmware for this build. The original
repository has no licence.

Disclaimer: a LLM was used to modify the project, so the state of documentation
is extensive but characteristically robotic.
