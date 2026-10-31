import select
import sys
import time

import config
import machine

led = machine.Pin(config.LED_PIN, machine.Pin.OUT)
fan = machine.PWM(machine.Pin(config.FAN_PIN))
fan.freq(config.PWM_HZ)


def set_speed(percent):
    percent = max(0, min(100, percent))
    if 0 < percent < config.STALL_FLOOR:
        percent = config.STALL_FLOOR
    duty = percent if not config.PWM_INVERTED else 100 - percent
    fan.duty_u16(duty * 65535 // 100)


def set_led(on):
    led.value(1 if on else 0)


# The LED states: steady on means ready, a short off blink means a line
# arrived, and a slow blink means the watchdog tripped.
set_led(True)
set_speed(config.BOOT_SPEED)
print("pico fan controller ready")

poll = select.poll()
poll.register(sys.stdin, select.POLLIN)
last_seen = time.ticks_ms()
last_blink = time.ticks_ms()
warned = False

while True:
    # A read can fail while the USB host resets the port. The loop must
    # survive that, because a dead loop keeps the fans where they are.
    try:
        ready = poll.poll(100)
    except OSError:
        ready = []
    if ready:
        try:
            line = sys.stdin.readline().strip()
        except OSError:
            line = ""
        if line.isdigit():
            set_speed(int(line))
            last_seen = time.ticks_ms()
            warned = False
            # Two short off blinks, so a received speed is easy to see.
            for _ in range(2):
                set_led(False)
                time.sleep_ms(config.LED_RECEIVED_MS)
                set_led(True)
                time.sleep_ms(config.LED_RECEIVED_MS)
    if time.ticks_diff(time.ticks_ms(), last_seen) > config.WATCHDOG_SECONDS * 1000:
        set_speed(100)
        if time.ticks_diff(time.ticks_ms(), last_blink) > config.LED_WATCHDOG_MS:
            last_blink = time.ticks_ms()
            led.toggle()
        if not warned:
            print("no contact for 60s, fan at 100%")
            warned = True
    time.sleep_ms(100)
