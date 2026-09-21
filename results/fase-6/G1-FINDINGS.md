# G1 -- Graphics performance (~8 fps) and screenshot failure (GFX-ION): analysis and fixes

Date: 2026-09-20 (HW on V74). Deliverables: **V75** (kernel: binder FDA) and **V76** (V75 + cacheable
gralloc FB target). Method: measure first, hypothesize later; everything below is measured on HW except
where "to read" is noted.

## 0. Executive summary

| Problem | Root cause (measured) | Fix | Ver. |
|---|---|---|---|
| Capture "could not be saved" (GFX-ION) | ~1 MB/s ION memory leak in the composer -> `GraphicBufferAllocator NO_RESOURCES` -> `EGL_BAD_ALLOC` -> null bitmap | binder closes the `BINDER_TYPE_FDA` fds | V75 |
| +649 `sync_fence` fds/20 s in the composer, +305 in SF (crash from fds in hours) | same cause: nobody closes the fds received over hwbinder | same | V75 |
| ~8 fps globally | `fb_post` copies 4 MB/frame from **uncached** ION memory (~100 ms) | cacheable FB target ION (`SW_READ`) | V76 |

## 1. Graphics pipeline inventory (measured)

- Panel 800x1280@60, fb0 32 bpp, `virtual 800x3840` (3 slots), `fb_mem = 0xBB8000` = 3x4 MB (dts).
- HWC active: `HWC2On1Adapter` -> **SPRD HWC1 1.4 built from source** (`hwcomposer.sc8830`), with
  `sprd_gsp.sc8830` loaded. `libhwc2onfbadapter` is linked but unused.
- gralloc: `hardware/sprd/gralloc/scx30g_v2` (source), `USE_UI_OVERLAY`, no ADF, no UMP (DMA-BUF/ION).
- SurfaceFlinger: `RUNNING_WITHOUT_SYNC_FRAMEWORK=1`, `NUM_FRAMEBUFFER_SURFACE_BUFFERS=3`,
  `PresentFenceIsNotReliable`. All layers **CLIENT** (the GPU composes into the FB target).
- Presentation path: `SprdPrimaryDisplayDevice::commit` -> `HWCBufferSyncBuild` (kernel fences via a
  custom ION ioctl) -> `FRAMEBUFFER_TARGET` case -> `fbDev->post()` (gralloc `fb_post`).
- `fb_post`: if the handle is `PRIV_FLAGS_FRAMEBUFFER` -> `FBIOPAN_DISPLAY` by `yoffset` (real page-flip);
  otherwise -> **`memcpy` of `line_length*yres` = 4 MB + FBIOPAN(yoffset 0)** (V34 branch).
- **V29** (`alloc_device.cpp:320`) unconditionally turns every `HW_FB` request into an ION buffer
  (`v29Usage = usage & ~HW_FB | HW_2D`) -> always the memcpy branch. Historical reason (ARTIFACTS): V33
  tried the page-flip and got a real `-ENOMEM`.
- Measurements: `fb_post fps` 2.7 idle / 8-11 with scroll; composer `HwBinder` threads ~40% + ~39% CPU
  during scroll (the memcpy runs in the `present` thread).

## 2. Leaks (the cause of the screenshot failure)

### 2.1 Measurement
In 20 s of continuous scroll:
- composer `sync_fence` 4382 -> 5031 (**+649**), SF 2294 -> 2599 (**+305**).
- ION `system` "total orphaned" 437.9 -> 463.1 MB (**+25 MB = 6 buffers of 4 MB**); `Lost RAM` ~ total
  orphaned ION (438 MB) -> it is graphics buffer memory with no live owner.
- `/sys/kernel/debug/sync`: 7365 live fences: **4950 `mali_flag_fence`** (layer acquire) and **2406
  `HWCRetire`** (one per frame since boot; all `signaled`).
- SF/composer `nofile` limit = 32768 -> at this rate they die in 2-3 h of use (faster with more
  layers/fps).

### 2.2 Attribution by restart (not by inference)
- `kill surfaceflinger` -> `HWCRetire` 2526 -> 111: **SF held the present fences**.
- `stop/start vendor.hwcomposer-2-1` -> `mali_flag_fence` 5411 -> 13 and **ION 500 MB -> 80 MB**: **the
  composer held the acquire fences and the imported buffer handles** (pinned memory).
- What each process leaks is exactly what it **receives over hwbinder**: fences (`setLayerBuffer`,
  `setClientTarget`, `presentDisplay`) and buffer handles.

### 2.3 Root cause: ownership of the `BINDER_TYPE_FDA` fds
- `system/libhwbinder/Parcel.cpp` `release_object()`: `case BINDER_TYPE_FDA: // The enclosed file
  descriptors are closed in the kernel` -> userspace does **not** close (it duplicates what it keeps:
  `readFence()` does `dup`, `importBuffer` clones the handle).
- Upstream kernel `binder_transaction_buffer_release()`: `case BINDER_TYPE_FDA` closes all the array fds
  with `task_close_fd()` when the buffer is freed (BC_FREE_BUFFER).
- Local backport **V31** in `drivers/staging/android/binder.c`:
  `case BINDER_TYPE_FDA: /* V31: fd array, the receiver closes the fds */ break;` -> **nobody closes**.
- Chain up to the capture: ION leak -> `lowmemorykiller` active after boot ->
  `GraphicBufferAllocator: Failed to allocate (554x391) usage 702: 5` (NO_RESOURCES) -> `AHardwareBuffer
  failed (Out of memory)` -> `EGL_BAD_ALLOC` -> `SurfaceControl.screenshot()` null ->
  `NullPointerException createAshmemBitmap()` (`GlobalScreenshot.java:249`) -> `systemui:screenshot` dies
  -> "could not be saved".

