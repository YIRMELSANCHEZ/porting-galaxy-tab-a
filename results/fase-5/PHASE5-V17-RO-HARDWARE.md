# Phase 5 -- V17: force ro.hardware=sc8830 (root cause of /data + HALs)

Date: 2026-09-18. Status: in offline build/validation; `DO-NOT-FLASH`.

## Reason (from the V16 diagnosis)

The bootloader does not pass `androidboot.hardware`, so `ro.boot.hardware` is
empty and `init.cpp` leaves `ro.hardware = "unknown"` (default). That breaks
`init.rc:9 import /init.${ro.hardware}.rc` -> `init.sc8830.rc` (which has
`mount_all /fstab.sc8830`) **is never imported** -> `/data`/`/cache` are not
mounted -> mkdir RO -> keystore/installd/zygote in a loop. Also `${ro.hardware}`
governs HAL loading (`<name>.${ro.hardware}.so`), so "unknown" also breaks
graphics/HIDL. See `results/fase-5/v16-recovery/DIAGNOSIS.md`.

## Change (`sm-t280-phase5/scripts/apply-v17-ro-hardware.py`)

`system/core/init/init.cpp`, props table:
`{ "ro.boot.hardware", "ro.hardware", "unknown" }` -> default **"sc8830"**.
The V16 changes are kept (checkpoint/installkey off, harmless).

init goes in the boot ramdisk; only boot is recompiled (kernel and system
unchanged). Verified: the ramdisk init binary contains "sc8830".

## Expected scope (high)

A single change that can unblock several things at once:
- `import /init.sc8830.rc` works -> `mount_all /fstab.sc8830` runs -> `/data`
  and `/cache` mount RW -> post-fs-data creates the structure -> keystore/installd/
  zygote stop failing over missing dirs.
- `import /vendor/etc/init/hw/init.sc8830.rc` and other `${ro.hardware}` resolve.
- The `<name>.sc8830.so` HALs are located (relevant for hwservicemanager/
  graphics later).

## Artifact

- Package: `sm-t280-phase5/packages/SM-T280-android10-ro-hardware-PHASE5-v17-DO-NOT-FLASH.tar.md5`
- package_sha256: `4f95183d61e4c857026a569d882a65fd2f6958b6b7802e336be41d6cfdb017e1`
- boot_sha256: `e4692b9cff604adabe940ec8f99d8843f230d99483dec64ca6644bc560dea0a7`

## Build GOTCHA (important)

`m bootimage` does NOT recompile the `init` executable, so the first V17 build
came out with a boot identical to V16 (old init). Correct: `m init_second_stage`
-> `cp out/.../system/bin/init out/.../ramdisk/init` -> `rebuild-bootimage.sh`, and
verify that the `boot_sha256` changes. (Noted in START-HERE.md.)

## How to verify after flashing

Force recovery, mount /data and check structure + tombstones:
```
adb shell mount -t ext4 /dev/block/platform/sdio_emmc/by-name/userdata /data
adb shell 'ls /data'                 # expect misc, dalvik-cache, system, tombstones...
adb shell 'ls -l /data/tombstones/'  # real hwservicemanager crash, at last
```
- If `/data` has structure: mount_all runs -> root cause resolved. Read tombstones
  for the next front (HIDL/graphics).
- If `/data` is still empty: review why mount_all does not mount /data despite the
  import (with the now-more-readable boot).
