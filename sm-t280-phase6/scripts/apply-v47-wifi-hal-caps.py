#!/usr/bin/env python3
# V47 (WiFi bring-up, step 4 - the REAL finit_module EPERM fix): V46 set the vendor HAL
# as `user root` but finit_module STILL failed with EPERM. Definitive diagnosis via
# /proc/<pid>/status of the wifi@1.0-service:
#   Uid: 0 0 0 0   (root)
#   CapPrm: 0000000000000000
#   CapEff: 0000000000000000
#   CapBnd: 0000000000000000
# That is: root but with ZERO capabilities. The `capabilities NET_ADMIN NET_RAW
# SYS_MODULE` line in the .rc, on kernel 3.10 (no ambient capabilities), makes init
# try to raise the caps via the ambient mechanism (which does not exist) and the result is that
# it CLEARS all cap sets (bounding/effective/permitted = 0). A root process
# with CapEff=0 cannot finit_module -> EPERM. (A normal root shell has
# CapEff=0x1fffffffff, that is why the manual insmod does load the driver.)
#
# Fix: REMOVE the `capabilities ...` line from the rc. Without it, init does not touch the cap
# sets and the root process keeps ALL capabilities (including SYS_MODULE) ->
# finit_module loads the driver. Same lesson as logd (V22-V24) on this kernel.
# The .rc installs in /vendor/etc/init (system.img); boot = V45 (unchanged).
# Cumulative over V46. Idempotent.
import sys

RC = "/home/lineage/android/lineage-17.1/hardware/interfaces/wifi/1.3/default/android.hardware.wifi@1.0-service.rc"

s = open(RC, encoding="utf-8", errors="surrogateescape").read()

CAP_LINE = "    capabilities NET_ADMIN NET_RAW SYS_MODULE\n"

if CAP_LINE not in s:
    if "capabilities" not in s:
        print("V47_ALREADY (no capabilities line)"); sys.exit(0)
    print("V47_ERROR: capabilities line differs from the expected one"); sys.exit(1)

s = s.replace(CAP_LINE, "", 1)
open(RC, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V47_APPLIED -> capabilities line removed (root keeps all caps)")