### 2.4 V75 fix (`apply-v75-kernel... binder-fda-close.py`, boot.img only)
Implements the FDA case of `binder_transaction_buffer_release` like upstream: validates the parent
(`BINDER_TYPE_PTR`, already fixed to the receiver's user address), converts it with
`proc->user_buffer_offset` and closes each fd with `task_close_fd(proc, ...)`. `proc` is the receiver in
the normal free and `target_proc` in the sender's failure path (fds already installed), same as upstream.
Checked: userspace (libhwbinder/libhidl) has no V31 changes -> no double close.

**Verify after flashing:** `ls /proc/$(pidof surfaceflinger)/fd | wc -l` and the composer's stable after 1
min of scroll; `grep "total orphaned" /sys/kernel/debug/ion/heaps/ion_heap_system` stable; `dumpsys
meminfo | grep "Lost RAM"` low; capture after boot OK.

## 3. The 8 fps

### 3.1 Why the fb-slot page-flip (V33) cannot work on A10
- The `HW_FB` buffers are requested by SF from the **allocator@2.0 in another process**; the passthrough
  (`Gralloc0Hal.h`) does `freeBuffers()` as soon as it returns the handle -> `gralloc_free` clears the
  slot (`bufferMask`) -> the next `alloc` reuses the same slot (aliasing) and any reallocation ends in
  `-ENOMEM`/corruption. On 5.1 SF and HWC allocated in the same process.
- Also, in DMA-BUF mode without UMP a `PRIV_FLAGS_FRAMEBUFFER` handle has no `share_fd`: Mali cannot render
  into fb memory from SF. -> Route discarded with reason.

### 3.2 Where the time really goes
The destination (fb, write-combining) is not the bottleneck; the **source** is: the FB target ION is
allocated without `SW_*` bits -> `ion_flag = 0` -> **uncached** -> CPU read at ~40 MB/s -> ~100 ms per
frame.

### 3.3 V76 fix (`apply-v76-gralloc-cached-fbtarget.py`, system.img)
`v29Usage |= GRALLOC_USAGE_SW_READ_RARELY` -> ION `CACHED|CACHED_NEEDS_SYNC`. Correct because
`gralloc_lock()` with `SW_READ` already does `ion_invalidate_fd` (the GPU writes via its path, the CPU
only reads) and `gralloc_unlock()` does `ion_sync_fd`; `fb_post` already locks the source with
`SW_READ_RARELY`. Expected cost: 4 MB invalidate (~1-2 ms) + cached memcpy (~3-5 ms). **Verify:** `logcat
| grep "fb_post fps"` with scroll (previously 8-11); composer `HwBinder` CPU.

### 3.4 Next step if more is needed (to read/decide): zero-copy via the DISPC OSD plane
The kernel supports `SPRD_FB_SET_OVERLAY`/`SPRD_FB_DISPLAY_OVERLAY` (OSD/IMG) and the HWC already has
`SprdPrimaryPlane` (2 buffers of 4 MB in the `overlay` carveout = the "8 MB orphaned" of the ION), but
`attachToDisplayPlane` only uses the primary plane with **OSD+video** (or
`DIRECT_DISPLAY_SINGLE_OSD_LAYER`) and `revisitGeometry` disables it without a GSP accelerator. To present
the FB target without a copy: allocate the `HW_FB` in a contiguous heap (enlarge `sprd,ion-heap@3` from 8
to >=20 MB in the dts) and send the FB target via the OSD plane with its physical address (or GSP blit).
It is a major change (HWC + gralloc + dts) and only worth it if V76 is not enough for the app.

## 3.5 Measured HW result with V76 (2026-09-20, uptime 7 min)
| Metric | Before (V74) | After (V76) |
|---|---|---|
| SF / composer `sync_fence` fds after 30 s of scroll | +305 / +649 | 19->14 / 7->7 (**stable**) |
| ION `system` orphaned | grows ~1 MB/s (500 MB) | 58->46 MB (stable) |
| `Lost RAM` | 438 MB | **38 MB** (Free RAM 909 MB) |
| Live fences in `/sys/kernel/debug/sync` | 7365 | 15-20 |
| `fb_post fps` with scroll | 8-11 | **17-18.5** |
| composer `HwBinder` thread CPU (scroll) | ~42% + ~39% | ~9% + 6% + 3% |
| Capture after boot / with gallery | NPE crash | **OK** (230 KB / 179 KB, 0 errors) |
| Regressions (storage V74, BT, wcnd, sensors, WiFi) | -- | no regression |

**Where the limit is now:** the app's own render. `gfxinfo` of the launcher during scroll: median 44
ms/frame, p90 65 ms, 95% janky, 244 "Slow issue draw commands" (Mali-400 GPU with overdraw at
800x1280x32) and 163 "Slow UI thread" (Cortex-A7). The display no longer caps: `fb_post` keeps up with the
app (17-18 fps ~ the ~22 fps the launcher produces). The OSD/DISPC step (section 3.4) would save ~15% of
composer CPU and ~5 ms of latency per frame, but **not** the app's 44 ms of drawing; it only makes sense
if the target app needs it after measuring it.

Minor pending observed: new MediaStore rows stay `_size=NULL` until a scan (the capture is visible and
opens fine); publishing with `IS_PENDING->0` does not trigger the `scanFile`.

## 4. Noise/useful data
- `/sys/kernel/debug/ion/heaps/*`: "orphaned" = buffers whose client closed its handle after sharing them
  (normal with allocator@2.0); their unbounded growth is the leak.
- Restarting the composer (`stop/start vendor.hwcomposer-2-1`) restarts SF: useful to measure deltas.
- `toybox mount -o remount` requires source and `-t`; `nsenter -t <pid> -m` works.
