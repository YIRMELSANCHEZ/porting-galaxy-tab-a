# Phase 6 -- V38: health OK (6.4 resolved). New blocker (on the critical path): audio HAL

Date: 2026-09-19. Source: V38 flashed, clean boot, `results/phase-6/v38-system-live/`. User: "animation".
bootanim running.

## 6.4 RESOLVED -- IHealth@2.0 provided, system_server unblocks

`android.hardware.health@2.0-service` works: `init.svc.health-hal-2-0=running`, `lshal` shows
`android.hardware.health@2.0::IHealth/default` REGISTERED (pid 220). The "Waited one second for ...IHealth"
loop disappeared. system_server (stable pid) advances MUCH further in startOtherServices:
StartPackageManagerService, NetworkManagement, IpSec, Wifi/WifiScanning/WifiP2P, ConnectivityService,
NsdService, NotificationManager, LocationManager, TimeDetector, SearchManager, WallpaperManager... (log
SystemServerTiming up to ~StartWallpaperManagerService).

## NEW BLOCKER (6.4b, ON THE CRITICAL PATH): audioserver crashes -> no media.audio_policy

system_server stays in a loop:
```
I ServiceManager: Waiting for service 'media.audio_policy' on '/dev/binder'...
```
media.audio_policy is published by audioserver, but audioserver dies on every attempt:
```
F libc: Fatal signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), fault addr 0x0 (null deref)
        pid NNNN (audioserver)
backtrace:
  #00 libaudioflinger.so  AudioFlinger::AudioFlinger()+1258
  #01 audioserver  BinderService<AudioFlinger>::publish
  #02 audioserver  main
```
Cause (already visible in logcat): audioserver finds NO audio HAL -> `hwservicemanager: getTransport:
Cannot find entry android.hardware.audio@5.0::IDevicesFactory/default in either framework or device
manifest` (same for 4.0/2.0 and audio.effect). AudioFlinger dereferences the null DevicesFactory and
crashes. Without audioserver -> AudioService (in system_server) waits forever for media.audio_policy -> NO
boot_completed. **Now audio DOES block the boot.**

The device has the legacy HAL `audio.primary.sc8830.so` (/system/lib/hw) and `audio_policy.sc8830`, but NOT
the HIDL service that wraps/registers IDevicesFactory, or audio entries in the VINTF manifest.

## V39 (fix) -- audio HIDL service + passthrough impls + manifest

`apply-v39-audio-hidl.py`:
- PRODUCT_PACKAGES += android.hardware.audio@2.0-service (class hal; does
  registerPassthroughServiceImplementation of IDevicesFactory 5.0->4.0->2.0 and IEffectsFactory) +
  android.hardware.audio@4.0-impl + android.hardware.audio.effect@4.0-impl (passthrough wrapping
  audio.primary.sc8830 via hw_get_module).
- VINTF manifest += audio@4.0 IDevicesFactory + audio.effect@4.0 IEffectsFactory (hwbinder). The service's
  .rc declares the 4.0 and 2.0 interfaces.
Installs in /system/vendor; boot = V35.

Expected success: audioserver starts without crashing, publishes media.audio_policy; system_server exits
the loop and completes startOtherServices -> ideally `sys.boot_completed=1`. If the 4.0 passthrough does not
match the legacy sc8830 HAL, try the 2.0-impl version (next iteration).

## Notes
- keystore (SIGABRT) and media (restarting) were still restarting on V38, but they are NOT on the observed
  critical path (system_server only waited for health and then media.audio_policy). Re-evaluate after V39.
