# Phase 5 -- V11: fstab fallback in fs_mgr (no ro.hardware or /proc/device-tree)

Date: 2026-09-17. Status: in offline build/validation; `DO-NOT-FLASH`.

## Reason (from the V10 diagnosis)

Both of Android 10's first-stage mount mechanisms are dead on this device:

- `ReadFstabFromDt()` -> **there is no `/proc/device-tree`** at runtime (verified
  by ADB). The `dt.img` is not exposed as DT.
- `GetFstabPath()` (file-based fstab) -> needs `ro.hardware`, which does not
  arrive because the bootloader ignores the boot.img cmdline.

The ramdisk (V9) already has `/fstab.sc8830`, the `/system` mountpoint and
`init.rc`. All that is missing is for first-stage to **find** the fstab.

## Change

`system/core/fs_mgr/fs_mgr_fstab.cpp` -> `GetFstabPath()` (applied with
`sm-t280-phase5/scripts/apply-v11-fstab-fallback.py`, idempotent): before the
final `return ""`, a fallback that looks for `/{odm/etc,vendor/etc,}fstab.sc8830`
directly (fixed device), without depending on `ro.hardware`.

Only affects first-stage (ramdisk `/init`). Second-stage uses `mount_all
/fstab.sc8830` with an explicit path, so `system.img` does not change. init +
boot are rebuilt; `system.img` is reused (V5 legacy-sparse).

## Offline validation

- Rebuild: `rebuild-bootimage.sh` (init relinks because of the fs_mgr change).
  Log `results/fase-5/v11-rebuild-bootimage.log`.
- Legacy ramdisk (V9): `verify-boot-ramdisk.sh`.
- Packaging: `prepare-v11-package.sh`.

## Artifact

- Package: `sm-t280-phase5/packages/SM-T280-android10-fstab-fallback-PHASE5-v11-DO-NOT-FLASH.tar.md5`
  (1,013,125,215 B). Ramdisk init recompiled with the patch (verified:
  contains `/odm/etc/fstab.` and `sc8830`).
- package_sha256: `cf70ffebf3ff00a6e9e1537afaab765d489769e399d6decffc6aeb62a82eea64`
- embedded_md5: `daa94db1e7bada89f8d01538c17e6b6a`
- boot_sha256: `1e71c2b83a4e1f63d66377cb552d6ef258525a8280992b3fe1a59ce6867fbfd9`
- Verification: `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`, `BOOT_RAMDISK_V9_LEGACY_ROOTFS_PASS`.

## Expected interpretation

- If first-stage finds `/fstab.sc8830` and mounts `/system`,
  `execv("/system/bin/init") failed` disappears and the boot moves to
  second-stage.
- **Probable next blocker: SELinux.** `androidboot.selinux=permissive` goes in
  the cmdline the bootloader ignores, so SELinux could stay enforcing and block
  the boot; that would be the next variable (force permissive via sepolicy or
  another way not dependent on the cmdline).
- Others possible: init.rc/services, Mali graphics HAL in SurfaceFlinger.
