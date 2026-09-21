#!/usr/bin/env python3
# V26 (unblock graphics presentation). With V25 the graphics HIDL stack already
# works: SurfaceFlinger registers its service, powers the display (power mode 2)
# and launches bootanim. BUT the screen stays on the logo because the Spreadtrum HWC does not
# consigue presentar frames (logcat V25):
#   E Gralloc2: buffer descriptor contains invalid usage bits 0x2000000
#   E SPRDHWComposer: SprdDisplayPlane cannot alloc buffer
#   E SPRDHWComposer: eglCreateWindowSurface EGL_BAD_NATIVE_WINDOW -> Init EGL ENV failed
#
# Cause: SPRDHWComposer requests buffers with a PRIVATE usage bit 0x2000000 (bit 25).
# frameworks/native/libs/ui/Gralloc2.cpp validateBufferDescriptorInfo() rechaza
# any bit outside the standard mask (getValid10/11UsageBits) -> BAD_VALUE
# -> the buffer is not allocated -> the EGL native window is invalid -> no composition.
#
# Fix (mechanism AOSP anticipates): TARGET_ADDITIONAL_GRALLOC_10_USAGE_BITS in
# BoardConfig -> soong_config -> -DADDNL_GRALLOC_10_USAGE_BITS in libui, which adds
# that bit to the valid mask. (Qualcomm use it for bits 10/13/21/27.)
# We add (1 << 25). Change in system.img (libui). boot unchanged. Idempotent.
import sys

F = "/home/lineage/android/lineage-17.1/device/samsung/gtexswifi/BoardConfig.mk"
s = open(F, encoding="utf-8", errors="surrogateescape").read()

if "TARGET_ADDITIONAL_GRALLOC_10_USAGE_BITS" in s:
    print("V26_PATCH_ALREADY_PRESENT"); sys.exit(0)

anchor = "# HWComposer\nUSE_SPRD_HWCOMPOSER := true\n"
block = (
    "# V26: el HWC Spreadtrum usa el bit de uso gralloc privado 0x2000000 (bit 25);\n"
    "# libui Gralloc2 lo rechazaria como invalido. Se anade a la mascara valida.\n"
    "TARGET_ADDITIONAL_GRALLOC_10_USAGE_BITS ?= 0\n"
    "TARGET_ADDITIONAL_GRALLOC_10_USAGE_BITS += | (1 << 25)\n\n"
)

if s.count(anchor) != 1:
    print("V26_PATCH_ANCHOR_ERROR count=%d" % s.count(anchor)); sys.exit(1)

s = s.replace(anchor, block + anchor)
open(F, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V26_PATCH_APPLIED")
