# This revision (3) is bad because it wakes the drives every 30 seconds, causes a power spike, and damages the drives, just to read the status of the drive.
# This problem is fixed in revision 4.


import subprocess
import time
import os
import glob
import logging
from logging.handlers import RotatingFileHandler

# --- CONFIGURATION ---
LOG_FILE = '/mnt/NVME_APPS/apps/fan_control.log'
TEMP_LOW = 35    
TEMP_HIGH = 50   
MIN_SPEED = 15   
CHECK_INTERVAL = 30  

handler = RotatingFileHandler(LOG_FILE, maxBytes=1024*1024, backupCount=1)
logging.basicConfig(
    handlers=[handler],
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def get_all_drives():
    paths = glob.glob('/dev/sd[a-z]') + glob.glob('/dev/nvme[0-9]n1')
    return [os.path.basename(p) for p in paths]

def get_max_temp():
    drives = get_all_drives()
    max_temp = 0
    awake_count = 0
    details = []

    for drive in drives:
        try:
            cmd = f"smartctl -n standby -A /dev/{drive}"
            res = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
            
            drive_temp = None
            for line in res.splitlines():
                if "Temperature_Celsius" in line or "Temperature:" in line:
                    parts = line.split()
                    raw_val = parts[-1] if "Temperature:" in line else parts[9]
                    drive_temp = int("".join(filter(str.isdigit, raw_val)))
                    if drive_temp > max_temp:
                        max_temp = drive_temp
                    awake_count += 1
            
            if drive_temp:
                details.append(f"{drive}: {drive_temp}C")
            else:
                details.append(f"{drive}: Awake")
        except Exception:
            details.append(f"{drive}: ASLEEP")
            
    return max_temp, awake_count, ", ".join(details)

def set_fan(speed):
    # Find the port dynamically in case it shifts from ACM0 to ACM1
    ports = glob.glob('/dev/ttyACM*')
    if not ports:
        logging.error("RP2040 not found! Check USB connection.")
        return False
    
    port = ports[0]
    try:
        # This is the "Wake Up" command that fixed your issue
        subprocess.run(['stty', '-F', port, '9600', 'raw', '-echo'], check=True, capture_output=True)
        
        with open(port, 'w') as f:
            f.write(f"{speed}\n")
            f.flush()
        return True
    except Exception as e:
        logging.error(f"Communication Error on {port}: {e}")
        return False

logging.info("--- Fan Control Service Started (v2.0 with Auto-Stty) ---")

while True:
    max_t, awake_count, drive_status = get_max_temp()
    
    if awake_count == 0:
        fan_speed = 0
        summary = "All drives asleep"
    elif max_t <= TEMP_LOW:
        fan_speed = MIN_SPEED
        summary = f"Drives cool ({max_t}C)"
    elif max_t >= TEMP_HIGH:
        fan_speed = 100
        summary = f"Drives HOT ({max_t}C)"
    else:
        ratio = (max_t - TEMP_LOW) / (TEMP_HIGH - TEMP_LOW)
        fan_speed = int(MIN_SPEED + (ratio * (100 - MIN_SPEED)))
        summary = f"Drives active ({max_t}C)"

    logging.info(f"Speed: {fan_speed}% | {summary} | Status: [{drive_status}]")
    set_fan(fan_speed)
    time.sleep(CHECK_INTERVAL)