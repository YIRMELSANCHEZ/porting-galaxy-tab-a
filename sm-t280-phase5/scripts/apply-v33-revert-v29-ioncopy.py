#!/usr/bin/env python3
# V33. With V31 (FDA) + V32 (usage bits) the graphics composes and posts (fb_post fps=14,
# dumpsys: composed BootAnimation layer). BUT each post gives:
#   kernel: ion_invalidate_for_cpu: dmabuf is error ... fffffff7 (-9 EBADF)
# = the cache sync of the ION buffer fails on the memcpy to the fb -> stale data on
# screen. The cause is the V29 hack (HW_FB buffers via ION + memcpy). V29 is NO longer
# needed: the "-ENOMEM" that motivated V29 was actually the binder FDA failure (resolved
# in V31). Reverting V29, the framebuffer uses its native PAGE-FLIP (FBIOPAN, no memcpy
# nor ION) -> clean post.
#
# V33 revierte, en hardware/sprd/gralloc/scx30g_v2/alloc_device.cpp:
#  - the V29 ION-copy block in gralloc_alloc_framebuffer_locked (restores page-flip)
#  - the V29/V30 diagnostic ALOGE (cleanup). Keeps V31/V32.
# Change in system.img (gralloc); boot = V31 (unchanged). Idempotent.
import sys

F = "/home/lineage/android/lineage-17.1/hardware/sprd/gralloc/scx30g_v2/alloc_device.cpp"
s = open(F, encoding="utf-8", errors="surrogateescape").read()

removed = 0

# 1) V29 ION-copy block (early return in the fb path)
v29blk = (
    "\t// V29: forzar copia por ION para HW_FB. El page-flip del fb legacy agota\n"
    "\t// buffers (-ENOMEM) cuando SF y HWC2OnFbAdapter comparten el framebuffer.\n"
    "\t// ION system heap siempre aloca; framebuffer post() hace memcpy a pantalla.\n"
    "\t{\n"
    "\t\tsize_t v29Size = m->finfo.line_length * m->info.yres;\n"
    "\t\tint v29Usage = (usage & ~GRALLOC_USAGE_HW_FB) | GRALLOC_USAGE_HW_2D;\n"
    "\t\tALOGE(\"V29: HW_FB via ION copy, size=%zu usage=0x%x\", v29Size, v29Usage);\n"
    "\t\treturn gralloc_alloc_buffer(dev, v29Size, v29Usage, pHandle);\n"
    "\t}\n\n"
)
if v29blk in s:
    s = s.replace(v29blk, "", 1); removed += 1

# 2) V29/V30 diagnostic logs
for line in (
    "\tALOGE(\"V29 alloc: w=%d h=%d format=0x%x usage=0x%x\", w, h, format, usage);\n",
    "\t\tALOGE(\"V30 ion_alloc: heap=0x%x size=%zu flag=0x%x ret=%d client=%d\", ion_heap_mask, size, ion_flag, ret, m->ion_client);\n",
    "\tALOGE(\"V30 alloc_device_alloc OK: w=%d h=%d fmt=0x%x usage=0x%x stride=%zu\", w, h, format, usage, (size_t)stride);\n",
):
    if line in s:
        s = s.replace(line, "", 1); removed += 1

if removed == 0:
    print("V33_NOTHING_TO_REVERT (already clean?)"); sys.exit(0)

open(F, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V33_APPLIED removed_blocks=%d ; remaining V29/V30 markers=%d" % (removed, s.count("V29")+s.count("V30")))
