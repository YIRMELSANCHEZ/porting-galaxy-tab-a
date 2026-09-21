# V88 -- SwiftAngle scaled EGL surface

Status: **OFFLINE PASS -- HARDWARE PENDING**
Date: 2026-09-21

## Cause demonstrated in V87

V87 called `native_window_set_buffers_dimensions(640,400)`, but `WindowSurface::checkForResize()` still
queried and used the logical size 1280x800. `FrameBufferAndroid::lock()` receives the 640x400 buffer and
considers it smaller than its 1280x800 framebuffer; no frame is queued. SurfaceFlinger showed the logical
layer black and a 640x400 buffer allocated, but `activeBuffer=0x0` in the SurfaceView.

When switching on hardware to `persist.swiftangle.scale=1` and restarting only the target app, the
SurfaceView went to `activeBuffer=1280x800 RGBA_8888` and the login appeared after about a minute.

## V88 fix

- `WindowSurface` keeps the original logical dimensions when constructed.
- `checkForResize()` computes the reduced size and calls `native_window_set_buffers_dimensions()` there.
- The EGL backbuffer, the SwiftShader FrameBuffer and the gralloc buffer share 640x400 at scale 2.
- SurfaceFlinger keeps the 1280x800 target layer and does the upscale.
- Scale 1 is still the no-reduction compatibility path.

## Artifact

`sm-t280-phase6/packages/SM-T280-android10-swiftangle-scaled-egl-PHASE6-v88-DO-NOT-FLASH.tar.md5`

SHA-256:

`0a5a359433bf91203e9623afb59382829b2a1f7d7ef93956f1cb8bb8e2607565`

Offline results:

- `V88_STATIC_VERIFY_PASS`
- `ODIN_SYSTEM_PACKAGE_PASS`
- `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`
- `V88_BUILD_AND_PACKAGE_PASS`
- Exact content: `boot.img` V75 + `system.img` V88.

## Pending test sequence

1. Confirm the physical state before any action.
2. The user flashes the package in Odin AP, Auto Reboot OFF, no PIT/Re-Partition.
3. Boot and first check that persistent scale `1` keeps the visible behavior.
4. With authorization, switch to scale `2` and restart only the target app.
5. Confirm `activeBuffer=640x400`, visible image, aligned touch, video and login.
6. Compare time to login, frame time, CPU and temperature against scale 1.
