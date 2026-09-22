# Phase 5 -- V18: MILESTONE (/data + all the plumbing) -> graphics HAL layer (pthread_t)

Date: 2026-09-18. Source: `results/phase-5/v18-recovery/last_kmsg.txt` + /data
mounted from recovery.

## MILESTONE: ro.hardware=sc8830 unblocked /data and everything else

With `ro.hardware=sc8830` effective in second-stage (system.img rebuilt, V18):

- `import /init.sc8830.rc` works -> `mount_all /fstab.sc8830` runs -> **`/data`
  mounts RW**.
- post-fs-data creates the **COMPLETE structure** of `/data` (misc, system,
  dalvik-cache, tombstones, app, anr, user, vendor...). Verified by mounting /data
  from recovery: ~45 directories, not just lost+found.
- Start: `apexd`, `hwservicemanager` (no crash!), `logd`, `vdc cryptfs
  init_user0` (OK), `art_apex_boot_integrity`, `zygote`.

The whole init/storage/binder/services chain is operational. The root cause of
`/data` (ro.hardware="unknown") is RESOLVED.

## New blocker: graphics HAL / pthread_t

`surfaceflinger` aborts:

```
Abort message: 'invalid pthread_t 0xb6f86328 passed to pthread_getschedparam'
```

triggered by `android.hardware.graphics.composer@2.1::IComposer` (Mali-400).
Also `audioserver` SIGSEGV. When surfaceflinger (critical) falls, init kills the
group (zygote/cameraserver/netd get signal 9).

It is a **known** problem of porting Android 5-7 era proprietary blobs to
Android 10: Android 10's bionic validates `pthread_t` strictly
(`__pthread_internal_find`) and aborts if a blob passes a pthread_t it does not
recognize. The Mali graphics HALs (composer/gralloc) do so.

`/data/tombstones` empty: crashes this early do not reach tombstoned; they are
seen in `last_kmsg`.

## Next (V19)

Shim in **bionic** to tolerate the old pthread_t: make
`pthread_getschedparam`/`pthread_setschedparam` (and the `__pthread_internal_find`
validation) not abort on an unknown pthread_t, returning the thread or a soft
error. It is the standard fix of Android 10 ports with old blobs.
It goes in bionic (libc) -> system.img. After it, evaluate whether the Mali HAL
composes or the next graphics problem appears (gralloc/EGL/formats).

## Progression (hardware-verified)

bootloop -> second-stage (V12) -> binder multi-device (V13) -> binder SG (V14) ->
/data RW (V15) -> ro.hardware=sc8830 -> /data structured + services (V18) ->
**Mali graphics HAL layer (pthread_t)**. It is the big front anticipated.
