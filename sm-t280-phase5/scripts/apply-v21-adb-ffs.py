#!/usr/bin/env python3
# V21 (diagnostic): enable adbd in the system boot to be able to pull
# logcat (the composer exits with status 1, no signal -> its error is only in
# logcat, not in last_kmsg). system already carries ro.adb.secure=0 and
# persist.sys.usb.config=mtp,adb, but it is missing the FunctionFS compat props
# (phase 4 fix, applied only to the recovery ramdisk); without them adbd
# does not enumerate on kernel 3.10. Idempotent.
import sys

F = "/home/lineage/android/lineage-17.1/device/samsung/gtexswifi/device.mk"
s = open(F, encoding="utf-8", errors="surrogateescape").read()

MARK = "# V21 diag: adbd/FunctionFS en system"
if MARK in s:
    print("V21_PATCH_ALREADY_PRESENT"); sys.exit(0)

block = (
    "\n" + MARK + "\n"
    "PRODUCT_PROPERTY_OVERRIDES += \\\n"
    "    ro.adb.nonblocking_ffs=false \\\n"
    "    sys.usb.ffs.aio_compat=true\n"
)
# Append at the end of the file.
s = s.rstrip("\n") + "\n" + block
open(F, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V21_PATCH_APPLIED")
