import machine
import sys
import time
import select
import neopixel

# 1. Setup status LED (Dim Green)
np = neopixel.NeoPixel(machine.Pin(16), 1)
np[0] = (0, 3, 0) # Very dim green
np.write()

# 2. Setup Fan on GP0
fan = machine.PWM(machine.Pin(0))
fan.freq(25000)

# Safety variables
last_update = time.time()
WATCHDOG_TIMEOUT = 60 # seconds

def set_fan_speed(percent):
    # Ensure percent is within bounds
    percent = max(0, min(100, percent))
    
    # PC Fans often stall below 15%
    if 0 < percent < 15: 
        percent = 15 
        
    duty = int(percent * 655.35)
    fan.duty_u16(duty)

# Start at 50% for safety until TrueNAS checks in
set_fan_speed(50)

poll_object = select.poll()
poll_object.register(sys.stdin, select.POLLIN)

print("RP2040 Fan Controller Active. Waiting for TrueNAS...")

while True:
    # Check for TrueNAS instructions over USB Serial
    if poll_object.poll(100):
        try:
            line = sys.stdin.readline().strip()
            if line.isdigit():
                speed = int(line)
                set_fan_speed(speed)
                last_update = time.time()
                # Flash Blue quickly to show data received
                np[0] = (0, 0, 5)
                np.write()
                time.sleep(0.05)
                np[0] = (0, 2, 0) # Back to Dim Green
                np.write()
        except:
            pass

    # Watchdog Logic
    if time.time() - last_update > WATCHDOG_TIMEOUT:
        print("RP2040 Fan Controller: No communication for 60 seconds - setting fan speed to 100%")
        set_fan_speed(100) # Safety first!
        np[0] = (10, 0, 0) # Turn LED Red to alert you
        np.write()
    
    time.sleep(0.1)
import machine
import sys
import time
import select
import neopixel

# 1. Setup status LED (Dim Green)
np = neopixel.NeoPixel(machine.Pin(16), 1)
np[0] = (0, 3, 0) # Very dim green
np.write()

# 2. Setup Fan on GP0
fan = machine.PWM(machine.Pin(0))
fan.freq(25000)

# Safety variables
last_update = time.time()
WATCHDOG_TIMEOUT = 60 # seconds

def set_fan_speed(percent):
    # Ensure percent is within bounds
    percent = max(0, min(100, percent))
    
    # PC Fans often stall below 15%
    if 0 < percent < 15: 
        percent = 15 
        
    duty = int(percent * 655.35)
    fan.duty_u16(duty)

# Start at 50% for safety until TrueNAS checks in
set_fan_speed(50)

poll_object = select.poll()
poll_object.register(sys.stdin, select.POLLIN)

print("RP2040 Fan Controller Active. Waiting for TrueNAS...")

while True:
    # Check for TrueNAS instructions over USB Serial
    if poll_object.poll(100):
        try:
            line = sys.stdin.readline().strip()
            if line.isdigit():
                speed = int(line)
                set_fan_speed(speed)
                last_update = time.time()
                # Flash Blue quickly to show data received
                np[0] = (0, 0, 5)
                np.write()
                time.sleep(0.05)
                np[0] = (0, 2, 0) # Back to Dim Green
                np.write()
        except:
            pass

    # Watchdog Logic
    if time.time() - last_update > WATCHDOG_TIMEOUT:
        print("RP2040 Fan Controller: No communication for 60 seconds - setting fan speed to 100%")
        set_fan_speed(100) # Safety first!
        np[0] = (10, 0, 0) # Turn LED Red to alert you
        np.write()
    
    time.sleep(0.1)
