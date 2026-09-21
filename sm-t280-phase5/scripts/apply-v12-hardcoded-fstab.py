#!/usr/bin/env python3
# V12: inject the first-stage /system entry by hand in ReadFirstStageFstab().
# This device does not expose /proc/device-tree (ReadFstabFromDt dies), the bootloader does not
# pass androidboot.hardware (GetFstabPath dies) and the fstab.sc8830 entry does not
# carry the first_stage_mount flag (it would be filtered). The only robust path is to build
# the FstabEntry in code, following the in-tree BuildGsiSystemFstabEntry() pattern.
# Idempotente.
import sys

SRC = "/home/lineage/android/lineage-17.1/system/core/init/first_stage_mount.cpp"
MARK = "gtexswifi: entrada /system de first-stage hardcodeada"

INJECT = '''
    // ''' + MARK + ''' (sin DT, sin ro.hardware, sin flag en fstab).
    if (fstab.empty()) {
        FstabEntry system = {.blk_device = "/dev/block/platform/sdio_emmc/by-name/SYSTEM",
                             .mount_point = "/system",
                             .fs_type = "ext4",
                             .flags = MS_RDONLY,
                             .fs_options = "errors=panic"};
        system.fs_mgr_flags.wait = true;
        system.fs_mgr_flags.first_stage_mount = true;
        fstab.emplace_back(std::move(system));
    }
'''

with open(SRC, "r", encoding="utf-8") as f:
    src = f.read()

if MARK in src:
    print("V12_PATCH_ALREADY_PRESENT")
    sys.exit(0)

lines = src.splitlines(keepends=True)
# Locate ReadFirstStageFstab and its final 'return fstab;' to inject before it.
start = None
for i, l in enumerate(lines):
    if "Fstab ReadFirstStageFstab()" in l:
        start = i
        break
if start is None:
    print("ERROR: could not find ReadFirstStageFstab()", file=sys.stderr)
    sys.exit(2)

ret_idx = None
for j in range(start + 1, len(lines)):
    if lines[j].strip() == "return fstab;":
        ret_idx = j
        break
if ret_idx is None:
    print("ERROR: could not find 'return fstab;' of ReadFirstStageFstab()", file=sys.stderr)
    sys.exit(2)

lines.insert(ret_idx, INJECT)
with open(SRC, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("V12_PATCH_APPLIED")
