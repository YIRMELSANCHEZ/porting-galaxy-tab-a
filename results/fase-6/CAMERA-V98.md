# Camera (CAM1 -> V98) -- diagnosis and state 2026-09-21

Prompted by "I have no camera app". The icon was missing because `Camera2` disables itself when
`getNumberOfCameras()` returns 0 (`SetActivitiesCameraReceiver`), and the camera provider was not
starting. Investigated live on V95 (flashed). Nothing was reflashed; this session's changes live in RAM
or in `/system` via remount and are not part of any package yet.

## Two causes found (both software)

1. **Android 10's linker no longer supports `LD_SHIM_LIBS`.** The V92 shim (`libcamera_shim.so`, which
   provides `android_atomic_or` for the 5.1 blob `libmemoryheapion.so`) was never loaded, and
   `camera.sc8830.so` failed in `dlopen` ("cannot locate symbol android_atomic_or"). Checked:
   `grep -c LD_SHIM_LIBS` in the linker = 0. With `LD_PRELOAD` the shim does load and the HAL opens: it
   detects **2 cameras** and powers on the sensor (`sensor_s5k4ecgx`).

2. **SIGSEGV when opening the camera** in `CameraDevice::sGetMemory` (`camera.device@1.0-impl.so`). The
   Spreadtrum 5.1 HAL calls `get_memory` with `user=NULL` from its preallocation thread
   (`pre_alloc_cap_mem_thread`), and the HIDL wrapper dereferences NULL. V98 patch
   (`apply-v98-camera-null-user.py`): stores the opened instance in a static pointer and uses it when the
   HAL passes no `user`; it also guards `sGetMemory` against a null pointer. 10 lines, idempotent.

## State after V98 (live test)

- Provider `android.hardware.camera.provider@2.4-service` alive, **no crash**.
- `dumpsys media.camera`: **Number of camera devices: 2**. The HAL allocates capture memory (24 MB) via
  ION correctly; sensor with preview sizes up to 1280x960 and capture 2576x1932.
- `libGLESv2_angle.so` (SwiftAngle) is still exclusive to the target app; the camera uses the real
  Mali-400.

## What still does NOT work: the Camera2 app preview

The official app opens the camera (`onCameraOpened`) but the preview fails in its legacy GL path:

```
gralloc.sc8830: V29 alloc: w=1024 h=768 format=0x1 usage=0x702
GraphicBufferAllocator: Failed to allocate (1024 x 768) format 1 usage 702: 5
EGL: __egl_platform_dequeue_buffer failed; err = -12 (ENOMEM)
libEGL: eglMakeCurrentImpl error 3003 (EGL_BAD_ALLOC)
SurfaceTextureRenderer: Could not compile shader 35633  -> ERROR state
```

It is the `android.hardware.camera2.legacy` path (SurfaceTextureRenderer + gralloc). It fails to allocate
the SurfaceTexture RGBA buffer with `usage=0x702` in the SPRD gralloc (`ION_HEAP_ID_MASK_SYSTEM`), and
without the buffer the EGL context does not line up and the preview shader does not compile. It is a
problem **distinct** from the camera HAL: it affects the legacy shim's GL preview path over this
gralloc/Mali, not the sensor. Still to pin down: the usage-bit combination (`0x702`) that the SPRD gralloc
rejects for RGBA, or memory pressure (1.49 GB total, ~549 MB free, system ION heap with 65 MB orphaned
from previous sessions). Hypotheses to try next time: (a) force `HAL_PIXEL_FORMAT_YV12`/NV21 in the
preview SurfaceTexture, (b) review the `TARGET_ADDITIONAL_GRALLOC_10_USAGE_BITS` in BoardConfig against
`0x702`, (c) a pure API2 camera app does not apply (HAL1 device, only the legacy path exists).

## Preview: root cause (V96 flashed, 2026-09-21 20:40)

With V96 on HW (provider starting from init, not manual) and a clean boot, the HAL is still perfect
(`dumpsys media.camera` = 2, `startPreviewInternal` OK) but **no app shows a preview**. Both API paths
tested:

| app / path | failure | where |
|---|---|---|
| LineageOS Camera2 (camera2 -> legacy shim -> GL) | `gralloc V29 RGBA 1024x768 usage=0x702 -> NO_RESOURCES (5)`, then `EGL_BAD_ALLOC`, shader does not compile | allocation of the RGBA render-target of `SurfaceTextureRenderer` |
| Open Camera with the old API (`CameraController1`) | `GraphicBufferAllocator: format 17 (NV21) 1024x768 usage=0x24000930 -> -22 (EINVAL)` in the allocator, before reaching the SPRD gralloc; the HAL goes to `SPRD_ERROR`, `camera onError 100 SERVER_DIED` | allocation of the preview SurfaceView buffer |

**It is not an app problem or a memory problem** (it fails the same on a clean boot). It is the **gralloc**
layer: the device uses `android.hardware.graphics.allocator@2.0-impl` + `gralloc.default.so` wrapping the
legacy blob `gralloc.sc8830.so` (`hardware/sprd/gralloc/scx30g_v2`, Mali-400 utgard GPU). The buffers the
camera needs for the **preview surface** are rejected:
- API1 path: allocator@2.0 returns EINVAL for NV21 with camera usage `0x24000930` (it does not even reach
  the SPRD blob's alloc; it is the gralloc0 <-> HIDL usage-bit conversion).
- camera2-legacy path: the SPRD blob does receive the RGBA `0x702` but the ION allocation fails
  (NO_RESOURCES).

It is a gralloc porting bug on Android 10 for camera buffers, not a camera HAL bug (which already works).
It affects **every** camera app. The HAL's internal capture buffers (24 MB via direct ION with
`libmemoryheapion`) do work; what fails is the preview display buffer.

## Verdict

- **Camera hardware: recovered** (from 0 to 2 cameras, HAL opens and starts preview). Big progress.
- **Preview: blocked by the gralloc**, not the app. It is a deeper porting problem, distinct and separate
  from the HAL. It requires debugging the camera buffer allocation in `allocator@2.0-impl`/`gralloc.sc8830`
  (usage-bit conversion and ION path), with rebuild + reflash cycles and an uncertain outcome. It is
  separate research work.
- Open Camera is installed (API1), ready to retest as soon as the gralloc is fixed.

Leads to resume: (1) why `allocator@2.0-impl` (`Gralloc0Hal::allocateOneBuffer`) returns -22 for
NV21+usage `0x24000930`; compare the `TARGET_ADDITIONAL_GRALLOC_10_USAGE_BITS` (bits 10,13,21,25) in
BoardConfig against the high bits `0x24000000` of the camera. (2) why the SPRD blob's ION returns
NO_RESOURCES for the camera2-legacy RGBA (heap/usage mask in `gralloc_alloc_buffer`).

Files: `scripts/apply-v98-camera-null-user.py`, `scripts/build-v98-camera-test.sh`,
`apps/camera.device@1.0-impl-v98.so` (patched lib). The rc `zz-camera-provider-shim.rc` switches to
`LD_PRELOAD` (not rebuilt into a package yet).
