#!/usr/bin/env python3
# V50 (WiFi bring-up, step 7 - driver module path): with V49 the legacy HAL initializes
# well (no NOT_SUPPORTED) and tries to load the driver, but:
#   android.hardware.wifi@1.0-service.legacy: Failed to open /lib/modules/sprdwl.ko:
#     No such file or directory
#   Failed to load WiFi driver -> Wifi HAL start failed
# Cause: WIFI_DRIVER_MODULE_PATH := "/lib/modules/sprdwl.ko" (BoardConfig), but on this
# on the device /lib does NOT EXIST (there is no /lib -> /system/lib symlink; / is the ramdisk and /system goes
# mounted separately). The .ko is in /system/lib/modules/sprdwl.ko (verified). Before the
# installclean worked due to a residual /lib/modules from the base build; installclean
# removed it and the wrong path surfaced.
#
# Fix: WIFI_DRIVER_MODULE_PATH := "/system/lib/modules/sprdwl.ko" (real path). It is a compile
# define used by libwifi_hal (DRIVER_MODULE_PATH) -> recompiles the HAL. Only system changes
# system.img; boot = V45 (f8a355e5). Cumulative over V49. Idempotent.
import sys

BC = "/home/lineage/android/lineage-17.1/device/samsung/gtexswifi/BoardConfig.mk"
s = open(BC, encoding="utf-8", errors="surrogateescape").read()

OLD = 'WIFI_DRIVER_MODULE_PATH     := "/lib/modules/sprdwl.ko"'
NEW = 'WIFI_DRIVER_MODULE_PATH     := "/system/lib/modules/sprdwl.ko"'

if '"/system/lib/modules/sprdwl.ko"' in s:
    print("V50_ALREADY"); sys.exit(0)
if OLD not in s:
    print("V50_ERROR: cannot find the expected WIFI_DRIVER_MODULE_PATH line")
    sys.exit(1)

s = s.replace(OLD, NEW, 1)
open(BC, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V50_APPLIED -> WIFI_DRIVER_MODULE_PATH = /system/lib/modules/sprdwl.ko")
