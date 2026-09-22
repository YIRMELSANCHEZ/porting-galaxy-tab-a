# Phase 4 status

## Current result

**PHASE_4_RECOVERY_OBJECTIVE_MET** (2026-09-17)

An Android 10 / Lineage 17.1 recovery **validated on hardware** (V21) exists:
it boots with display, rotation, keys and ADB in `recovery` state. This closes
the Phase 4 functional-recovery objective.

**Operational gate: recovery-only. DO NOT write `boot`, `system`, `data`, PIT,
modem or any other partition without new explicit authorization.** Bring-up of a
full (bootable) Android 10 system is outside this phase and the current
authorization.

The rest of this document keeps the complete chronological history of the bisect
and bring-up (v3->v21) for traceability. The previous header of this block
--`PHASE_4_OFFLINE_PREPARATION_COMPLETE` / `HOLD -- NO MORE FLASHING`-- was
superseded by the v8-v21 chain summarized below.

## Hardware test result

- OEM Unlock was enabled through the official method and Download Mode confirmed
  `FRP LOCK: OFF`.
- Odin wrote the custom recovery v3 and showed `PASS`.
- Direct boot via `adb reboot recovery` hung at the `Samsung Galaxy Tab A6`
  logo.
- Result: **CUSTOM_RECOVERY_BOOT_FAIL**.
- Only the stock AQJ1 recovery was restored with the corrected v2 package; Odin
  showed `PASS`.
- The stock recovery booted and `reboot system now` returned the device to a
  fully functional stock Android.
- Rescue result: **STOCK_RECOVERY_RESTORE_PASS**.

The tablet is not bricked and the restore path is proven. The next activity must
be offline only: diagnose and rebuild recovery before requesting another
hardware test.

## Offline fix v4

Analysis identified with high confidence that v3 used the wrong kernel artifact:
a 5,267,712-byte `zImage` instead of the full 11,883,332-byte `Image` required
by this Spreadtrum tree. V4 was built with the same kernel as `boot.img`, the
same DT and a minimal recomposed ramdisk.

V4 is 16,729,252 bytes, leaves 47,964 bytes of margin and passed extraction and
byte-by-byte comparison of kernel/DT, LZMA/CPIO validation and essential-file
checks: **RECOVERY_V4_OFFLINE_VERIFY_PASS**.

V4 has not been tested on hardware yet and remains marked `DO-NOT-FLASH`.

### v4 hardware result

V4 was written by Odin with `PASS`, but hung at the logo when starting recovery:
**RECOVERY_V4_BOOT_FAIL**. Only stock AQJ1 recovery was restored with Odin
`PASS` and stock Android booted fully again:
**STOCK_RECOVERY_ROLLBACK_AFTER_V4_PASS**.

V3 and v4 are withdrawn from further testing. The next diagnosis must be offline
and start from a known-booting stock image, replacing one component at a time to
isolate kernel, DT, ramdisk and cmdline.

## V5 stock round-trip

The stock recovery was rebuilt offline using its original components. V5's
kernel, gzip ramdisk, DT and cmdline are byte-by-byte identical to stock; v5 is
only 4 bytes smaller and passed DHTB/Android, gzip, CPIO validation and the
partition limit: **STOCK_ROUNDTRIP_V5_OFFLINE_VERIFY_PASS**.

V5 is the next recommended test because it only exercises the
repackaging/signing chain. It remains marked `DO-NOT-FLASH` until authorization.

### v5 hardware result

Odin wrote v5 with `PASS`; v5 booted the recovery menu and `reboot system now`
returned the tablet to fully booted stock Android.

**STOCK_ROUNDTRIP_V5_HARDWARE_BOOT_PASS**

The repackaging, DHTB, signing, offsets and Odin-package chain is validated on
hardware. The next isolation will keep the stock kernel, DT, cmdline and header,
replacing only the ramdisk with the Android 10 one.

## Fix v6

The Android 10 kernel lacked `CONFIG_RD_LZMA` even though the recovery ramdisk
is generated in LZMA. `CONFIG_RD_LZMA` and `CONFIG_DECOMPRESS_LZMA` were
enabled, the kernel recompiled and v6 rebuilt.

