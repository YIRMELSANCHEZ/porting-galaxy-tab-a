#!/usr/bin/env python3
# V25 (graphics fix): with logcat (V24) the SurfaceFlinger error is finally
# visible:
#   composer@2.1-service: Could not get passthrough implementation for
#                         android.hardware.graphics.composer@2.1::IComposer/default
#   -> service exited status 1 -> SurfaceFlinger: "failed to get hwcomposer
#      service" -> SIGABRT (loop on the logo).
#
# Cause: the `-service` (V20) are PASSTHROUGH: they load in-process the `-impl` lib
# that wraps the HWC/gralloc blob. On the device those `-impl` are missing:
#   - android.hardware.graphics.composer@2.1-impl  (trae libhwc2on1adapter ->
#     envuelve HWC1 hwcomposer.sc8830.so)
#   - android.hardware.graphics.allocator@2.0-impl (envuelve gralloc0
#     gralloc.sc8830.so)
# (mapper@2.0-impl was already added in V20 and IS present.)
#
# Fix: add them to PRODUCT_PACKAGES next to the graphics block. They are vendor -> they
# install in /vendor/lib/hw. Change in system.img (full build). Idempotent.
import sys

F = "/home/lineage/android/lineage-17.1/device/samsung/gtexswifi/device.mk"
s = open(F, encoding="utf-8", errors="surrogateescape").read()

if "android.hardware.graphics.composer@2.1-impl" in s:
    print("V25_PATCH_ALREADY_PRESENT"); sys.exit(0)

old = (
    "    android.hardware.graphics.allocator@2.0-service \\\n"
    "    android.hardware.graphics.mapper@2.0-impl \\\n"
    "    android.hardware.graphics.composer@2.1-service \\\n"
)
new = (
    "    android.hardware.graphics.allocator@2.0-service \\\n"
    "    android.hardware.graphics.allocator@2.0-impl \\\n"
    "    android.hardware.graphics.mapper@2.0-impl \\\n"
    "    android.hardware.graphics.composer@2.1-service \\\n"
    "    android.hardware.graphics.composer@2.1-impl \\\n"
)

if s.count(old) != 1:
    print("V25_PATCH_ANCHOR_ERROR count=%d" % s.count(old)); sys.exit(1)

s = s.replace(old, new)
open(F, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V25_PATCH_APPLIED")
