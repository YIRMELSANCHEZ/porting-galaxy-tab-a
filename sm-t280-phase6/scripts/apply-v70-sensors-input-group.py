#!/usr/bin/env python3
# V70 (part 2: AUTO-ROTATION). On top of V69. Change ONLY in the sensors service's init.rc.
#
# ROOT CAUSE (verified on HW):
#   logcat: "Sensors: AccelerometerSensor enable: mEnabled 0, handle 0, en 1"
#           "SensorService: Error activating sensor 0 (Operation not permitted)"  <- EPERM
#   The WindowOrientationListener IS enabled and registers the accelerometer
#   (mEnabled=true, mSensor=K2HH, AccelSensorJudge), the HAL receives the request, but on
#   writing the activation node it gets EPERM and the sensor never turns on
#   (0 active connections, raw_data 0,0,0 -> mOrientation=-1 -> no rotation).
# EVIDENCIA:
#   - /sys/class/input/input5/{enable,poll_delay} son  -rw-rw---- root:input  (0660, grupo input)
#   - the android.hardware.sensors@1.0-service runs as uid/gid 1000 (system) with
#     groups "system wakelock uhid" -> it does NOT belong to the 'input' group -> cannot write.
#   - init.board.rc does chown of /sys/class/sensors/accelerometer_sensor/* but NOT of the
#     the real enable/poll_delay nodes of the input device.
#   - Tested as root: on writing poll_delay, k2hh_set_odr fires ("change odr 3") and
#     raw_data goes from "0,0,0" to real data (-150,-8,7916 ~ 1g). The chip works.
#   - The HAL calls setDelay BEFORE enable, so as soon as it can write it will configure the
#     ODR and the data will flow.
#
# FIX: add the 'input' group to the sensors service. Robust (does not depend on the number of
# inputN, which can vary between boots). Idempotent.
import sys
from pathlib import Path

SRC = Path("/home/lineage/android/lineage-17.1/hardware/interfaces/sensors/1.0/default/"
           "android.hardware.sensors@1.0-service.rc")

s = SRC.read_text(encoding="utf-8", errors="surrogateescape")

if "group system wakelock uhid input" in s:
    print("V70_SENSORS_ALREADY"); sys.exit(0)

OLD = "    group system wakelock uhid\n"
NEW = "    group system wakelock uhid input\n"

if OLD not in s:
    print("V70_ERROR: cannot find 'group system wakelock uhid' in the sensors rc"); sys.exit(1)

s = s.replace(OLD, NEW, 1)
SRC.write_text(s, encoding="utf-8", errors="surrogateescape")
print("V70_APPLIED -> 'input' group added to the sensors service (accelerometer activation)")
