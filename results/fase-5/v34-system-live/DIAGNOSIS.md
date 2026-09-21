# Phase 5 -- V34: [OK] ANIMATION VISIBLE ON SCREEN. Framework: class_start main missing

Date: 2026-09-18. Source: user ("I see an animation") + `logcat -b all` +
live `ps`/`getprop`. `results/fase-5/v34-system-live/logcat.txt`.

## MAXIMUM MILESTONE: first Android render on the tablet

The `FBIOPAN_DISPLAY` after the memcpy (V34) makes the panel latch each frame. The
user **SEES the boot animation**. The whole graphics chain works end to end:
kernel binder FDA (V31) -> HW_FB alloc via ION (V29) -> SF GLES composition ->
fb_post with FBIOPAN (V34) -> sprdfb panel. **Graphics phase: solved.**

## New front (phase 6, framework bring-up): zygote does not auto-start

- `ps`: only surfaceflinger + bootanimation. **NO zygote, NO system_server** on the
  normal boot. The animation is sustained by SF (bootanim is launched by SF, not system_server).
- `ro.zygote=zygote32` OK, `/init.zygote32.rc` OK, but in the log there is only
  `class_start core`, **never `class_start main`** (zygote is class main).
- **Root cause:** `ro.crypto.state` is **EMPTY**. In `system/core/rootdir/init.rc`:
  - `on zygote-start && property:ro.crypto.state=unencrypted` (638) -> `start zygote`
  - `on nonencrypted` (770) -> `class_start main` + `late_start`
  Both depend on `ro.crypto.state` being unencrypted/unsupported/encrypted. Being
  empty, neither zygote nor class_start main fire. (vold/cryptfs should set it;
  `vdc cryptfs init_user0` runs with status 0 but does not set the prop -- possible effect
  of the `formattable` /data without encryption metadata, or of the V16 changes in post-fs-data.)
- **Validated live:** `setprop ctl.start zygote` by hand -> zygote (1592) starts,
  **forks system_server (1618)**, rises to **32 services**. The framework DOES boot; only
  the trigger is missing.

## Later framework blockers (after fixing the trigger)

With zygote by hand, system_server progresses but:
1. **`BootAnimation: SurfaceFlinger died`** -- SF restarts when system_server
   takes the display (possible SF instability with system_server / or an artifact of the
   manual late-start).
2. **system_server crashes once (1399->1618)** and stalls in **PackageManagerService**:
   `Watchdog: Pausing ... reason: packagemanagermain` + `WAITED_HALF` (main thread
   blocked ~30s scanning/`collecting certs` of overlays). Risk of a Watchdog kill.
3. **audioserver SIGSEGV** in `AudioFlinger::AudioFlinger()` every 5s (audio HAL) --
   floods the log, uid 1041 killed in a loop.

## V35 (next) -- trigger class_start main

Chosen option: force `ro.crypto.state=unencrypted` AFTER post-fs-data (when
/data is ready) so the triggers `on property:ro.crypto.state=
unencrypted` -> `trigger nonencrypted` -> `class_start main` (+ `start zygote`) fire. Via
`init.sc8830.rc`/`init.rc` `on post-fs-data` -> boot.img changes. (Alternative: fix
vold to set the prop for real.)
After V35, attack PMS (possible dex2oat/overlay/storage) and audioserver (audio HAL).

## Graphics artifact state (resolved, preserve)
V25 (HIDL -impl), V26/V32 (usage bits), V27 (FB adapter), V28 (fb0 dims), V29 (ION
alloc HW_FB), V31 (binder FDA, boot 8e11eb52), V34 (FBIOPAN in fb_post memcpy).
