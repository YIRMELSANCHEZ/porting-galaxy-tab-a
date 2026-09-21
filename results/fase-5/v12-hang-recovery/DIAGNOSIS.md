# Phase 5 -- V12: MILESTONE (second-stage boots) + new blocker (binder)

Date: 2026-09-17. Source: `results/fase-5/v12-hang-recovery/last_kmsg.txt`.

## MILESTONE: first-stage resolved

V12 changed the symptom from a **loop** (reboot to bootloader in ~3 s) to a **hang
on the logo ~3 min**. The `last_kmsg` shows that **`/system` mounted and the
second-stage init booted Android 10**:

- `init: SVC_EXEC service 'exec 6 (/system/bin/art_apex_boot_integrity)' ...`
- `/system` and `/system/vendor` services run (healthd, vold, netd,
  hwservicemanager, media.codec, configstore, cas, wificond, app_process32...).

The `/system` entry hardcoded in `ReadFirstStageFstab()` (V12) worked. The whole
V5-V12 chain (legacy sparse, GCC4.8 kernel, legacy ramdisk, hardcoded first-stage)
is validated on hardware to reach second-stage.

## New blocker: binder driver (Android 10 multi-device)

All HIDL/binder services abort (SIGABRT) with:

```
Abort message: 'Failed to setup binder polling: -9 (Unknown error -9)'
Abort message: 'Could not setThreadPoolConfiguration: -9'
```

`-9` = EBADF. Origin in `libhidlbase configureBinderRpcThreadpool`. Cause:

- Kernel: `CONFIG_ANDROID_BINDER_IPC=y`, `CONFIG_ANDROID_BINDER_IPC_32BIT=y`,
  **but NOT `CONFIG_ANDROID_BINDER_DEVICES`**; the 3.10 binder driver does not even
  support it (it does not appear in its Kconfig). It only creates `/dev/binder`.
- Android 10 (Treble) also requires **`/dev/hwbinder`** (HIDL) and
  **`/dev/vndbinder`** (vendor). Not existing, the HIDL services fail to open
  their binder -> EBADF -> abort.

After the crash storm, init ends with `Restarting system with command
'bootloader'` (that is why it sometimes looks like a hang, sometimes a slow
reboot). A one-off `ext4_find_entry` error was also seen in `mmcblk0p25` (to
watch, not critical now).

## Fix -> V13 (kernel: multi-binder)

Backport to the 3.10 binder driver of **multiple-device** support
(`CONFIG_ANDROID_BINDER_DEVICES="binder,hwbinder,vndbinder"`), AOSP common kernel
pattern (create several misc devices from a list). It is a **kernel driver**
change (bigger than the previous init iterations) and recompiles the kernel +
dt.img + boot.

Alternatives to consider if the backport gets complicated: a compatibility layer
that creates `/dev/hwbinder`/`/dev/vndbinder` on the single binder (less reliable).
