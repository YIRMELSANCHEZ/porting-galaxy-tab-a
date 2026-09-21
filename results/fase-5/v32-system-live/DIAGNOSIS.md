# Phase 5 -- V32: GRAPHICS COMPOSES AND POSTS (fb_post 14fps). ion_invalidate -> V33

Date: 2026-09-18. Source: `logcat -b all` + `dumpsys SurfaceFlinger` + `dmesg`,
`results/fase-5/v32-system-live/logcat.txt`.

## MILESTONE: SurfaceFlinger composes and posts to the framebuffer

- The usage bit 0x400 error (client) disappeared (only a non-fatal WARNING remains
  `MapperHal: invalid usage bits 0x400`). The bootanim buffer **is allocated**.
- `BootAnimation: BootAnimationShownTiming` -> the animation is rendered.
- `dumpsys SurfaceFlinger`: Display 0 powerMode=2, **composes the BootAnimation#0 layer**
  (composition type DEVICE), active 800x1280 RGBA buffer, VisibleRegion [0,0,800,1280].
- **`gralloc.sc8830: fb_post fps = 14.4`** -> SF **posts frames to the fb** at ~14 fps.

The whole graphics pipeline works: alloc -> binder (FDA, V31) -> GLES composition
-> post to the framebuffer.

## Remaining blocker: ion_invalidate on each post -> stale screen

```
kernel: ion_invalidate_for_cpu: dmabuf is error and dmabuf is fffffff7   (-9 EBADF)
```
On each `fb_post`, the CPU cache sync of the ION buffer fails (invalid dmabuf). The
cause is the **V29** hack (HW_FB buffers via ION + memcpy on post). The memcpy copies
data without synchronizing -> the fb receives stale content -> the uboot logo is shown
instead of the animation.

## V33 (fix) -- revert V29 (native page-flip)

V29 is NO longer needed: the "-ENOMEM" that motivated it was actually the binder FDA
failure (resolved in V31). `apply-v33-revert-v29-ioncopy.py` reverts the ION-copy block of
`gralloc_alloc_framebuffer_locked` (and cleans the V29/V30 logs). The framebuffer returns to its
**native page-flip** (FBIOPAN among the fb's 3 slots, no memcpy or ion_invalidate)
-> clean post. Keeps V31 (FDA) + V32 (usage). boot = V31 (unchanged); only system.

Expected success: fb_post without ION errors -> the framebuffer shows what SF composes ->
**boot animation VISIBLE on screen**. If page-flip gives some problem (e.g.
tearing or real -ENOMEM from >3 buffers), re-evaluate with a *properly synchronized* ION copy.

## Secondary: audioserver SIGSEGV in `AudioFlinger::AudioFlinger()` in a loop.
