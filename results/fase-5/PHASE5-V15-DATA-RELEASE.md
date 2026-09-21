# Phase 5 -- V15: /data mountable + PTR case in binder release

Date: 2026-09-18. Status: in offline build/validation; `DO-NOT-FLASH`.

## Reason (from the V14 diagnosis)

V14 got the SG binder working at the command level, but these remained: (1)
`/data` unmounted -> cascade (dalvik-cache, keystore); (2)
`binder_transaction_buffer_release: bad object type` for `BINDER_TYPE_PTR`.

## Changes (`sm-t280-phase5/scripts/apply-v15-data-release.py`)

1. `drivers/staging/android/binder.c`: `BINDER_TYPE_PTR` case in
   `binder_transaction_buffer_release()` (SG buffers have no resource to free) ->
   silences the "bad object type" and avoids traversal mismatches.
2. `device/samsung/gtexswifi/rootdir/fstab.sc8830`: the `/data` entry changes from
   `wait,check,encryptable=footer` to `wait,check,formattable` -- no FDE encryption
   and with automatic formatting if the mount fails (the `ext4_find_entry` of
   mmcblk0p25 suggested `/data` was corrupt). It is a diagnostic-boot decision.

system.img unchanged; kernel + boot are rebuilt. The `fstab.sc8830` goes in the
boot ramdisk (ROOT_OUT), refreshed before building.

## Offline validation

- Build: `rebuild-bootimage.sh` (recompiles the kernel because of the binder.c change).
  Log `results/fase-5/v15-rebuild-bootimage.log`.
- Ramdisk: `verify-boot-ramdisk.sh` (init binary + fstab + init.rc + /system).
- Packaging: `prepare-v15-package.sh`.

## Artifact

- Package: `sm-t280-phase5/packages/SM-T280-android10-data-mount-PHASE5-v15-DO-NOT-FLASH.tar.md5`
  (1,013,125,211 B). Kernel recompiled; ramdisk with `/data ... formattable`.
- package_sha256: `c34d1399c8957f157a20c8da90580f4e698e7af71ebecb751e67e4f22121826e`
- embedded_md5: `4f3efb6b30a85d6b26ba3a9632f06d16`
- boot_sha256: `9914f90c7d2aff13f732fd2ddd8b002609f54c6006f22ea58378bcc33acc5bb5`
- `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`, `BOOT_RAMDISK_V9_LEGACY_ROOTFS_PASS`.

## Expected interpretation

- Partial success: `/data` mounts (formatting if needed) -> the dalvik-cache/keystore
  failures disappear; zygote advances. The binder's "bad object type" disappears.
- To re-evaluate: the `hwservicemanager` SIGSEGV (does not depend on /data). If it
  persists -> review in detail the PTR case of `binder_transaction` (SG copy /
  parent fixup) or rule out an external cause (VINTF manifest). If it resolves ->
  next front the Mali-400 graphics HAL.
