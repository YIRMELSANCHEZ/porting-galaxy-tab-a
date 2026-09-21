#!/usr/bin/env python3
# V29 (unblock graphics allocation). The gralloc is SOURCE. NOTE: the module
# gralloc.sc8830 is compiled from hardware/sprd/gralloc/SCX30G_V2 (NOT from sc8830;
# both define the same LOCAL_MODULE and scx30g_v2 wins). Verified by the build:
#   target thumb C++: gralloc.sc8830 <= hardware/sprd/gralloc/scx30g_v2/alloc_device.cpp
#
# Failure (V28): SF does not allocate its composition target:
#   GraphicBufferAllocator: Failed to allocate 800x1280 fmt 1 usage 1a00: 5 (NO_RESOURCES)
# usage 0x1a00 carries HW_FB -> gralloc_alloc_framebuffer_locked (page-flip on the fb
# legacy of 3 buffers). SF + HWC2OnFbAdapter share the fb and exhaust buffers -> -ENOMEM.
#
# Fix: force the ION COPY path for HW_FB (ION system heap buffer, always
# available; framebuffer post() does a memcpy to screen). + entry ALOGE log to
# see remaining EINVAL. Change in gralloc.sc8830 (system.img). boot unchanged. Idempotent.
import sys

F = "/home/lineage/android/lineage-17.1/hardware/sprd/gralloc/scx30g_v2/alloc_device.cpp"
s = open(F, encoding="utf-8", errors="surrogateescape").read()

if "V29" in s:
    print("V29_PATCH_ALREADY_PRESENT"); sys.exit(0)

fb_old = (
    "\tconst uint32_t bufferMask = m->bufferMask;\n"
    "\tconst uint32_t numBuffers = m->numBuffers;\n"
    "\tconst size_t bufferSize = m->finfo.line_length * m->info.yres;\n"
)
fb_new = (
    "\t// V29: forzar copia por ION para HW_FB. El page-flip del fb legacy agota\n"
    "\t// buffers (-ENOMEM) cuando SF y HWC2OnFbAdapter comparten el framebuffer.\n"
    "\t// ION system heap siempre aloca; framebuffer post() hace memcpy a pantalla.\n"
    "\t{\n"
    "\t\tsize_t v29Size = m->finfo.line_length * m->info.yres;\n"
    "\t\tint v29Usage = (usage & ~GRALLOC_USAGE_HW_FB) | GRALLOC_USAGE_HW_2D;\n"
    "\t\tALOGE(\"V29: HW_FB via ION copy, size=%zu usage=0x%x\", v29Size, v29Usage);\n"
    "\t\treturn gralloc_alloc_buffer(dev, v29Size, v29Usage, pHandle);\n"
    "\t}\n\n"
    "\tconst uint32_t bufferMask = m->bufferMask;\n"
    "\tconst uint32_t numBuffers = m->numBuffers;\n"
    "\tconst size_t bufferSize = m->finfo.line_length * m->info.yres;\n"
)

en_old = (
    "\t// ALOGD_IF(mDebug,\"alloc buffer start w:%d h:%d format:0x%x usage:0x%x\",w,h,format,usage);\n"
)
en_new = (
    "\t// ALOGD_IF(mDebug,\"alloc buffer start w:%d h:%d format:0x%x usage:0x%x\",w,h,format,usage);\n"
    "\tALOGE(\"V29 alloc: w=%d h=%d format=0x%x usage=0x%x\", w, h, format, usage);\n"
)

for old in (fb_old, en_old):
    if s.count(old) != 1:
        print("V29_ANCHOR_ERROR count=%d for: %s" % (s.count(old), old.splitlines()[0])); sys.exit(1)

s = s.replace(fb_old, fb_new).replace(en_old, en_new)
open(F, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V29_PATCH_APPLIED")
