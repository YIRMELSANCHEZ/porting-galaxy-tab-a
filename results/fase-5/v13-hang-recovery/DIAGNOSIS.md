# Phase 5 -- V13: binder multi-device OK; new blockers (binder SG + /data)

Date: 2026-09-18. Source: `results/fase-5/v13-hang-recovery/last_kmsg.txt`.

## Success: multi-binder resolved

The `Failed to setup binder polling: -9` aborts **disappear** (0 occurrences).
`zygote`, `surfaceflinger`, `cameraserver`, `netd`, `media`, `logd`,
HIDL services... start. The boot advances much further.

## New blocker 1: binder without scatter-gather

```
binder: 362:362 unknown command 1076650769
binder: 362:362 ioctl c0186201 ... returned -22
```

`1076650769 = 0x40286211 = BC_TRANSACTION_SG` (`_IOW('c',17,...)`). The 3.10
binder driver does not support the scatter-gather transactions Android 8+ uses
(`BC_TRANSACTION_SG`/`BC_REPLY_SG`, `binder_buffer_object`, `BINDER_TYPE_PTR`,
`extra_buffers_size`). Consequence: `surfaceflinger` (SIGSEGV/regfail),
`ISurfaceFlingerConfigs`, `health@2.0`, `cas`, `allocator`, `configstore`
fail `registerAsService` with `-2147483648`.

-> V14: scatter-gather backport to the binder (AOSP common kernel pattern
"binder: add support for scatter-gather").

## New blocker 2: /data not mounted

```
Abort message: 'Error creating cache dir /data/dalvik-cache/arm : No such file or directory'
```

`/data` is not mounted (first-stage only mounts `/system`; second-stage's
`mount_all` does not mount `/data`, or its fstab entry is not processed). zygote
aborts because it cannot create dalvik-cache. To address after (or together with)
the binder SG: ensure `/data` (and `/cache`, `/vendor` as needed) is mounted in
second-stage via `fstab.sc8830` / `mount_all`.

## State

Accumulated progression: bootloop -> second-stage (V12) -> binder multi-device (V13) ->
binder SG + /data missing. Each layer is a real and hardware-verified advance.
SELinux permissive OK. The `ext4_find_entry` of `mmcblk0p25` remains under observation.

## Scope note

The binder scatter-gather backport is a considerable kernel patch (more than the
multi-device one). After it, the likely next front is the Mali-400 graphics HAL
so SurfaceFlinger composes.
