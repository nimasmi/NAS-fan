import subprocess
import time
import os
import glob

# --- CONFIGURATION ---
PORT = '/dev/ttyACM0'
TEMP_LOW = 35    # Below this, fans are at MIN_SPEED
TEMP_HIGH = 50   # Above this, fans are at 100%
MIN_SPEED = 15   # Lowest speed while drives are awake
CHECK_INTERVAL = 30  # Heartbeat (must be less than RP2040 watchdog)

def get_all_drives():
    """Finds all physical disks (sdX and nvmeX) currently in the system."""
    # This looks for devices like sda, sdb, and nvme0n1
    paths = glob.glob('/dev/sd[a-z]') + glob.glob('/dev/nvme[0-9]n1')
    return [os.path.basename(p) for p in paths]

def get_max_temp():
    drives = get_all_drives()
    max_temp = 0
    drives_awake = 0

    for drive in drives:
        try:
            # -n standby prevents waking sleeping drives
            cmd = f"smartctl -n standby -A /dev/{drive}"
            res = subprocess.check_output(cmd, shell=True, text=True)
            
            # Check for standard HDD temp or NVMe temp
            for line in res.splitlines():
                if "Temperature_Celsius" in line or "Temperature:" in line:
                    # Extract the integer temperature value
                    temp = int("".join(filter(str.isdigit, line.split()[-1])))
                    if temp > max_temp:
                        max_temp = temp
                    drives_awake += 1
        except Exception:
            # Drive is likely in Standby/Sleep
            continue
            
    return max_temp, drives_awake

def set_fan(speed):
    try:
        if os.path.exists(PORT):
            with open(PORT, 'w') as f:
                f.write(f"{speed}\n")
                f.flush()
            return True
    except Exception as e:
        print(f"Communication Error: {e}")
    return False

print("Auto-Detecting Fan Controller Started...")

while True:
    max_t, awake_count = get_max_temp()
    
    if awake_count == 0:
        # All drives are asleep. Safe to turn fans OFF (0%)
        fan_speed = 0
        status = "All drives asleep"
    elif max_t <= TEMP_LOW:
        fan_speed = MIN_SPEED
        status = f"Drives cool ({max_t}C)"
    elif max_t >= TEMP_HIGH:
        fan_speed = 100
        status = f"Drives HOT ({max_t}C)"
    else:
        # Linear scale calculation
        ratio = (max_t - TEMP_LOW) / (TEMP_HIGH - TEMP_LOW)
        fan_speed = int(MIN_SPEED + (ratio * (100 - MIN_SPEED)))
        status = f"Drives active ({max_t}C)"

    print(f"[{time.strftime('%H:%M:%S')}] {status} -> Fan Speed: {fan_speed}%")
    set_fan(fan_speed)
    
    time.sleep(CHECK_INTERVAL)
