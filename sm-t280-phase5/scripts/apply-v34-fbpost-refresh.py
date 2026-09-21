#!/usr/bin/env python3
# V34. Reapplies V29 (ION alloc for HW_FB; the native page-flip gives real -ENOMEM,
# confirmed on reverting in V33) AND fixes the presentation:
#
# fb_post has 2 branches: page-flip (buffer PRIV_FLAGS_FRAMEBUFFER) that does
# FBIOPAN_DISPLAY -> the sprdfb latches the frame to the panel; and memcpy (ION buffer, the
# V29 one) that copies to the fb memory but does NOT do FBIOPAN -> the DPI dispc keeps
# showing the last latched frame (the uboot logo) even though the memcpy writes the
# new frame. That is why fb_post runs at 14fps but the screen does not change.
#
# V34 adds, after the memcpy+unlock of the else branch, FBIOPAN_DISPLAY (yoffset=0) to
# force the panel latch/refresh. (V29 is reapplied separately with its script.)
# Change in framebuffer_device.cpp (gralloc.sc8830 / system.img). boot = V31. Idempotent.
import sys

F = "/home/lineage/android/lineage-17.1/hardware/sprd/gralloc/scx30g_v2/framebuffer_device.cpp"
s = open(F, encoding="utf-8", errors="surrogateescape").read()

if "V34" in s:
    print("V34_ALREADY_PRESENT"); sys.exit(0)

old = (
    "\t\tmemcpy(fb_vaddr, buffer_vaddr, m->finfo.line_length * m->info.yres);\n"
    "\n"
    "\t\tm->base.unlock(&m->base, buffer);\n"
    "\t\tm->base.unlock(&m->base, m->framebuffer);\n"
    "\t}\n"
)
new = (
    "\t\tmemcpy(fb_vaddr, buffer_vaddr, m->finfo.line_length * m->info.yres);\n"
    "\n"
    "\t\tm->base.unlock(&m->base, buffer);\n"
    "\t\tm->base.unlock(&m->base, m->framebuffer);\n"
    "\n"
    "\t\t/* V34: la rama memcpy no hacia FBIOPAN -> el panel DPI no latcheaba el frame\n"
    "\t\t * nuevo. Forzar el refresco/latch del sprdfb desde el offset 0. */\n"
    "\t\tm->info.yoffset = 0;\n"
    "\t\tif (ioctl(m->framebuffer->fd, FBIOPAN_DISPLAY, &m->info) == -1) {\n"
    "\t\t\tAERR(\"V34 FBIOPAN_DISPLAY (memcpy path) failed for fd: %d\", m->framebuffer->fd);\n"
    "\t\t}\n"
    "\t}\n"
)

if s.count(old) != 1:
    print("V34_ANCHOR_ERROR count=%d" % s.count(old)); sys.exit(1)

s = s.replace(old, new, 1)
open(F, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V34_APPLIED")
