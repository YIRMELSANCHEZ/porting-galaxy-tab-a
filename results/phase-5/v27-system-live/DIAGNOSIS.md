# Phase 5 -- V27: FB adapter active, but framebuffer 0x0; V28 = dims via ioctl fb0

Date: 2026-09-18. Source: `logcat -b all`,
`results/phase-5/v27-system-live/logcat.txt`.

## V27 result

The pivot worked at the path level: logcat shows
`I ComposerHal: V27: skipping HWC module; forcing gralloc/framebuffer adapter`
(in the composer service and in SF's in-process compositor). **All Spreadtrum HWC
errors disappear** (SprdPrimaryPlane, EGL). SF sets `power mode 2` and launches
bootanim without aborting.

## New blocker: dimensions 0x0

```
E BufferQueueProducer: [FramebufferSurface] allocateBuffers: failed to allocate
  buffer (0 x 0, format 1, usage 0x200)
```

`HWC2OnFbAdapter` (constructor) copies the size from the `framebuffer_device_t`:
```
mFbInfo.width  = mFbDevice->width;    // 0
mFbInfo.height = mFbDevice->height;   // 0
mFbInfo.vsync_period_ns = int(1e9 / mFbDevice->fps);  // fps 0 -> invalid
```
The `gralloc.sc8830` fb HAL **does not fill** width/height/fps of the
`framebuffer_device_t` (leaves them at 0). SF asks the adapter for the display
config -> 0x0 -> `FramebufferSurface` allocates 0x0 and fails -> no composition target -> logo.

The **sprdfb kernel DOES know** the panel (logcat: `sprdfb ... LCD Panel 0x5eb810 is
attached`, 800x1280).

## V28 (fix) -- read the dimensions from the kernel via fb0

`apply-v28-fbadapter-dims.py`: in the `HWC2OnFbAdapter` constructor, if
width/height/fps come as 0, open `/dev/graphics/fb0` (or `/dev/fb0`) and read
`FBIOGET_VSCREENINFO` (kernel xres/yres). Defaults: fps 60, format RGBA_8888,
dpi 160. `mFbInfo.vsync_period_ns` is computed at the end with a safe fps. Change in
composer@2.1-impl (system.img); boot unchanged.

Expected success: the adapter reports 800x1280 -> FramebufferSurface allocates fine -> SF
composes via GLES and presents to fb0 -> **visible boot animation**.

## Secondary (does not block the UI): audioserver SIGSEGV in a loop (audio HAL).
