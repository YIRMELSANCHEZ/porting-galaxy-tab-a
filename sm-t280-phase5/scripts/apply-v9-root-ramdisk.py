#!/usr/bin/env python3
# V9: build the boot ramdisk from TARGET_ROOT_OUT (full legacy rootfs:
# init.rc, init.*.rc, /system mountpoint, sepolicy, fstab.sc8830, symlinks) with a
# real binary /init instead of the symlink to /system/bin/init.
#
# Fixes the root cause of the loop: V6 used TARGET_RAMDISK_OUT (minimal
# system-as-root ramdisk, without /system or init.rc), so first-stage could not mount
# /system and execv(/system/bin/init) failed. Idempotent.
import sys, re

MK = "/home/lineage/android/lineage-17.1/device/samsung/gtexswifi/mkbootimg.mk"
MARK = "# V9: ramdisk de boot desde ROOT_OUT con /init binario real"

with open(MK, "r", encoding="utf-8") as f:
    src = f.read()

if MARK in src:
    print("V9_PATCH_ALREADY_PRESENT")
    sys.exit(0)

lines = src.splitlines(keepends=True)
out = []
done = False
for l in lines:
    # Replace the boot ramdisk MKBOOTFS line (avoid the recovery one).
    if (not done) and ("$(MKBOOTFS)" in l) and ("$(INSTALLED_RAMDISK_TARGET)" in l) and ("$(TARGET_RAMDISK_OUT)" in l):
        indent = re.match(r"\s*", l).group(0)
        out.append(f"{indent}$(hide) {MARK}\n")
        # real binary init (from RAMDISK_OUT) over the ROOT_OUT symlink.
        out.append(f"{indent}$(hide) rm -f $(TARGET_ROOT_OUT)/init\n")
        out.append(f"{indent}$(hide) cp -f $(TARGET_RAMDISK_OUT)/init $(TARGET_ROOT_OUT)/init\n")
        # Package the full legacy rootfs (ROOT_OUT) as the boot ramdisk.
        out.append(f"{indent}$(hide) $(MKBOOTFS) -d $(TARGET_OUT) $(TARGET_ROOT_OUT) | $(BOOT_RAMDISK_COMPRESSOR) > $(INSTALLED_RAMDISK_TARGET)\n")
        done = True
        continue
    # Remove the V8 fstab copy to RAMDISK_OUT (now unnecessary with ROOT_OUT).
    if "cp -f $(TARGET_ROOT_OUT)/fstab.sc8830 $(TARGET_RAMDISK_OUT)/fstab.sc8830" in l:
        continue
    if "V8: fstab.sc8830 en el ramdisk de boot" in l:
        continue
    out.append(l)

if not done:
    print("ERROR: could not find the boot ramdisk MKBOOTFS line", file=sys.stderr)
    sys.exit(2)

with open(MK, "w", encoding="utf-8") as f:
    f.writelines(out)
print("V9_PATCH_APPLIED")
