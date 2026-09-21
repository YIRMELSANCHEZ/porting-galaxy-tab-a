# Phase 5 -- V24: logcat RECOVERED. Logo cause isolated; V25 = graphics -impl

Date: 2026-09-18. Source: **`logcat -b all`** live (at last), saved in
`results/fase-5/v24-system-live/logcat.txt` (4978 lines).

## Milestone: V24 fixes logd -> live logcat

`init.svc.logd=running`, `/dev/socket/logd*` created, `logcat` flows. The chain
V22->V23->V24 (see `v22-`/`v23-system-live/DIAGNOSIS.md`) is closed. With full
visibility, the real blockers are isolated.

## Root blocker of the logo: SurfaceFlinger SIGABRT

```
E composer@2.1-service: Could not get passthrough implementation for
    android.hardware.graphics.composer@2.1::IComposer/default.
init: Service 'vendor.hwcomposer-2-1' exited with status 1
...
F HwcComposer: failed to get hwcomposer service
F libc: Fatal signal 6 (SIGABRT) in surfaceflinger
init: Command 'restart zygote' ... (SF onrestart) -> restarts zygote -> loop
```

The `-service` (V20) are **passthrough**: they load in-process the `-impl` lib that
wraps the blob. On the device (verified by `ls`):

- Present: `gralloc.sc8830.so`, `hwcomposer.sc8830.so` (blobs), the `-service`,
  and `mapper@2.0-impl` (V20).
- **MISSING** the passthrough `-impl`:
  - `android.hardware.graphics.composer@2.1-impl` (brings `libhwc2on1adapter` ->
    wraps the HWC1 `hwcomposer.sc8830.so`)
  - `android.hardware.graphics.allocator@2.0-impl` (wraps gralloc0)

`device.mk` (V20) added the `-service` and the mapper impl, but **not** the
composer/allocator impls. Without them, the passthrough service has nothing to load.

## V25 (fix) -- add the missing -impl

`apply-v25-graphics-impl.py`: adds to PRODUCT_PACKAGES
`android.hardware.graphics.allocator@2.0-impl` and
`android.hardware.graphics.composer@2.1-impl` (vendor -> /vendor/lib/hw). The
composer impl includes `libhwc2on1adapter`/`libhwc2onfbadapter` (HWC1->HWC2) and opens
`hwcomposer.sc8830.so` via `libhardware`. Change in system.img; boot unchanged.

Expected success: composer@2.1-service loads the impl, registers IComposer, SF gets
it and composes -> **boot animation** (milestone). Residual risk: the Spreadtrum HWC1
may fail to open the display inside the adapter (would show in the new logcat).

## Secondary blockers already identified (do NOT block the UI; after V25)

- `mediaserver`: `CANNOT LINK "/system/bin/mediaserver": cannot locate symbol
  "ion_is_legacy" referenced by "/system/lib/libcodec2_vndk.so"`. libion mismatch
  (blob vs AOSP). `media` status-1 loop.
- `audioserver` (pid 220): SIGSEGV null-deref; audio HALs
  (`android.hardware.audio@2.0/4.0/5.0::IDevicesFactory`) not registered/not
  found.
- Both are vendor HAL/blobs; they are attacked after having a UI (SF is the hard
  dependency of the graphics boot; media/audio degrade function but do not prevent
  the launcher).
