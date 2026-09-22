# Phase 6 -- V35: auto-boot OK (6.1). ROOT CAUSE of the hang: hwservicemanager crash

Date: 2026-09-18/19. Source: CLEAN boot (no commands), `logcat`+`dmesg`+ANR trace,
`results/phase-6/v35-system-live/`.

## 6.1 RESOLVED -- the framework auto-boots

V35 (`setprop ro.crypto.state unencrypted` + `trigger nonencrypted` at the end of `on post-fs-data`) works:
on a normal boot, `ro.crypto.state=unencrypted`, `init.svc.zygote=running`, zygote + system_server start on
their OWN. Log: `init: starting service 'zygote'` + `class_start main ... succeeded`.

## ROOT CAUSE (common to 6.2/6.3/6.4): hwservicemanager CRASHES (SIGSEGV)

`dmesg`: `init: Service 'hwservicemanager' (pid 155) received signal 11` -> `onrestart: class_restart main`
(restarts system_server in cascade) -> restarts as pid 466, which gets stuck. **Crash backtrace
(tombstone):**
```
#00 libvintf.so  HalManifest::getInstances(...)         <- null pointer deref
#01 hwservicemanager  android::hardware::getInstances(string)
#02 hwservicemanager  ServiceManager::listManifestByInterface(...)
```
hwservicemanager, when querying the VINTF manifest to answer getService/getTransport/list, calls
`GetDeviceHalManifest()->getInstances(...)`. **The device has NO VINTF manifest** (verified: absent in
`/vendor/etc/vintf/manifest.xml` and in the `device/samsung/gtexswifi` tree) -> the manifest is null ->
null-deref -> SIGSEGV.

### Observed cascade (all a consequence of this)
- **system_server** hangs in `ActivityManagerService::<init>` -> `ProcessStats` -> `Debug.getMemoryInfo` ->
  `IMemtrack::getService` -> `getTransport` to hwservicemanager (which is dead/stuck) -> the main thread
  blocked in binder_thread_read (Watchdog WAITED_HALF). Deadlock: multiple processes (515/526/527/529/530/553)
  blocked on outgoing transactions to hwservicemanager (466) that does not respond.
- **audioserver** SIGSEGV (AudioFlinger) and **keystore** abort: they cannot find their HALs
  (audio@N.0::IDevicesFactory) because hwservicemanager is broken.

## V36 (fix) -- device VINTF manifest

`apply-v36-vintf-manifest.py`: creates `device/samsung/gtexswifi/manifest.xml` (declares the HALs that ARE
provided: graphics allocator@2.0/composer@2.1/mapper@2.0 passthrough, configstore@1.1, health@2.0,
memtrack@1.0 passthrough) + `DEVICE_MANIFEST_FILE` in BoardConfig -> installed to
`/vendor/etc/vintf/manifest.xml`. With a valid (non-null) manifest, `getInstances` does not crash ->
hwservicemanager survives -> stable HIDL -> system_server progresses. Change in system.img; boot = V35.

Expected success: hwservicemanager does NOT crash; system_server moves past ActivityManager/memtrack and
advances (PackageManager, etc.). Re-diagnose whatever remains after this.

## Note: audioserver
The audioserver crash (AudioFlinger::AudioFlinger()) may persist separately (SPRD audio HAL, source in
hardware/sprd/audio/sc8830). If it continues after V36, silence/provide it (6.4). But first see whether it
no longer crashes with hwservicemanager stable.
