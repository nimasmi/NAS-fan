# RP2040 PWM Fan Controller

This project uses an RP2040 Zero board inside a 3D printed enclosure to control the PWM fan speed of an Intel N100 NAS's case fans. The speed of the fans is proportional to the temperature of the hard drives.

- Written in MicroPython (RP2040) and Python (N100)
- If HDD is asleep, temps are not read and the drive is kept in a sleeping `C_STATE`.
- Minimum fan speed is 15%

- Power savings from 100% fan speed to 15% is approx 4.5w.
- HDD temps should be between 30°c - 40°c. The controller should only kick on the fans if it rises above 40°c.
