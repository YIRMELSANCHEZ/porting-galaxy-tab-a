# Phase 6 -- Framework bring-up (boot up to the launcher)

Starting point: **phase 5 consolidated** (see `PHASE5-COMPLETE.md`). Graphics
work (animation visible). Flashed candidate: **V34** (boot `8e11eb52`, FDA
kernel). Phase 6 objective: get the Java framework to boot on its own and reach
the **launcher/home**.

## State validated live (V34)

Starting zygote by hand (`adb shell setprop ctl.start zygote`), the framework
DOES come up: zygote -> **system_server** -> **32 services** registered. Confirms
zygote and system_server are functional; the problem is the start trigger +
downstream blockers.

## Ordered blockers (the 4 known ones)

### 6.1 -- zygote does not auto-start (FIRST; the clearest)
`class_start main` (init.rc:770 `on nonencrypted`) and `start zygote`
(init.rc:638 `on zygote-start && property:ro.crypto.state=unencrypted`) depend on
**`ro.crypto.state`**, which at runtime is **EMPTY**. vold/`vdc cryptfs
init_user0` runs with status 0 but does not set the prop (probable effect of the
`formattable` /data without encryption metadata, or of the V16 changes in
post-fs-data).

**Proposed fix (V35):** force `ro.crypto.state=unencrypted` AFTER /data is
mounted (in `on post-fs-data`, at the end, in init.rc or the ramdisk's
init.sc8830.rc) -> fires `on property:ro.crypto.state=unencrypted` -> `trigger
nonencrypted` -> `class_start main`. It is a ramdisk change -> **boot.img
changes**. Cleaner alternative: fix vold/fs_mgr so it sets the prop for real.
- WATCH the timing: do NOT set it before post-fs-data (zygote needs /data).
- Verify after V35: `getprop init.svc.zygote` = running on a normal boot.

### 6.2 -- PackageManagerService stalls system_server
`Watchdog: Pausing HandlerChecker: main thread for reason: packagemanagermain` +
`WAITED_HALF` (~30s blocked). Seen "collecting certs" of product overlays.
Suspicions: slow or hung dex2oat/odex, scanning a problematic APK, or slow /data
access. Investigate with `logcat -b all | grep -i
"PackageManager\|dex2oat\|installd"` and see whether it progresses (slow) or hangs
(hard). If it is a Watchdog kill -> system_server loop (seen 1399->1618).

### 6.3 -- SurfaceFlinger restarts when system_server connects
`BootAnimation: SurfaceFlinger died, exiting`. SF dies/restarts when
system_server takes the display (DisplayManager). It may be an artifact of the
manual late-start of zygote, or real instability. Re-evaluate with a normal boot
(after 6.1).

### 6.4 -- audioserver SIGSEGV in a loop (audio HAL)
`AudioFlinger::AudioFlinger()` null-deref, every 5s, uid 1041 killed. Audio HAL
(`android.hardware.audio@2.0/4.0/5.0::IDevicesFactory` not registered). Floods
the log. Options: provide the SPRD audio HAL service
(`hardware/sprd/audio/sc8830`, it is SOURCE), or disable audioserver temporarily
to clean the boot and isolate 6.2/6.3.

## How to work (same as phase 5)

- Build: `wsl.exe -u lineage bash -lc 'bash .../scripts/build-full-rom.sh > log 2>&1'`
  (WSL opens as root; MUST be `-u lineage`). Package with `prepare-vNN-package.sh`.
- Logs: repo `adb.exe` + `MSYS_NO_PATHCONV=1`; system boots with adbd (V21 ffs).
- Flash authorization: user only, Odin **AP**, Auto Reboot OFF, no PIT.
- Document each iteration in `vNN-system-live/DIAGNOSIS.md` + HANDOFF + ARTIFACTS.

## Log-capture method
See `LOG-CAPTURE-METHOD.md`. With system booted there is direct ADB (recovery not needed).
