# Phase 5 -- V33: page-flip gives real -ENOMEM (V29 needed); V34 = FBIOPAN after memcpy

Date: 2026-09-18. Source: `logcat -b all`,
`results/phase-5/v33-system-live/logcat.txt`.

## V33 (revert V29) CONFIRMS that V29 was needed

Reverting V29 and returning to the native page-flip, the FramebufferSurface
allocation fails in a loop (60/s):
```
E GraphicBufferAllocator: Failed to allocate 800x1280 usage 1a00: 5 (NO_RESOURCES)
```
It is the REAL `-ENOMEM` of `gralloc_alloc_framebuffer_locked`
(`bufferMask >= (1<<numBuffers)-1`): the page-flip exhausts the fb's 3 slots and does not
recycle them with the FramebufferSurface+HWC2OnFbAdapter model. => **V29 (HW_FB buffers via
ION) is needed** for the allocation to succeed. (In V28 the "usage 1a00:5" was the SUM of
this + the FDA failure; V31 fixed FDA, but the page-flip -ENOMEM remains.)

## Cause of the "frozen logo" in V32 (with V29): fb_post does not refresh

`framebuffer_device.cpp fb_post` has 2 branches:
- **page-flip** (buffer PRIV_FLAGS_FRAMEBUFFER): does `FBIOPAN_DISPLAY` -> the sprdfb
  latches the frame to the panel.
- **memcpy** (V29 ION buffer, PRIV_FLAGS_USES_ION): `memcpy` to the fb memory and
  unlock, **without FBIOPAN**. The DPI panel keeps showing the last latched frame (the
  uboot logo) even though the memcpy writes the new frame. That is why `fb_post fps=14`
  but the screen does not change. (The `ion_invalidate ... fffffff7` error is NON-fatal:
  `gralloc_lock` ignores the return; `*vaddr=hnd->base` anyway.)

## V34 (fix)

Reapplies V29 (ION alloc) + `apply-v34-fbpost-refresh.py`: in the memcpy branch of fb_post,
after the memcpy+unlock, `m->info.yoffset=0; ioctl(fb, FBIOPAN_DISPLAY, &m->info)` to
force the panel latch/refresh from offset 0. Keeps V31 (FDA) + V32 (usage).
Change in gralloc.sc8830 (system.img); boot = V31 (unchanged).

Expected success: each fb_post latches the frame -> **boot animation VISIBLE**. If it still
does not show, review: (a) the panel offset/scan-out, (b) whether the memcpy reads correct
data (GPU->CPU sync of the ION buffer), (c) alternative: fix the page-flip's buffer
recycling to use the native path.
