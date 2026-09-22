# Phase 6 -- V37: JIT disabled, loop BROKEN (6.3 resolved). New blocker: health HAL

Date: 2026-09-19. Source: V37 flashed, clean boot, `results/phase-6/v37-system-live/` (logcat.txt,
dmesg.txt, ps-A.txt). User: "animation". bootanim running.

## 6.3 RESOLVED -- system_server no longer crashes in the JIT

With `dalvik.vm.usejit=false` (verified at runtime):
- `system_server` pid STABLE (same pid in separate samples; no more Zygote exit/restart in a loop). The
  "Jit thread pool" SIGSEGV disappeared completely.
- It advances MUCH further: PackageManager scans the 139 system apps and FINISHES (`Finished scanning
  system apps ... packageCount: 139`, `Time to scan packages: 2.788 s`) -> exactly the point where V36
  died. Then: StartPackageManagerService, StartOtaDexOptService, StartUserManagerService, SetSystemProcess,
  InitWatchdog, StartOverlayManagerService, StartSensorService, AppDataPrepare... = inside
  SystemServer.startOtherServices().

## NEW BLOCKER (6.4): no health HAL -> system_server hung

system_server (BatteryService) and surfaceflinger stay in an infinite loop:
```
W ServiceManagement: Waited one second for android.hardware.health@2.0::IHealth/default
I ServiceManagement: getService: Trying again for ...IHealth/default...
```
dmesg:
```
init: Received control message 'interface_start' for '...IHealth/default' from
      hwservicemanager
init: Could not find 'android.hardware.health@2.0::IHealth/default' for
      ctl.interface_start
```
Cause: the device does NOT install the binderized health HAL service. Only the old `healthd` exists (pid
214; reads the battery via sysfs OK: `healthd: battery l=98 v=4315...`), but Android 10 consumes IHealth@2.0
via HIDL, not healthd. Also, the V36 manifest declares health@2.0/IHealth (hwbinder) but nothing provides
it -> clients wait forever for a nonexistent service. system_server stays in `futex_wait` and does not
reach `boot_completed`.

## V38 (fix) -- include android.hardware.health@2.0-service

`apply-v38-health-service.py`: adds `android.hardware.health@2.0-service` (generic, from system/core/healthd,
already compiled; class hal; overrides healthd) to PRODUCT_PACKAGES. It uses libbatterymonitor (auto-detects
/sys/class/power_supply, the same sysfs healthd already reads fine) -> starts in `on boot` (class_start hal)
and registers IHealth@2.0 -> system_server and surfaceflinger unblock. vendor:true -> installs in
/system/vendor/bin/hw (vendor lives in system). Only changes system.img; boot = V35.

Expected success: the "Waited one second for ...IHealth" loop disappears; system_server completes
startOtherServices and (ideally) reaches `sys.boot_completed=1`.

## Secondary blocker still active: audioserver SIGSEGV (6.4b)

`audioserver` keeps crashing every ~5 s (SIGSEGV, null-deref in AudioFlinger). Cause: it finds NO audio HAL
-> `hwservicemanager: getTransport: Cannot find entry android.hardware.audio@5.0::IDevicesFactory/default
in either framework or device manifest` (also 4.0/2.0 and audio.effect). No audio HIDL service is registered
or in the manifest. It does NOT block system_server directly (system_server only waits for health), but the
audio HAL will need to be provided/silenced (audio.primary.sc8830 is already in PRODUCT_PACKAGES; the HIDL
wrapper android.hardware.audio@N.0-service + manifest entries are missing). It is tackled after confirming
V38 unblocks the boot (next iteration, V39).
