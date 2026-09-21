#!/usr/bin/env python3
# V32. V31 (BINDER_TYPE_FDA) broke the binder wall: SurfaceFlinger now allocates its
# FramebufferSurface (usage 0x1a00, 3 buffers, result=0). One failure remains: the
# bootanimation buffer (usage 0xf02) fails in libui's CLIENT validator:
#   E Gralloc2: buffer descriptor contains invalid usage bits 0x400
#   E GraphicBufferAllocator: Failed to allocate ... usage f02: -22
# 0x400 = bit 10 = GRALLOC_USAGE_HW_2D (legacy, not in the HIDL BufferUsage enum).
# V26 only added bit 25; bit 10 is missing. The common legacy bits 10/13/21 are added
# (like Qualcomm) to TARGET_ADDITIONAL_GRALLOC_10_USAGE_BITS -> valid mask in
# libui. Change in system.img (libui); boot = V31 (unchanged). Idempotent.
import sys

F = "/home/lineage/android/lineage-17.1/device/samsung/gtexswifi/BoardConfig.mk"
s = open(F, encoding="utf-8", errors="surrogateescape").read()

if "(1 << 10)" in s:
    print("V32_PATCH_ALREADY_PRESENT"); sys.exit(0)

old = "TARGET_ADDITIONAL_GRALLOC_10_USAGE_BITS += | (1 << 25)\n"
new = (
    "TARGET_ADDITIONAL_GRALLOC_10_USAGE_BITS += | (1 << 25)\n"
    "# V32: bits de uso legacy SPRD/HW_2D que libui rechazaba (0x400=bit10 en bootanim)\n"
    "TARGET_ADDITIONAL_GRALLOC_10_USAGE_BITS += | (1 << 10)\n"
    "TARGET_ADDITIONAL_GRALLOC_10_USAGE_BITS += | (1 << 13)\n"
    "TARGET_ADDITIONAL_GRALLOC_10_USAGE_BITS += | (1 << 21)\n"
)

if s.count(old) != 1:
    print("V32_ANCHOR_ERROR count=%d" % s.count(old)); sys.exit(1)

s = s.replace(old, new, 1)
open(F, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V32_PATCH_APPLIED")
