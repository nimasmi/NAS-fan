# Board constants. Change these only when the hardware changes.
FAN_PIN = 0
# "LED" is the board LED. On a Pico it is GPIO 25. On a Pico W it is the
# single-colour LED behind the wireless chip, which Pin(25) does not reach.
LED_PIN = "LED"
PWM_HZ = 25000
STALL_FLOOR = 15
BOOT_SPEED = 50
WATCHDOG_SECONDS = 60
# True when the fans are driven through a MOSFET, which inverts the duty.
PWM_INVERTED = False
# The board LED has one colour, so the states are steady and two blinks.
LED_RECEIVED_MS = 150
LED_WATCHDOG_MS = 250
