# Phase 5 -- V9: boot ramdisk from ROOT_OUT (full legacy rootfs)

Date: 2026-09-17. Status: built and verified offline; `DO-NOT-FLASH` until the
user flashes it.

## Reason (from the V8 diagnosis)

The loop was not because of the fstab: `first_stage_init` does
`execv("/system/bin/init")` after first-stage; if `/system` is not mounted,
`execv` fails -> FATAL -> reboot. The V6/V8 ramdisk (TARGET_RAMDISK_OUT) is the
minimal system-as-root and **lacks the `/system` mountpoint, `init.rc`,
`init.*.rc` and `sepolicy`**. See
`results/fase-5/v8-bootloop-recovery/DIAGNOSIS.md`.

## Change

`device/samsung/gtexswifi/mkbootimg.mk` (applied with
`sm-t280-phase5/scripts/apply-v9-root-ramdisk.py`, idempotent):

- The boot ramdisk is built from `TARGET_ROOT_OUT` (full legacy rootfs) instead
  of `TARGET_RAMDISK_OUT`.
- The `/init`->`/system/bin/init` symlink is replaced by the real `init` binary
  (copied from `TARGET_RAMDISK_OUT/init`) before `MKBOOTFS`.
- The V8 fstab copy is removed (now unnecessary: ROOT_OUT already includes it).

Kernel, DT, cmdline and system.img do not change. The package's system is the
same legacy-sparse validated since V5.

## Offline validation

- Rebuild: `rebuild-bootimage.sh` (`m bootimage`), OK 01:09.
  Log `results/fase-5/v9-rebuild-bootimage.log`. Fits in 16 MiB
  (`assert-max-image-size` would have failed otherwise).
- Ramdisk: `verify-boot-ramdisk.sh` -> **BOOT_RAMDISK_V9_LEGACY_ROOTFS_PASS**:
  - real `init` binary `-rwxr-x--- 1376316`,
  - `fstab.sc8830 2316`,
  - `init.rc 34136`,
  - `system` mountpoint (dir).
  - boot 12,952,756 B.
- Packaging: `prepare-v9-package.sh` (hashes finalized below).

## Artifact

- Package: `sm-t280-phase5/packages/SM-T280-android10-legacy-rootfs-PHASE5-v9-DO-NOT-FLASH.tar.md5`
  (1,013,125,213 B). Content: exactly `boot.img` + `system.img`.
- package_sha256: `99593976ba5c1597feb15e4a068b526c54db2bb81891b7cd1fbd2324b1d0ab11`
- embedded_md5: `6faa4a06ff43e8fc67942438618ff836`
- boot_sha256: `ccafaae697de5a7ec5e3618aa456515db88cd217eb349ad0ffcfa607aad038ec`
- system (legacy sparse) sha256: `15e45f117e3e64115ab659c68391206da1599d1cd5f51db82caca6c9105724f1`

## Hardware test (pending the user)

Odin AP, Auto Reboot OFF, no PIT/Re-Partition. Flash V9, boot to system and
capture `last_kmsg` with `capture-first-boot.sh`.

## Expected interpretation

- If the legacy ramdisk is correct, first-stage should be able to mount `/system`
  (mountpoint present + fstab) and `execv("/system/bin/init")` no longer fail; the
  boot advances to second-stage (loads `init.rc`, SELinux, zygote).
- **Probable next blockers** (one variable per iteration): SELinux (permissive
  via cmdline, should not block), mounting `/system` with first-stage flags, or
  the Mali graphics HAL in SurfaceFlinger. Capture `last_kmsg`/`logcat` before
  proposing the next variant.