V6 is 16,735,396 bytes, leaves 41,820 bytes of margin and passes full structural
validation: **RECOVERY_V6_OFFLINE_VERIFY_PASS**. It is the next proposed test,
not yet tested on hardware.

### v6 hardware result

V6 was written with Odin `PASS`, but hung at the logo:
**RECOVERY_V6_BOOT_FAIL**. Only stock recovery v2 was restored and Android
booted correctly again: **STOCK_RECOVERY_ROLLBACK_AFTER_V6_PASS**.

V7 will isolate the Android 10 kernel keeping stock gzip ramdisk, DT and cmdline.

## Conclusive result v7

V7 was written with Odin `PASS`, but hung at the logo despite using stock
ramdisk, DT, cmdline and offsets. V5 with those same components did boot.

**KERNEL_ISOLATION_V7_BOOT_FAIL**

The hang is isolated to the recompiled Android 10 kernel. Only stock recovery v2
was restored and Android booted correctly again:
**STOCK_RECOVERY_ROLLBACK_AFTER_V7_PASS**.

Gate at the time of v7: **HOLD -- KERNEL DEBUGGING REQUIRED** (resolved later by
the v8-v21 chain; see the consolidation section at the end of the document).

The preparation that does not require interacting with the tablet is finished.
During that offline preparation no ADB was run, the device was not rebooted and
nothing was written to it.

The read-only USB preflight was authorized and completed afterward. ADB
confirmed `SM-T280/gtexswifi`, Android 5.1.1, build and bootloader
`T280XXU0AQJ1`, with battery at 81%. There was no write or reboot.

The manual Download Mode preflight was also authorized and completed with no
writes. The screen confirmed `SM-T280`, official binary/system, FRP ON, Secure
Download Enabled, Knox Warranty Void `0x0` and RP SWREV `B:0 K:0 S:0`. Windows
recognized `04E8:685D` through the Samsung driver `2.21.4.0`. The tablet left
Download Mode without flashing and the user confirmed stock Android booted
afterward.

A minimal Odin package with a single `recovery.img` was prepared. Its embedded
MD5 is valid, the extracted payload matches the recovery candidate byte by byte
and the package contains no PIT or other partitions. It remains marked `DO NOT
FLASH` until final authorization.

Odin 3.13.1 accepted and loaded package version v3 correctly. The first two
variants were rejected before connecting the tablet due to the MD5 footer
format; no write occurred.

The first authorized attempt to write only `RECOVERY` was rejected by the
bootloader with `Custom Binary (RECOVERY) Blocked By FRP Lock`. Odin reported
`succeed 0 / failed 1`. The attempt will not be repeated and FRP/OEM Unlock will
not be modified without a separate decision and authorization.

## Completed

- Structural and cryptographic audit of `boot.img`, `system.img` and `dt.img`.
- Clean verification of the ext4 image inside `system.img` via `e2fsck -fn`.
- Confirmation of the Samsung/Spreadtrum DHTB header and the Android header of `boot.img`.
- Reproducible build of a recovery candidate with a compressed `zImage` kernel.
- Recovery candidate reduced to 10,484,900 bytes, within the 16 MiB physical partition.
- Separate offline scripts that contain no tablet-interaction commands.
- Restore plan and decision gates documented.

## Blockers before interacting

1. Confirm the PC has the Samsung driver and a compatible recovery/flash tool, without running it against the tablet yet.
2. Explicitly accept the risk that the first boot may fail and require a restore.
3. Separately authorize the first interaction with the device.

## Restore tools

- Official Samsung USB driver v1.9.5.0 downloaded from Samsung Developer.
- Valid Authenticode signature under `Samsung Electronics CO., LTD.`.
- Driver SHA-256: `0ecc9e47d836a7cff7215ec9cdf33dc7f3e416a7d5ededad522b978b2eb84a20`.
- The driver is installed and Windows registers ADB, USB Composite and Samsung
  Mobile USB Modem version `2.21.4.0`.
- Odin 3.13.1 3B Patched from SamFW was inspected without running it; the binary is unsigned and remains **NOT APPROVED / DO NOT RUN**.
- Detailed tool status in `sm-t280-phase4/stock/TOOLS-STATUS.md`.
- Heimdall 1.4.2 was installed in WSL and validated the 31-entry stock PIT offline.
- Confirmed from the PIT: `KERNEL` 16 MiB, `RECOVERY` 16 MiB and `SYSTEM` 2 GiB.
- No USB detection or any command against the device was run.

