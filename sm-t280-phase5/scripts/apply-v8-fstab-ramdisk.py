#!/usr/bin/env python3
# V8: include fstab.sc8830 in the boot ramdisk (TARGET_RAMDISK_OUT).
# The V6 fix builds the ramdisk from TARGET_RAMDISK_OUT, which only has
# `init`; fstab.sc8830 lives in TARGET_ROOT_OUT (root/). First-stage init looks for
# /fstab.sc8830 in the ramdisk and does not find it -> reboots to bootloader.
# This patch copies fstab.sc8830 to the ramdisk root just before MKBOOTFS.
# Idempotente.
import sys

MK = "/home/lineage/android/lineage-17.1/device/samsung/gtexswifi/mkbootimg.mk"
MARK = "# V8: fstab.sc8830 en el ramdisk de boot para first-stage mount"
CP_LINE = "\t$(hide) cp -f $(TARGET_ROOT_OUT)/fstab.sc8830 $(TARGET_RAMDISK_OUT)/fstab.sc8830\n"
MKBOOTFS_NEEDLE = "$(MKBOOTFS) -d $(TARGET_OUT) $(TARGET_RAMDISK_OUT) |"

with open(MK, "r", encoding="utf-8") as f:
    lines = f.readlines()

if any(MARK in l for l in lines):
    print("V8_PATCH_ALREADY_PRESENT")
    sys.exit(0)

out = []
patched = False
for l in lines:
    if (not patched) and (MKBOOTFS_NEEDLE in l):
        out.append("\t$(hide) " + MARK + "\n")
        out.append(CP_LINE)
        patched = True
    out.append(l)

if not patched:
    print("ERROR: could not find the boot ramdisk MKBOOTFS line", file=sys.stderr)
    sys.exit(2)

with open(MK, "w", encoding="utf-8") as f:
    f.writelines(out)
print("V8_PATCH_APPLIED")
