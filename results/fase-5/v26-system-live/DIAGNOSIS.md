# Phase 5 -- V26: usage bit OK, but the SPRD HWC does not allocate (blob); V27 = FB adapter

Date: 2026-09-18. Source: `logcat -b all`,
`results/fase-5/v26-system-live/logcat.txt`.

## V26 result

The `ADDNL_GRALLOC_10_USAGE_BITS` flag **worked** in the client validator:
`I Gralloc2: Adding additional valid usage bits: 0x2000000`. The client error
`E Gralloc2: invalid usage bits 0x2000000` disappeared. (The `W MapperHal: invalid
usage bits` is only ALOGW, not a failure.)

## But the real failure was lower down: gralloc0 alloc() fails

```
E GraphicBufferAllocator: Failed to allocate (800 x 1280) layerCount 1 format 1
                          usage 3000000: 5
E SPRDHWComposer: SprdDisplayPlane cannot alloc buffer
E SPRDHWComposer: SprdPrimaryPlane::open failed
E SPRDHWComposer: eglCreateWindowSurface EGL_BAD_NATIVE_WINDOW -> Init EGL ENV failed
```

- usage = **0x3000000** = SPRD private bits 24 (0x1000000) + 25 (0x2000000).
- code **5 = NO_RESOURCES**. In the Gralloc0 passthrough allocator
  (`allocator/2.0/.../Gralloc0Hal.h` `allocateOneBuffer`): `mDevice->alloc(...)`
  returns `!=0` and `!=-EINVAL` -> NO_RESOURCES. That is, **the `gralloc.sc8830`
  blob itself fails in `alloc()`** for the HWC overlay buffer (the overlay/GSP ION
  heap is unavailable in this environment). It is inside the blob -> not patchable.

## Pivot V27 -- force the framebuffer adapter (avoid the SPRD HWC)

`composer@2.1-impl` (`HwcLoader.h`) chooses:
- HWC module present -> `HWC2On1Adapter` -> SPRD HWC1 (broken: overlay does not allocate).
- gralloc only -> `framebuffer_open` -> **`HWC2OnFbAdapter`** (SurfaceFlinger composes
  in its GLES RenderEngine and presents to fb0).

`apply-v27-force-fb-adapter.py`: `HwcLoader::loadModule()` skips
`hw_get_module(HWC)` and uses gralloc directly -> HWC2OnFbAdapter. SF already has EGL
GLES working (RenderEngine EGL 1.4 Mali) and fb0 (sprdfb) opens fine; only the blob's
overlay is avoided. Change in composer@2.1-impl (system.img); boot unchanged.

Expected success: SF composes via GLES and presents to fb0 -> **visible boot
animation**. It is software/GPU composition (not HW overlay), slower but robust to
reach the UI; the native HWC can be optimized later.

## Secondary (does not block the UI): audioserver SIGSEGV in a loop (audio HAL).