## Stock firmware search

- The exact nominal match `SM-T280 / TPA / T280XXU0AQJ1 / T280UVS0AQJ1` was located.
- The MD5 published by the historical archive is `a0bf55d45cfcaf9197055bdd7a670a62`.
- A direct query to the Samsung service via SamLoader returns `403 Model or region not found`; the old firmware is no longer served by that route.
- The integrated web download failed because the provider does not support private sessions; another archived copy requires signing in.
- `sm-t280-phase4/stock/` and `scripts/verify-stock-package.ps1` were prepared to locally validate the file obtained with a normal browser.
- Odin has not been installed or run and the tablet has not been interacted with.

## Verified stock firmware

- Archive: `SAMFW.COM_SM-T280_TPA_T280XXU0AQJ1_fac.zip`.
- Size: `1111411676` bytes.
- MD5: `a0bf55d45cfcaf9197055bdd7a670a62` -- exact match.
- SHA-256: `91c2615b15afe86176a9c35d372bff2fc785eafc3f74c022bce407ea916f9ecf`.
- AP: `boot.img`, `recovery.img`, `system.img`, `SPRDCP.img`, `SPRDDSP.img`, `nvitem.bin`.
- BL: `spl.img`, `sboot.bin`, `sboot2.bin`, `param.lfs`.
- CSC: `GTEXSWIFI_EUR_OPEN.pit`, `cache.img`, `hidden.img`.
- All ZIP/TAR containers pass the integrity read.
- The user confirmed they do not need to keep personal data, so a destructive restore of `/data` is acceptable if necessary.

## Open risks

- V8 (Linux 3.10.65, GCC 4.9, stock boot environment) was written with Odin
  `PASS`, but hung at the logo. Stock recovery v2 was restored with `PASS` and
  stock Android booted fully again.
- V9 (Linux 3.10.65, GCC 4.8 AOSP) is built and verified offline. Its write got
  Odin `PASS` and it booted the recovery menu correctly. This isolates GCC 4.9
  as the cause of the V8 failure and fixes GCC 4.8 as the base toolchain for the
  port's initial kernel.
- V10 (Linux 3.10.108, GCC 4.8, stock environment) got Odin `PASS` and booted
  the recovery menu. The 3.10.108 base is validated to continue.
- V11 combined the validated kernel with the Android 10 ramdisk. Odin got
  `PASS`, but the device entered a logo loop before showing the menu. Stock
  recovery v2 was restored and stock Android booted fully. The failure is
  isolated to the Android 10 ramdisk/userspace or its compression.

- The Android 10 recovery (V21) is functionally validated on hardware; the
  v8-v11 block above reflects intermediate steps already passed.
- `boot.img` forces SELinux permissive, appropriate only for initial diagnosis and not for a final version.
- The proprietary Spreadtrum/Mali blobs and multimedia acceleration can only be validated on hardware.
- An image fitting in the partition does not guarantee boot compatibility.
- Full `system` boot has not been attempted yet and requires separate
  authorization (see "Next gate").

## Consolidation of the v8-v21 chain (kernel bisect + recovery bring-up)

Constant methodology: change **one variable** per iteration on the v5 baseline,
which boots; full offline validation (sizes, compression, CPIO, 16 MiB partition
margin, hashes) before each flash; Odin **AP, `RECOVERY` only, Auto Reboot
OFF**; rollback to `SM-T280-AQJ1-STOCK-RECOVERY-RESTORE-v2.tar.md5` after each
failure. Per-version detail in `results/phase-4/RECOVERY-V*.md` and build/verify
logs in `sm-t280-phase4/packages/` (packages) and `results/phase-4/`
(images/logs).

### Kernel bisect (hang cause isolated)

