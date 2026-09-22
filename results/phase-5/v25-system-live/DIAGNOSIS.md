# Phase 5 -- V25: graphics MILESTONE. SF composes and powers the display; presentation missing (HWC)

Date: 2026-09-18. Source: `logcat -b all` live,
`results/phase-5/v25-system-live/logcat.txt` (3827 lines).

## MILESTONE: SurfaceFlinger works

The V25 `-impl` loaded. Success chain in logcat:

- composer@2.1-service loads the impl and opens the **real framebuffer**:
  `[Gralloc] using (fd=8) id=sprdfb xres=800 yres=1280 bpp=32 refresh=60Hz`.
- `SPRDHWComposer: GSP_GetCapability ok`, `getDisplayAttributes disp:0 800x1280`.
- **`SurfaceFlinger` registers its binder** (`service list`: `ISurfaceComposer`), and
  **no longer aborts** (previously SIGABRT). State: alive in `SyS_epoll_wait` (normal
  loop).
- `SurfaceFlinger: Setting power mode 2 on display 0` -> **display powered on**.
- `SurfaceFlinger` **launches bootanim** (`start bootanim from pid 232`); `bootanimation`
  (pid 334) running.

It is the biggest graphics advance so far: the HIDL composer/gralloc/mapper stack +
SurfaceFlinger is operational.

## Current blocker: the Spreadtrum HWC does not present frames

The screen stays on the logo because SPRDHWComposer cannot allocate its display-
plane buffer or create its GLES context:

```
W Gralloc3: mapper/allocator 3.x is not supported          (falls back to 2.0, ok)
E Gralloc2: buffer descriptor contains invalid usage bits 0x2000000
E SPRDHWComposer: SprdDisplayPlane cannot alloc buffer
E SPRDHWComposer: eglCreateWindowSurface: EGL error 0x300b (EGL_BAD_NATIVE_WINDOW)
E SPRDHWComposer: eglMakeCurrent: EGL error 0x3009 (EGL_BAD_MATCH)
E SPRDHWComposer: Couldn't create a working GLES context ... Init EGL ENV failed
```

Cause: SPRDHWComposer requests buffers with a **private usage bit 0x2000000** (bit 25).
`frameworks/native/libs/ui/Gralloc2.cpp` `validateBufferDescriptorInfo()` rejects
every bit outside the standard mask (`getValid10/11UsageBits`) -> `BAD_VALUE` -> the
buffer is not allocated -> the EGL native window is invalid (`EGL_BAD_NATIVE_WINDOW`) ->
the HWC's internal GLES compositor does not start -> nothing is presented.

## V26 (fix) -- allow the private usage bit

AOSP anticipates this: `TARGET_ADDITIONAL_GRALLOC_10_USAGE_BITS` (BoardConfig) ->
soong_config -> `-DADDNL_GRALLOC_10_USAGE_BITS` in libui, which adds the bit to the
valid mask (Qualcomm use it for bits 10/13/21/27).
`apply-v26-gralloc-usage-bit.py` adds `(1 << 25)`. Change in system.img (libui);
boot unchanged.

Expected success: the display-plane buffer is allocated, the HWC EGL starts,
SPRDHWComposer presents -> **visible boot animation** (end of the static logo).
If another private bit is rejected, add it likewise.

## Persistent secondary (does not block the UI): audioserver

`audioserver` SIGSEGV null-deref in a loop every ~5 s (audio HAL not registered).
Floods the log but does not prevent graphics. Attacked after having a UI.
