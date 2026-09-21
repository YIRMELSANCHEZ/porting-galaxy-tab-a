#!/usr/bin/env python3
# V86 (VIDEO). After V85 mediaswcodec now locates gralloc.sc8830.so but its dlopen fails:
# 'library "libnativehelper.so" not found': gralloc -> libdither.so -> libandroid_runtime.so ->
# libnativehelper (APEX runtime, inaccessible from the sphal namespace, and it would also drag the whole
# framework into the decoder process). libdither is in source (hardware/sprd/libdither) and only uses
# utils/Timers.h + utils/Log.h: libbinder and libandroid_runtime are removed from LOCAL_SHARED_LIBRARIES.
# Idempotente.
import sys
from pathlib import Path

p = Path("/home/lineage/android/lineage-17.1/hardware/sprd/libdither/Android.mk")
s = p.read_text(encoding="utf-8")
old = """LOCAL_SHARED_LIBRARIES := \\
	libutils \\
	libcutils \\
	libbinder \\
	libdl \\
	libandroid_runtime \\
	liblog \\
"""
new = """# V86: sin libbinder/libandroid_runtime (arrastraban libnativehelper al namespace sphal de mediaswcodec)
LOCAL_SHARED_LIBRARIES := \\
	libutils \\
	libcutils \\
	libdl \\
	liblog \\
"""
if "V86" in s:
    print("libdither/Android.mk: already patched")
elif s.count(old) != 1:
    print("V86_ERROR: unexpected libdither/Android.mk block"); sys.exit(1)
else:
    p.write_text(s.replace(old, new, 1), encoding="utf-8")
    print("libdither/Android.mk: dependencias recortadas")
print("V86_DONE")
