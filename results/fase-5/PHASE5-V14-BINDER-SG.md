# Phase 5 -- V14: scatter-gather backport to the binder (kernel)

Date: 2026-09-18. Status: in offline build/validation; `DO-NOT-FLASH`.

## Reason (from the V13 diagnosis)

With multi-binder (V13) the HIDL services start, but `surfaceflinger` and the
HIDL services use scatter-gather transactions (`BC_TRANSACTION_SG`,
`BINDER_TYPE_PTR`) that the 3.10 binder does not support -> `unknown command
0x40286211` / `-22` -> `registerAsService=-2147483648`.

## Change

`drivers/staging/android/uapi/binder.h` + `drivers/staging/android/binder.c`
(applied with `sm-t280-phase5/scripts/apply-v14-binder-sg.py`, idempotent).
Backport of the upstream design (Martijn Coenen):

- UAPI: `BINDER_TYPE_PTR`, `struct binder_object_header`,
  `struct binder_buffer_object`, `struct binder_transaction_data_sg`,
  `BINDER_BUFFER_FLAG_HAS_PARENT`, `BC_TRANSACTION_SG`/`BC_REPLY_SG` (nr 17/18).
- `binder_buffer.extra_buffers_size`; `binder_alloc_buf` and `binder_free_buf`
  account for the extra space (consistent with the allocator).
- `binder_transaction` receives `extra_buffers_size`; size-aware object
  validation (`binder_object_size`); `BINDER_TYPE_PTR` case that copies the SG
  buffer to the extra region, relocates the pointer to the target's space and
  applies the parent fixup (`BINDER_BUFFER_FLAG_HAS_PARENT`).
- `BC_TRANSACTION_SG`/`BC_REPLY_SG` dispatch in `binder_thread_write`; the stats
  array `bc[]` enlarged to `BC_REPLY_SG`.

system.img unchanged; kernel + boot are rebuilt.

## Risk

It is the highest-risk patch of the port (kernel IPC driver, handling of user
buffers). The parent fixup is simplified relative to the upstream hardening (no
anti-overlap last_fixup tracking); acceptable in a diagnostic build with trusted
userspace and SELinux permissive. Tested stock rollback available.

## Offline validation

- Build: `rebuild-bootimage.sh` (recompiles the kernel). Log
  `results/fase-5/v14-rebuild-bootimage.log`. The compiler validates the patch.
- Legacy ramdisk: `verify-boot-ramdisk.sh`.
- Packaging: `prepare-v14-package.sh`.

## Artifact

- Package: `sm-t280-phase5/packages/SM-T280-android10-binder-sg-PHASE5-v14-DO-NOT-FLASH.tar.md5`
  (1,013,125,210 B). Kernel recompiled (binder.o OK).
- package_sha256: `2034b319c7d6129d79d083414440f5a6cff7272631a03a43affbe540aed8fdfd`
- embedded_md5: `22dee5945eac58a778e555bacef48e58`
- boot_sha256: `9f35b617c98b9c8f9dae11029fd57b38f4c1f102c0b4ca04267eeeb2fcd758a7`
- `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`, `BOOT_RAMDISK_V9_LEGACY_ROOTFS_PASS`.

## Expected interpretation

- Success: `unknown command 0x40286211` and `registerAsService=-2147483648`
  disappear; `surfaceflinger` and the HIDL services register. The front moves to
  the Mali-400 graphics HAL (gralloc/hwcomposer/EGL) so SurfaceFlinger composes,
  and to mounting `/data`.
- If new instability/kernel panic appears, suspect the SG handling (review the
  PTR case and the parent fixup); rollback to stock if appropriate.
