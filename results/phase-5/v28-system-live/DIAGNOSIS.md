# Phase 5 -- V28: dims OK (800x1280); gralloc is SOURCE; HW_FB alloc exhausts fb; V29

Date: 2026-09-18. Source: `logcat -b all` + tree review.

## V28 result

The ioctl fallback to `/dev/graphics/fb0` **worked**: SF now tries to allocate at
**800x1280** (previously 0x0). But the composition target allocation fails:

```
E GraphicBufferAllocator: Failed to allocate (800 x 1280) fmt 1 usage 1a00: 5 (NO_RESOURCES)
E GraphicBufferAllocator: Failed to allocate (800 x 1280) fmt 1 usage f02: -22 (EINVAL)
E BufferQueueProducer: [BootAnimation#0] dequeueBuffer: createGraphicBuffer failed
```

## KEY FINDING: the gralloc (and the HWC) are SOURCE, not blobs

`BoardConfig`: `TARGET_USE_PREBUILT_GRALLOC := false`. In the tree:
- `hardware/sprd/gralloc/sc8830/` -- **gralloc.sc8830 from source** (alloc_device.cpp...)
- `hardware/sprd/hwcomposer/SprdPrimaryDisplayDevice/` -- the **SPRD HWC from source**
- `hardware/sprd/libion_sprd/sc8830/` -- the SPRD ION from source

-> The whole SPRD graphics stack is **patchable**. (Reinterprets previous findings that
treated it as a blob.)

## Cause of the HW_FB failure (usage 0x1a00 -> error 5)

`alloc_device.cpp` `gralloc_alloc_framebuffer_locked`: uses **page-flip** on the
legacy framebuffer. `yres_virtual=3840 / yres=1280 = 3 buffers`. SF and
`HWC2OnFbAdapter` **share** the fb and exhaust the 3 -> `bufferMask` full ->
`-ENOMEM` (mapped to NO_RESOURCES=5). There is no `[Gralloc-ERROR]` because that
branch does not log. (The `ion_alloc` of gralloc_alloc_buffer is NOT reached on this
path.)

## V29 (fix) -- ION copy for HW_FB

**IMPORTANT (gralloc directory):** the `gralloc.sc8830` module is compiled from
`hardware/sprd/gralloc/**scx30g_v2**/alloc_device.cpp`, NOT from `sc8830/` (both
define `LOCAL_MODULE := gralloc.$(TARGET_BOARD_PLATFORM)` and scx30g_v2 wins).
Confirmed by the build log: `gralloc.sc8830 <= .../gralloc/scx30g_v2/alloc_device.cpp`.
gralloc patches go to **scx30g_v2**.

`apply-v29-gralloc-fb-ion.py`: in `gralloc_alloc_framebuffer_locked`, force the ION
COPY path (the gralloc already has it for numBuffers==1): allocate a normal buffer
from the **ION system heap** (always available, 1.35GB free) and let
`framebuffer post()` do a memcpy to screen. Robust, without page-flip contention.
Also, an entry log `ALOGE("V29 alloc: ...")` always active to see any remaining
EINVAL (e.g. the bootanim buffer usage 0xf02, error -22, still without a confirmed
cause). Change in gralloc.sc8830 (system.img); boot unchanged.

Expected success: SF allocates its composition target -> composes via GLES -> posts to fb0 ->
**visible boot animation**. If the 0xf02 (bootanim) stays at -22, the `V29 alloc` log
will say where it stops for the next fix.

## Secondary (does not block the UI): audioserver SIGSEGV in `AudioFlinger::AudioFlinger()`
(constructor, null deref) in a loop every 5s; audio HAL. Floods dmesg. Later.
