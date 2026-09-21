#!/usr/bin/env python3
# V85 (VIDEO). After V84 the mapper@2.0-impl loads in mediaswcodec, but hw_get_module fails:
# 'library "/system/lib/hw/gralloc.sc8830.so" needed or dlopened by "/system/lib/libhardware.so" is
# not accessible for the namespace "sphal"' -> MapperHal "failed to get gralloc module" -> same
# SIGSEGV in C2AllocatorGralloc. In this build the gralloc module is in /system/lib/hw (not in
# /vendor/lib/hw); /system/${LIB}/hw is added to permitted.paths (and search) of the sphal namespace of
# the swcodec APEX ld.config.txt. Idempotent; requires apply-v84 first.
import sys
from pathlib import Path

p = Path("/home/lineage/android/lineage-17.1/frameworks/av/apex/ld.config.txt")
s = p.read_text(encoding="utf-8")
if "V85" in s:
    print("apex/ld.config.txt: already patched (V85)")
else:
    old = "namespace.sphal.search.paths += /system/${LIB}\n"
    if s.count(old) != 1:
        print("V85_ERROR: the V84 line is missing"); sys.exit(1)
    s = s.replace(old, old + "# V85: el modulo gralloc.sc8830.so esta en /system/lib/hw en esta build\n"
                  "namespace.sphal.search.paths += /system/${LIB}/hw\n"
                  "namespace.sphal.permitted.paths += /system/${LIB}\n"
                  "namespace.sphal.permitted.paths += /system/${LIB}/hw\n", 1)
    p.write_text(s, encoding="utf-8")
    print("apex/ld.config.txt: sphal allows /system/lib/hw")
print("V85_DONE")
