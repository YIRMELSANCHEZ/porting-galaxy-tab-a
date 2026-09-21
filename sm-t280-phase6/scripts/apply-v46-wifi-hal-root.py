#!/usr/bin/env python3
# V46 (WiFi bring-up, step 3 - the vendor HAL cannot load the driver): with V45 the
# framework gets to start the WiFi vendor HAL, but:
#   android.hardware.wifi@1.0-service: finit_module return: -1: Operation not permitted
#   Failed to load WiFi driver -> Wifi HAL start failed
#   WifiVendorHal: Failed to start vendor HAL
# SELinux is Permissive, so it is NOT SELinux. It is the known problem of
# CAPABILITIES on kernel 3.10 (no ambient capabilities, the same that broke logd in
# V22-V24): the wifi@1.0-service runs as `user wifi` with `capabilities
# ... SYS_MODULE`, but on setuid(wifi) kernel 3.10 cannot raise the capability
# via the ambient mechanism -> CAP_SYS_MODULE is lost -> finit_module fails with EPERM.
# (The MANUAL insmod as root does load the driver: wlan0 is created, firmware OK.)
#
# Fix: make android.hardware.wifi@1.0-service run as ROOT (no setuid to wifi), so it
# keeps CAP_SYS_MODULE and can do finit_module of the sprdwl driver. It is a bring-up
# fix (permissive); reversible if the caps are ever resolved. Its .rc installs
# in /vendor/etc/init (system.img); boot = V45 (unchanged). Cumulative. Idempotent.
import sys

RC = "/home/lineage/android/lineage-17.1/hardware/interfaces/wifi/1.3/default/android.hardware.wifi@1.0-service.rc"

s = open(RC, encoding="utf-8", errors="surrogateescape").read()

if "user root" in s:
    print("V46_ALREADY"); sys.exit(0)

OLD = "    user wifi\n"
if OLD not in s:
    print("V46_ERROR: cannot find 'user wifi' in the wifi HAL rc")
    sys.exit(1)

s = s.replace(OLD, "    user root\n", 1)
open(RC, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V46_APPLIED -> android.hardware.wifi@1.0-service runs as root (CAP_SYS_MODULE)")
