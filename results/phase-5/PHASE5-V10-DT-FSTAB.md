# Phase 5 -- V10: /system fstab in the device tree

Date: 2026-09-17. Status: in offline build/validation; `DO-NOT-FLASH` until the
user flashes it.

## Reason (from the V9 diagnosis)

The Spreadtrum bootloader **ignores the boot.img's `BOARD_KERNEL_CMDLINE`** (the
real cmdline is `console=null ... init=/init`, without `androidboot.hardware`).
So `ro.hardware` does not reach init, `GetFstabPath()` does not look for
`/fstab.sc8830`, and the file-based fstab is never used (V7/V8/V9 fail
identically and init crashes). The bootloader does respect the DTB body (it only
overwrites `bootargs`). Android 10's canonical path: declare the fstab in the DTB
so `ReadFstabFromDt()` reads it in first-stage. See
`results/phase-5/v9-bootloop-recovery/DIAGNOSIS.md`.

## Change

`kernel/samsung/gtexswifi/arch/arm/boot/dts/sprd-scx35_gtexswifi_rev05.dts`
(active rev, `hw_revision=5`), applied with
`sm-t280-phase5/scripts/apply-v10-dt-fstab.py` (idempotent). Node added after
`chosen`:

```
firmware {
    android {
        compatible = "android,firmware";
        fstab {
            compatible = "android,fstab";
            system {
                compatible = "android,system";
                dev = "/dev/block/platform/sdio_emmc/by-name/SYSTEM";
                type = "ext4";
                mnt_flags = "ro,errors=panic";
                fsmgr_flags = "wait";
            };
        };
    };
};
```

Keeps everything from V5-V9 (legacy sparse, init binary, ROOT_OUT). system.img
unchanged. Recompiles kernel dtbs -> `dt.img` -> boot.

## Offline validation

- Rebuild: `rebuild-bootimage.sh` (log `results/phase-5/v10-rebuild-bootimage.log`).
- dt.img must contain the node (`strings dt.img` -> `android,fstab`,
  `by-name/SYSTEM`).
- Ramdisk still has legacy rootfs (V9): `verify-boot-ramdisk.sh`.
- Packaging: `prepare-v10-package.sh`.

## Artifact

- Package: `sm-t280-phase5/packages/SM-T280-android10-dt-fstab-PHASE5-v10-DO-NOT-FLASH.tar.md5`
  (1,013,125,209 B). Content: exactly `boot.img` + `system.img`.
  dt.img (inside boot) contains `android,fstab` + `by-name/SYSTEM` (verified).
- package_sha256: `4bcd82435ceef76a0b85754dfb20482087eb3782666f5c3c32e3f2ee58e6ae83`
- embedded_md5: `4189e1e243be2ed7646492b56eebf954`
- boot_sha256: `be21e0821272d58d71b2c81a9c0bf0b29ee14f7d38f912fe2272a449cdb39d4d`
- system (legacy sparse) sha256: `15e45f117e3e64115ab659c68391206da1599d1cd5f51db82caca6c9105724f1`
- Verification: `ODIN_SYSTEM_PACKAGE_PASS` + `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`,
  ramdisk `BOOT_RAMDISK_V9_LEGACY_ROOTFS_PASS`.

## Expected interpretation

- If the bootloader honors the DTB's `fstab` node, `ReadFstabFromDt()` stops
  failing, first-stage mounts `/system` and `execv("/system/bin/init")` proceeds
  to second-stage.
- If `ReadFstabFromDt` keeps failing, it means the bootloader does NOT use our
  DTB body (it would use its own); we would have to investigate how it injects
  `/firmware/android` and whether it accepts the fstab another way.
- Probable next blockers after mounting `/system`: SELinux, second-stage init.rc,
  Mali graphics HAL. One variable per iteration; capture `last_kmsg`/`logcat`.
