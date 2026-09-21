#!/usr/bin/env python3
# V53 (WiFi bring-up, step 10 - supplicant data directory): with V52 wpa_supplicant
# now starts (/vendor/bin/hw/wpa_supplicant, live pid) and the framework connects via HIDL, but:
#   wpa_supplicant: Failed to write to /data/vendor/wifi/wpa/wpa_supplicant.conf:
#     No such file or directory
#   wpa_supplicant: Conf file does not exists: /data/vendor/wifi/wpa/wpa_supplicant.conf
#   SupplicantStaIfaceHal: Failed to create ISupplicantIface 1
# Cause: Android 10's supplicant HAL copies the .conf to /data/vendor/wifi/wpa/ and operates
# there, but that directory does NOT exist (the device's init.wifi.rc only creates /data/misc/wifi,
# old style). Without the dir -> it cannot create the conf -> ISupplicantIface fails -> the
# framework tears down and wlan0 does not stay up.
#
# Fix: crear /data/vendor/wifi, /data/vendor/wifi/wpa y .../sockets (owner wifi:wifi) en
# on post-fs-data of init.wifi.rc. Goes in the RAMDISK -> boot.img CHANGES (same kernel).
# Cumulative over V52. Idempotent.
import sys

RC = "/home/lineage/android/lineage-17.1/device/samsung/gtexswifi/rootdir/init.wifi.rc"
s = open(RC, encoding="utf-8", errors="surrogateescape").read()

if "/data/vendor/wifi/wpa" in s:
    print("V53_ALREADY"); sys.exit(0)

ANCHOR = "    mkdir /data/misc/wifi/wpa_supplicant 0770 wifi wifi\n"
ADD = (
    ANCHOR
    + "    # V53: dirs de datos del supplicant Android 10 (HIDL copia el conf aqui)\n"
    "    mkdir /data/vendor/wifi 0770 wifi wifi\n"
    "    mkdir /data/vendor/wifi/wpa 0770 wifi wifi\n"
    "    mkdir /data/vendor/wifi/wpa/sockets 0770 wifi wifi\n"
)

if ANCHOR not in s:
    print("V53_ERROR: cannot find the mkdir /data/misc/wifi/wpa_supplicant anchor")
    sys.exit(1)

s = s.replace(ANCHOR, ADD, 1)
open(RC, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V53_APPLIED -> mkdir /data/vendor/wifi/wpa (+sockets) en post-fs-data")
