#!/usr/bin/env python3
# V52 (WiFi bring-up, step 9 - wpa_supplicant binary path): with V51 the generic vendor
# HAL STARTS ("WifiVendorHal: Vendor Hal started successfully") and the framework moves to
# start the supplicant via HIDL, but:
#   WifiNative: Failed to connect to supplicant
#   dmesg: init: Could not ctl.interface_start for
#     'android.hardware.wifi.supplicant@1.0::ISupplicant/default':
#     Cannot find '/system/bin/wpa_supplicant': No such file or directory
# Cause: the wpa_supplicant service (rewritten in V45) points to /system/bin/wpa_supplicant,
# but in Android 10 the binary is installed as a vendor HAL in /vendor/bin/hw/wpa_supplicant
# (verified on the device). init does not find it -> does not start -> does not register ISupplicant.
#
# Fix: correct the service path to /vendor/bin/hw/wpa_supplicant in init.wifi.rc. This
# file goes in the RAMDISK (device.mk: rootdir/init.wifi.rc -> root/), so it requires
# rebuild boot.img (new hash; same kernel). Cumulative over V51. Idempotent.
import sys

RC = "/home/lineage/android/lineage-17.1/device/samsung/gtexswifi/rootdir/init.wifi.rc"
s = open(RC, encoding="utf-8", errors="surrogateescape").read()

OLD = "service wpa_supplicant /system/bin/wpa_supplicant \\\n"
NEW = "service wpa_supplicant /vendor/bin/hw/wpa_supplicant \\\n"

if "service wpa_supplicant /vendor/bin/hw/wpa_supplicant" in s:
    print("V52_ALREADY"); sys.exit(0)
if OLD not in s:
    print("V52_ERROR: cannot find the expected wpa_supplicant service (V45)")
    sys.exit(1)

s = s.replace(OLD, NEW, 1)
open(RC, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V52_APPLIED -> wpa_supplicant en /vendor/bin/hw/wpa_supplicant")
