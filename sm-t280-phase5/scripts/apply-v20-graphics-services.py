#!/usr/bin/env python3
# V20: add the Android 10 graphics HIDL services missing in the device
# tree. The blob MODULES (gralloc.sc8830, hwcomposer.sc8830, libGLES_mali) are there,
# but NOT the services that expose them via HIDL (composer@2.1-service,
# allocator@2.0-service, mapper@2.0-impl). surfaceflinger pide composer@2.1 y no
# nobody provides -> EX_TRANSACTION_FAILED. The AOSP default services
# incluyen adaptadores (hwc2on1adapter, Gralloc1On0). Idempotente.
import sys

F = "/home/lineage/android/lineage-17.1/device/samsung/gtexswifi/device.mk"
s = open(F, encoding="utf-8", errors="surrogateescape").read()

if "graphics.composer@2.1-service" in s:
    print("V20_PATCH_ALREADY_PRESENT"); sys.exit(0)

old = "    hwcomposer.sc8830 \\\n"
new = ("    hwcomposer.sc8830 \\\n"
       "    android.hardware.graphics.allocator@2.0-service \\\n"
       "    android.hardware.graphics.mapper@2.0-impl \\\n"
       "    android.hardware.graphics.composer@2.1-service \\\n")

if old not in s:
    print("ERROR: could not find 'hwcomposer.sc8830' in device.mk", file=sys.stderr)
    sys.exit(2)
s = s.replace(old, new, 1)
open(F, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V20_PATCH_APPLIED")
