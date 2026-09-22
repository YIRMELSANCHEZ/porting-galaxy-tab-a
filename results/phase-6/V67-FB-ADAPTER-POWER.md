# V67 -- HWC2 framebuffer adapter with real off/on

Status: **HARDWARE PASS; OFF/ON AND OFF->ON RACE VALIDATED**

## Hardware diagnosis of V66

V66 booted correctly and the device exposed via ADB:

- kernel `3.10.108-g95996f39350-dirty #28` (boot V66 confirmed);
- `sys.boot_completed=1`;
- Android `Awake`, logical display `ON` and backlight `143`;
- no `V66 HWC power-mode` message in all of `dmesg` after the tests.

Inspecting `/proc/<composer-pid>/maps` showed that the Composer service does not load
`/system/lib/hw/hwcomposer.sc8830.so`. It loads `libhwc2onfbadapter.so`. In that adapter's source,
`setPowerModeHook()` ignored the received mode and contained literally:

`// pretend that it works`

Therefore, the Spreadtrum ioctl wired in V66 received no call. V66 was useful for diagnosis, but it could
not change the physical behavior.

## V67 fix

V67 cumulatively keeps V62, V63, V64 and the V66 kernel, and modifies both ends of the path actually used.

### Userspace

File:

`hardware/interfaces/graphics/composer/2.1/utils/hwc2onfbadapter/HWC2OnFbAdapter.cpp`

`setPowerModeHook()` now:

- turns `HWC2_POWER_MODE_OFF` into `FB_BLANK_POWERDOWN`;
- turns `HWC2_POWER_MODE_ON` into `FB_BLANK_UNBLANK`;
- opens `/dev/graphics/fb0` (fallback `/dev/fb0`) and runs `FBIOBLANK` synchronously;
- returns real errors if it cannot open the framebuffer or the ioctl fails;
- rejects DOZE because the adapter itself declares it does not support it;
- logs `V67 HWC2 fb power mode` markers in logcat.

### Kernel

File:

`kernel/samsung/gtexswifi/drivers/video/sprdfb/sprdfb_main.c`

The `sprdfb_blank()` callback already turned the panel off/on, but on wake it did not coordinate the legacy
state. V67 adds:

- synchronous power-off via the existing `sprdfb_power(dev, 0)`;
- before the unblank, if the state is not `PM_SUSPEND_ON`, a call to `request_suspend_state(PM_SUSPEND_ON)`;
- synchronous power-on and refresh;
- `V67 fb_blank ...` markers in dmesg.

This covers a fast OFF->ON: no OFF worker is created; a still-queued suspend aborts and one already running
handlers is followed by the full `late_resume`, also recovering mip4 and touchkey.

## Artifact

- Package: `sm-t280-phase6/packages/SM-T280-android10-fb-adapter-power-PHASE6-v67-DO-NOT-FLASH.tar.md5`
- Exact Odin AP content: `boot.img` + `system.img`
- Boot SHA-256: `2d621cf4d4862c31edb182d2c6348a4f611812755389b4a6b6ad50c9d9e317c1`
- Adapter SHA-256: `81b898708f2ca13e3c109238138dc817fc087a559f875d9411bbe178f087b8c3`
- Standard sparse system SHA-256: `5def012aa1d4d896767a65f18998c23e8fe85cbafb41737d07067e4b1c72037e`
- Legacy sparse system SHA-256: `167e9c120af385dc3f1259e99060d6a781ccd16e67f652fa5108bfe9dee25e2c`
- Package SHA-256: `99b01e53213391eecc2592eeab2b76d97cac02c8b4689cff1da33c11a2d4e218`
- Embedded Odin MD5: `b79aeaa249914684c357be0f62691ee6`
- Package size: `1019289697` bytes
- Boot size: `12938420` bytes; margin: `3838796` bytes

## Offline validation

- `V67_BOOT_SYSTEM_BUILD_PASS`
- V67 marker present in the kernel and in `libhwc2onfbadapter.so`
- V67 marker present inside `system.img`
- V64 suspend-counter marker kept inside `system.img`
- `ODIN_SYSTEM_PACKAGE_PASS`
- `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`
- `V67_PACKAGE_PASS`
- `SYSTEM_BOOT_OFFLINE_VERIFY_PASS`
- clean system ext4
- Samsung/SEAndroid tag present
- package recomputed from Windows too with the same SHA-256
- no whitespace errors in the kernel or hardware/interfaces diffs

## Physical result

The user confirmed that on and off were fixed. The later ADB audit also showed:

- Android fully booted: `sys.boot_completed=1`;
- V67 kernel actually loaded: `3.10.108-g95996f39350-dirty #30`;
- correct userspace transitions via `V67 HWC2 fb power mode 0/2 complete`;
- correct kernel transitions via `V67 fb_blank OFF/ON complete`;
- a normal OFF completed in about 316 ms;
- three later fast cycles with no stale power-off after the last ON;
- explicit cancellation of the pending legacy suspend during the first wake;
- `late_resume` recovered panel, `mip4_ts` and touchkey;
- real touch events after the resume;
- stable final state: `Awake`, `mWakefulnessChanging=false`, display `ON`, real brightness `143`;
- SurfaceFlinger: zero dropped frames of total, HWC and GPU;
- no `FBIOBLANK failed`, panic, Oops, hung task, soft lockup or ext4 error.

The detail and the unrelated issues detected during the same capture are in
`results/phase-6/V67-LIVE-VALIDATION.md`.