| Ver | Isolated variable | Kernel / toolchain | Hardware |
|---|---|---|---|
| v5 | Pure stock round-trip | stock 3.10.108 / GCC4.8 | **BOOT_PASS** (baseline) |
| v6 | A10 kernel + RD_LZMA | 3.10.108 / GCC4.9 | BOOT_FAIL |
| v7 | A10 kernel only, rest stock byte-for-byte | 3.10.108 / GCC4.9 | BOOT_FAIL -> failure isolated to the kernel |
| v8 | Base kernel | 3.10.65 / GCC4.9 | BOOT_FAIL -> rules out a 65->108 regression |
| v9 | **Toolchain** | 3.10.65 / **GCC4.8** | **BOOT_PASS** |
| v10 | Version on GCC4.8 | 3.10.108 / **GCC4.8** | **BOOT_PASS** |

**Bisect conclusion:** the deciding factor was **GCC 4.9 vs GCC 4.8**, not the
kernel version. The port's base kernel is fixed at **Linux 3.10.108 compiled
with GCC 4.8** (`kernel-v10-gcc48-3.10.108-out/arch/arm/boot/Image`).

### Android 10 recovery userspace bring-up

| Ver | Change | Hardware / purpose |
|---|---|---|
| v11 | Kernel v10 + Android 10 recovery ramdisk (LZMA) | BOOTLOOP -> failure isolated to the ramdisk/userspace |
| v12 | Stock ramdisk recompressed gzip->LZMA | **BOOT_PASS** -> rules out LZMA as the cause; the failure is in the A10 userspace |
| v13 | Diagnosis: no `critical` in ueventd/charger, early ADB | Diagnostic iteration (ADB/logs channel) |
| v14 | `security.cpp`: tolerate missing `/proc/sys/vm/mmap_rnd_bits` on legacy 3.10 kernel | Fixes A10 init abort |
| v15-v16 | UI/USB and display: `graphics_fbdev` honors `ro.minui.force_single_buffer`; recovery rotation in `BoardConfig.mk` (`ROTATION_DOWN`/`hwrotation 180`) | Correct display and menu |
| v17-v19 | `adbd` diagnosis (FunctionFS) | Isolates the ADB failure |
| v20 | Legacy USB compat: `ro.adb.nonblocking_ffs=false`, `sys.usb.ffs.aio_compat=true` (FunctionFS without AIO on 3.10) | **First full functional runtime test**: display, keys and ADB `recovery` |
| v21 | Clean candidate (no diagnostic traces); BCB clear downgraded to informational due to missing `/misc` | **RECOVERY_V21_HARDWARE_VERIFY_PASS** (2026-09-17) |

### Source changes that must remain (in `lineage-17.1`)

- `system/core/init/security.cpp` -- tolerate missing `/proc/sys/vm/mmap_rnd_bits`.
- `bootable/recovery/minui/graphics_fbdev.cpp` -- honor `ro.minui.force_single_buffer`.
- `device/samsung/gtexswifi/BoardConfig.mk` -- recovery rotation.
- `bootable/recovery/recovery.cpp` -- missing `/misc`/BCB as informational.

### Final recovery status and artifact

- Package: `SM-T280-recovery-android10-clean-candidate-PHASE4-v21-DO-NOT-FLASH.tar.md5`.
- SHA-256: `970d11f9582de738435087c54ca3270c41f6e01a7969a85ce1c6d06110bd7a4b`.
- Runtime evidence: `results/phase-4/v21-runtime/` and `results/phase-4/RECOVERY-V21-HARDWARE-VERIFY.md`.
- Verified on hardware: ADB `recovery`, `SM_T280/gtexswifi`, kernel
  `3.10.108-g95996f39350`, correct FFS/display/rotation, informational BCB clear.

## Next gate

The Phase 4 recovery objective is met and validated on hardware. The current
authorization covers **only tests of the `recovery` partition via Odin**.

The next objective --booting a full Android 10 / LineageOS 17.1 system-- is
**not** covered by this test or the current authorization, because it involves
writing `boot` and `system`. Before any action in that direction:

1. A **separate, explicit authorization** must be requested and granted to write
   partitions other than `recovery`.
2. A destructive restore plan from the already-validated stock firmware
   (`SAMFW.COM_SM-T280_TPA_T280XXU0AQJ1_fac.zip`) must exist and be verified.
3. The first action after authorizing will still be a read-only status check,
   followed by a pause; no special reboot or flash should be bundled with that
   check.
