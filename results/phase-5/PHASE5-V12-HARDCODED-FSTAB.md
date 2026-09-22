# Phase 5 -- V12: first-stage /system entry hardcoded in init

Date: 2026-09-17. Status: in offline build/validation; `DO-NOT-FLASH`.

## Reason (from the V9-V11 diagnoses)

The three first-stage fstab paths of Android 10 are dead or fragile on this
device:

- DT (`ReadFstabFromDt`): no `/proc/device-tree` at runtime.
- File by `ro.hardware` (`GetFstabPath`): the bootloader does not pass
  `androidboot.hardware`.
- File found + flag: the `/system` entry of `fstab.sc8830` does not carry
  `first_stage_mount`, so `ReadFirstStageFstab()` filters it out.

## Change

`system/core/init/first_stage_mount.cpp` -> `ReadFirstStageFstab()` (applied with
`sm-t280-phase5/scripts/apply-v12-hardcoded-fstab.py`, idempotent): when the
fstab comes out empty, the `/system` entry is injected by hand, following the
in-tree `BuildGsiSystemFstabEntry()` pattern:

```
FstabEntry system = {.blk_device = "/dev/block/platform/sdio_emmc/by-name/SYSTEM",
                     .mount_point = "/system", .fs_type = "ext4",
                     .flags = MS_RDONLY, .fs_options = "errors=panic"};
system.fs_mgr_flags.wait = true;
system.fs_mgr_flags.first_stage_mount = true;
```

Removes all dependency on DT, `ro.hardware`, file and flags. Only affects
first-stage (ramdisk init). `system.img` unchanged (V5 legacy-sparse).

## Offline validation

- Build: `rebuild-bootimage.sh` OK; `first_stage_mount.cpp` recompiled. Ramdisk
  init contains the `by-name/SYSTEM` path (verified in the binary) -> the patch is
  in the flashable init.
- Legacy ramdisk (V9): `BOOT_RAMDISK_V9_LEGACY_ROOTFS_PASS`.
- Packaging: `prepare-v12-package.sh`.

## Artifact

- Package: `sm-t280-phase5/packages/SM-T280-android10-hardcoded-fstab-PHASE5-v12-DO-NOT-FLASH.tar.md5`
  (1,013,125,216 B).
- package_sha256: `1873981e65850d032db77b46186cd645e76a7663071184227f84e51734861410`
- embedded_md5: `fd14bb1a6249b4681b853604afd63c18`
- boot_sha256: `2f744723ef0f69ba70ee0c74b87b3526ac7d208c6004568189efbefbeae9bedf`
- Verification: `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`, `BOOT_RAMDISK_V9_LEGACY_ROOTFS_PASS`.

## Expected interpretation

- High confidence: it is the first time the `/system` entry reaches first-stage
  with the correct flag and without depending on anything external. If the
  `by-name/SYSTEM` block exists and is the flashed system.img, first-stage should
  mount `/system` and `execv("/system/bin/init")` proceed to second-stage.
- Success signal in `last_kmsg`: `execv(... ) failed: No such file` disappears;
  second-stage messages appear (init.rc, services, zygote).
- Possible next blockers: services/HAL (Mali graphics), though SELinux is already
  permissive. One variable per iteration.
