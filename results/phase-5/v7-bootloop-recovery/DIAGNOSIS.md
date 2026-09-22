# Phase 5 -- V7 diagnosis (last_kmsg captured)

Date: 2026-09-17. Source: `results/phase-5/v7-bootloop-recovery/last_kmsg.txt`
(139,702 B, extracted via ADB from recovery; root shell stable at the time of
capture). `pstore` empty.

## Observed sequence

```
[3.346] init: Failed to fstab for first stage mount
[3.347] init: [libfs_mgr]ReadDefaultFstab(): failed to find device default fstab
[3.348] init: First stage mount skipped (missing/incompatible/empty fstab in device tree)
[3.387] sec_reboot_notifier (1, bootloader)
[3.835] Restarting system with command 'bootloader'.
```

## Interpretation

- The V7 fix (`androidboot.hardware=sc8830`) **did change the behavior**: in V6
  init did a hard-reboot in first-stage; in V7 init reaches the first-stage mount
  evaluation and **skips** it because it does not find the fstab.
- But in Android 10 `/system` must be mounted in first-stage. Skipping it, init
  is left with no system and **reboots to bootloader** (`Restarting system with
  command 'bootloader'`). That is the V7 logo loop.

## Root cause (confirmed, side effect of the V6 fix)

- `device/samsung/gtexswifi/device.mk` installs `fstab.sc8830` in
  **`root/fstab.sc8830`** (TARGET_ROOT_OUT).
- The V6 fix changed `mkbootimg.mk` to build the boot ramdisk from
  **TARGET_RAMDISK_OUT** (to have a binary `/init` instead of the symlink to
  `/system/bin/init`).
- Consequence: the boot ramdisk came to contain only `init` and **lost
  `/fstab.sc8830`**. Verified:
  - `out/target/product/gtexswifi/ramdisk/` -> only `init`.
  - `out/target/product/gtexswifi/root/` -> contains `fstab.sc8830`.
- With `ro.hardware=sc8830`, `ReadDefaultFstab()` looks for `/fstab.sc8830` in the
  ramdisk and it is not there -> "failed to find device default fstab".

The fstab's `/system` entry is valid:
`/dev/block/platform/sdio_emmc/by-name/SYSTEM /system ext4 ro,errors=panic wait`.

## Recommended next step (V8, a single variable)

Include `fstab.sc8830` in the **boot ramdisk** (TARGET_RAMDISK_OUT), keeping the
binary `/init` of the V6 fix. Options:

1. Add in `device.mk` a copy of `fstab.sc8830` also to
   `TARGET_RAMDISK_OUT` (e.g. `ramdisk/fstab.sc8830`), or
2. Adjust `mkbootimg.mk` so the boot ramdisk includes
   `root/fstab.sc8830` in addition to RAMDISK_OUT's `init`.

Offline validation before proposing a flash:
- `verify-boot-ramdisk.sh` must confirm a binary `init` **and** the presence of
  `/fstab.sc8830` in the ramdisk.
- `verify-system-boot-candidate.sh` + `verify-odin-boot-system-package.sh`.
- Package with **legacy** sparse (finding V5: file_hdr_sz=32/chunk_hdr_sz=16),
  not modern AOSP sparse, or Odin rejects the system.img.

Interpretation of V8:
- If first-stage finds the fstab and mounts `/system`, the next error (if any)
  will already be from second-stage/SELinux/services.
- If it keeps skipping the mount, review the first-stage flags required by
  Lineage 17.1's fs_mgr (e.g. `first_stage_mount`) or the fstab search path.

## Process note

The V1 package the previous session left (standard AOSP sparse) did not write in
Odin; this device requires legacy sparse. The SYSTEM transfer chain was resolved
in V5.
