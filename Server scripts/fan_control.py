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
            # Stage 1: Check ONLY the power status.
            # -i is fast and usually hits the OS cache, not the platters.
            cmd_pw = f"smartctl -i -n standby /dev/{drive}"
            proc = subprocess.run(cmd_pw, shell=True, text=True, capture_output=True)
            
            # If the drive is in STANDBY or a deep IDLE, smartctl tells us here.
            output = proc.stdout.upper()
            
            # Logic: If it's in STANDBY or any IDLE state (like IDLE_B or IDLE_C),
            # we consider it "Sleeping" for the sake of fan control to prevent spin-up.
            if proc.returncode == 2 or "STANDBY" in output or "IDLE_C" in output or "IDLE_B" in output:
                details.append(f"{drive}: ASLEEP")
                continue 

            # Stage 2: If it's truly ACTIVE or IDLE (platter spinning), get the temp.
            awake_count += 1
            cmd_temp = f"smartctl -A /dev/{drive}"
            res_t = subprocess.check_output(cmd_temp, shell=True, text=True)
            
            drive_temp = None
            for line in res_t.splitlines():
                if "Temperature_Celsius" in line:
                    drive_temp = int(line.split()[9])
                    if drive_temp > max_temp:
                        max_temp = drive_temp
                    break
            
            details.append(f"{drive}: {drive_temp}C" if drive_temp else f"{drive}: AWAKE")
            
        except Exception as e:
            details.append(f"{drive}: ERR")
            
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
