#!/usr/bin/env python3
# V76 (G1: display capped at ~8 fps). On top of V75 (kernel). Changes gralloc.sc8830 (scx30g_v2) -> system.img.
#
# CAUSE (see results/phase-6/G1-FINDINGS.md):
#   V29 forces every HW_FB buffer (SurfaceFlinger's 3 FramebufferSurface = "FB target",
#   the GPU composition output) to be a normal ION buffer instead of a framebuffer slot,
#   so fb_post() in the composer always takes the memcpy branch: it copies 800x1280x4 = 4 MB per
#   frame to the fb memory (uncached, write-combining) and then FBIOPAN. The destination is not the
#   problem: it is the SOURCE. gralloc_alloc_buffer() only requests ION_FLAG_CACHED when the usage
#   carries SW_READ/SW_WRITE bits, and v29Usage does not carry them -> the FB target is UNCACHED memory and
#   the memcpy reads it at ~40 MB/s -> ~100 ms per frame -> ~8 global fps (measured: fb_post fps 8-11,
#   the composer's HwBinder at 80 % CPU during scroll).
#
# FIX: request the FB target cacheable (SW_READ_RARELY). It is consistent with the cache maintenance that
#   gralloc already does: gralloc_lock() with SW_READ -> ion_invalidate_fd() before the CPU reads (the
#   GPU writes by its own path) and gralloc_unlock() -> ion_sync_fd(). fb_post() already locks the
#   source with GRALLOC_USAGE_SW_READ_RARELY. The CPU never writes to that buffer. Cost: a 4 MB
#   invalidate per frame (~1-2 ms) versus ~100 ms of uncached reading.
# Idempotente. Verificar: logcat "fb_post fps" durante scroll (antes 8-11).
import sys
from pathlib import Path

SRC = Path("/home/lineage/android/lineage-17.1/hardware/sprd/gralloc/scx30g_v2/alloc_device.cpp")

OLD = """		int v29Usage = (usage & ~GRALLOC_USAGE_HW_FB) | GRALLOC_USAGE_HW_2D;
"""
NEW = """		/* V76: cacheable (SW_READ) -> gralloc_lock hace ion_invalidate_fd y el memcpy de
		 * fb_post lee memoria con cache en vez de uncached (~100 ms/frame -> ~8 fps). */
		int v29Usage = (usage & ~GRALLOC_USAGE_HW_FB) | GRALLOC_USAGE_HW_2D |
		               GRALLOC_USAGE_SW_READ_RARELY;
"""

s = SRC.read_text(encoding="utf-8", errors="surrogateescape")
if "V76: cacheable" in s:
    print("V76_ALREADY"); sys.exit(0)
if s.count(OLD) != 1:
    print("V76_ERROR: V29 block not found exactly once"); sys.exit(1)
SRC.write_text(s.replace(OLD, NEW, 1), encoding="utf-8", errors="surrogateescape")
print("V76_APPLIED -> FB target ION cacheable (SW_READ_RARELY)")
