#!/usr/bin/env python3
# V17: force ro.hardware=sc8830 when ro.boot.hardware is empty.
# The bootloader does not pass androidboot.hardware, so ro.hardware stays "unknown"
# (default en init.cpp). Eso rompe `import /init.${ro.hardware}.rc` (init.sc8830.rc
# never imported -> mount_all never runs -> /data unmounted) and the HAL loading
# (`<name>.${ro.hardware}.so`). Idempotente.
import sys

F = "/home/lineage/android/lineage-17.1/system/core/init/init.cpp"
s = open(F, encoding="utf-8", errors="surrogateescape").read()

old = '{ "ro.boot.hardware",   "ro.hardware",   "unknown", },'
new = '{ "ro.boot.hardware",   "ro.hardware",   "sc8830", }, // V17: bootloader no pasa androidboot.hardware'

if 'sc8830' in s and 'V17' in s:
    print("V17_PATCH_ALREADY_PRESENT"); sys.exit(0)
if old not in s:
    print("ERROR: could not find the ro.hardware line in init.cpp", file=sys.stderr); sys.exit(2)
s = s.replace(old, new, 1)
open(F, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V17_PATCH_APPLIED")
