# Phase 6 -- Graphics performance: display capped at ~8fps (pending optimization)

Date: 2026-09-19. Diagnosis on V55/V56.

## Symptom
Everything (UI and video) looks jerky. The user reports "incorrect" video in the browser.

## Measurement
- `gralloc.sc8830: fb_post fps` = **~8.4 fps** consistently, both in video and scrolling the launcher, WITH
  and WITHOUT the browser -> it is a GLOBAL display limit, not the video or the browser.
- `dumpsys SurfaceFlinger`: VSYNC period = 16.67ms = **60Hz** (the framework thinks 60Hz; the panel is
  800x1280p-60). Layer composition = **CLIENT (GPU)** (SurfaceFlinger composes with the Mali-400 into a
  buffer; the HWC dumps that buffer).
- `top` during scroll (no browser): **hwcomposer.sc8830 (pid 217) at ~84% CPU**; surfaceflinger ~6%. ->
  the HWC spends ~100ms of CPU per frame.
- Framebuffer: 32bpp (no 16bpp dither), virtual_size 800x3840 (room for 3 buffers).
- The Jelly browser ADDITIONALLY saturates another CPU at ~105% (software video decode + Chromium render),
  worsening the case, but is NOT the cause of the 8fps.

## Cause
The SPRD HWC (hardware/sprd/hwcomposer, via HWC2On1Adapter) does NOT use the display controller's (DISPC)
hardware overlays or the 2D hardware blitter (GSP, sprd_gsp.sc8830). Instead: SurfaceFlinger composes on
the GPU (CLIENT) and fb_post (gralloc scx30g_v2/framebuffer_device.cpp) DUMPS the composed buffer to the
framebuffer via CPU (memcpy branch V34, because the buffer is not PRIV_FLAGS_FRAMEBUFFER -> it does not take
the fast page-flip-by-yoffset branch). That memcpy (reading uncached GPU memory) is pathologically slow
(~100ms/frame) -> 8fps.

It is the pending performance optimization from phase 5: there it was achieved that graphics WORKED
(visible animation, V34) but via the slow path (fb adapter + memcpy); the speed was never optimized.

## Optimization routes (to explore; significant effort)
1. **Page-flip without a copy**: have SurfaceFlinger compose directly into the framebuffer buffers
   (PRIV_FLAGS_FRAMEBUFFER, the 3 buffers of the 3840 virtual) so fb_post takes the FBIOPAN-by-yoffset
   branch (no memcpy). Requires reviewing the framebuffer buffer allocation in gralloc (scx30g_v2) and the
   numFramebuffers.
2. **DISPC overlays (composition DEVICE)**: have the SPRD HWC assign layers to the DISPC hardware overlays
   (composition=DEVICE) instead of CLIENT+memcpy. It is the "correct" path but the most complex (the SPRD
   HWC was never fully activated in this port).
3. **GSP blitter**: use sprd_gsp.sc8830 (2D hardware) for the final blit instead of a CPU memcpy.
4. Discarded: software dither (the panel is 32bpp, does not apply).

## Video/browser note
With the display at 8fps + the browser saturating the CPU with software decode, browser video is doubly
bad. To evaluate real video it helps to: (a) raise the display fps (this optimization), and (b) test with a
native player / the target app, not the browser.
