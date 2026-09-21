# Phase 5 -- V13: multi-binder backport to the kernel (Treble/Android 10)

Date: 2026-09-17. Status: in offline build/validation; `DO-NOT-FLASH`.

## Reason (from the V12 diagnosis)

V12 managed to mount `/system` and boot second-stage, but **all HIDL services
abort** with `Failed to setup binder polling: -9` /
`Could not setThreadPoolConfiguration: -9` (EBADF). Kernel 3.10 has
`CONFIG_ANDROID_BINDER_IPC` but only creates `/dev/binder`; Android 10 needs
`/dev/hwbinder` and `/dev/vndbinder`, each with its own context manager.

## Change

`kernel/samsung/gtexswifi/drivers/staging/android/binder.c` (applied with
`sm-t280-phase5/scripts/apply-v13-multibinder.py`, idempotent). Backport of the
AOSP common kernel's multi-device pattern:

- `struct binder_context` (context_mgr_node + uid + name) and `struct
  binder_device` (hlist + miscdev + context).
- Field `struct binder_context *context;` in `struct binder_proc`; set in
  `binder_open()` via `container_of(filp->private_data, struct binder_device,
  miscdev)`.
- The 16 references to `binder_context_mgr_node` and 5 to `binder_context_mgr_uid`
  become per-context (`proc->context->...`); `proc` is in scope at every site.
- `init_binder_device()` + a loop in `binder_init()` registering the devices from
  `binder_devices_param = "binder,hwbinder,vndbinder"`.

No Kconfig/defconfig changes (the list is hardcoded). system.img unchanged;
kernel + boot are rebuilt.

## Offline validation

- Build: `rebuild-bootimage.sh` (recompiles the kernel). Log
  `results/fase-5/v13-rebuild-bootimage.log`. The compiler validates the patch.
- Legacy ramdisk (V9/V12): `verify-boot-ramdisk.sh`.
- Packaging: `prepare-v13-package.sh`.

## Artifact

- Package: `sm-t280-phase5/packages/SM-T280-android10-multibinder-PHASE5-v13-DO-NOT-FLASH.tar.md5`
  (1,013,125,212 B). Embedded kernel contains `binder,hwbinder,vndbinder` (verified).
- package_sha256: `6014cb981ba512adcfb3a1a4c74ffb90fd8d0453cb84ea4ab06e97dc73901a58`
- embedded_md5: `d41843928618a51666db3d7088b01295`
- boot_sha256: `66b5aa661d2e9fbff0cb17c0064fff1da4de4cd2c1f1bea5ffbc8d1f2a49ad5c`
- Build: kernel recompiled, `binder.o` OK; `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`.

## Expected interpretation

- If the kernel creates the three binder devices, `hwservicemanager` and the HIDL
  services (configstore, cas, media.codec...) stop aborting with -9.
- Signal in `last_kmsg`/`logcat`: the `binder polling: -9` disappear; the loop
  moves toward SurfaceFlinger/Mali graphics HAL or the boot animation.
- Watch the `ext4_find_entry` in `mmcblk0p25` seen in V12.
