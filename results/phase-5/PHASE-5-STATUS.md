# Phase 5 status

> UPDATE 2026-09-17: SYSTEM transfer and boot advanced through V1->V8. The V1
> package (AOSP sparse) would not write in Odin: this device requires **legacy**
> sparse (resolved in V5). Then boot was debugged: V5 panic (VFS root), V6 (init
> binary in ramdisk), V7 (`androidboot.hardware=sc8830`), and **V8**
> (fstab.sc8830 in the boot ramdisk, current candidate). **Live state and next
> step in `results/phase-5/HANDOFF-CURRENT-STATE.md`.** Per-version diagnoses in
> `results/phase-5/PHASE5-V8-FSTAB-IN-RAMDISK.md` and
> `results/phase-5/v7-bootloop-recovery/DIAGNOSIS.md`. The below is the 5.0/5.1/5.2
> record (initial build) and is kept for traceability.

## Current result (initial build 5.0/5.1/5.2 -- historical)

**PHASE_5_ROM_BUILT_AND_PACKAGED** (2026-09-17)

- 5.0 full ROM build: **OK** (`build completed successfully 54:19`).
- 5.1 offline validation: **SYSTEM_BOOT_OFFLINE_VERIFY_PASS**.
- 5.2 Odin AP packaging: **ODIN_SYSTEM_PACKAGE_PASS**.
- 5.3 flash + first boot: **pending physical user action** (Download Mode + Odin).
  Autonomous capture tooling ready.

Gate: the package is `DO-NOT-FLASH` until the user flashes it. Only `KERNEL`
(boot) and `SYSTEM` will be written; recovery (V21), PIT, BL and modem are not
touched.

## 5.0 -- Build

- `lunch lineage_gtexswifi-userdebug; mka` in WSL Ubuntu 22.04, user `lineage`.
- Reproducible: in-tree kernel `kernel/samsung/gtexswifi` rev
  `95996f393501a578f0d0d263e6e1de5eefa819e9` (= tested V10 revision) + toolchain
  `arm-eabi-4.8` forced by `KERNEL_TOOLCHAIN` in `BoardConfig.mk`.
- Duration 54:19 with ccache. Log: `results/phase-5/build-full-rom.log`.
- Script: `sm-t280-phase5/scripts/build-full-rom.sh`.
- Process note: the first launch with `nohup &` died from `SIGHUP` (soong catches
  HUP when the WSL session closes). It was relaunched keeping the `wsl.exe`
  process alive in the foreground under a tool background task.

## 5.1 -- Offline validation (blocker passed)

`sm-t280-phase5/scripts/verify-system-boot-candidate.sh`; log
`results/phase-5/SYSTEM-BOOT-VERIFY.log`.

- boot.img: `12,166,324` B, margin `4,610,892` B under 16 MiB.
  Headers DHTB + `ANDROID!` + `SEANDROIDENFORCE`. Embedded kernel byte-identical
  to the product's `kernel`. Confirmed directly: `Linux version
  3.10.108-g95996f39350 ... gcc version 4.8`. cmdline SELinux permissive
  (diagnostic build).
- system.img: sparse `1,000,161,668` B; raw `2,147,483,648` B (= exactly 2 GiB,
  sized to the partition). `e2fsck -fn` clean.
- dt.img: `380,928` B, `cd9e9b89...` (identical to the DT of the tested chain).
- The verifier's two strings WARNs were a false negative of the in-script
  extraction; the kernel was confirmed by direct check.

## 5.2 -- Odin packaging

`sm-t280-phase5/scripts/package-system-for-odin.sh`; log
`results/phase-5/SYSTEM-PACKAGE.log`.

- AP package: `sm-t280-phase5/packages/SM-T280-system-android10-PHASE5-v1-DO-NOT-FLASH.tar.md5`
  (`1,012,336,726` B).
- Content (ustar): `boot.img` + `system.img`, nothing else (verified by extracting).
- PIT mapping (matches by file name): `boot.img`->KERNEL, `system.img`->SYSTEM.
- Embedded MD5 `5ca6dd05645ca034f729ab3208ef79e5` (valid: embedded==computed).
- package_sha256 `998da11be181f9e7d90eee3c741fb18134b0f9eb30c4df2eb0a18343848b189d`.
- Manifest: `results/phase-5/ARTIFACTS.sha256` (verified `OK`).

## 5.3 -- First boot (pending user)

Procedure and criteria in `results/phase-5/FIRST-BOOT-PROCEDURE.md`.

Autonomous part ready: `sm-t280-phase5/scripts/capture-first-boot.sh` will wait
for ADB up to 120 s, capture logcat/dmesg/last_kmsg/pstore/props/services in
`results/phase-5/first-boot-runtime/` and classify the boot stage.

Required physical action (user only): Download Mode -> Odin AP (Auto Reboot OFF,
no PIT/Re-Partition) -> manual boot to system -> connect USB.

## Expectation

First boot is **diagnostic**. Probably a bootloop or pre-framework stop
(init/SELinux/Mali graphics HAL). Expected and recoverable result; opens 5.4
(bring-up iteration, one variable per round). Stock rollback available.

## Load-bearing source changes (verified in the built tree)

- `system/core/init/security.cpp`: the mmap_rnd_bits tolerance patch for kernel
  3.10 ARM **is applied** (`__arm__` branch: if `MMAP_RND_PATH` is ENOENT ->
  WARNING + `Success()`, instead of `FATAL`). It is the fix that in recovery was
  v14; critical so the A10 init does not abort on this kernel.
- `device/samsung/gtexswifi`: `163b397 gtexswifi: build kernel with GCC 4.8`
  (committed).

## Open risks

- **`system/core/init/security.cpp` is modified without committing** (`git status:
  M init/security.cpp`) in the WSL tree. A `repo sync`/`git checkout` would lose
  it and reintroduce the init abort. It must be committed/preserved before any
  resync of the Android tree.
- Spreadtrum/Mali blobs and multimedia acceleration: only validatable on hardware.
- SELinux permissive: acceptable only in a diagnostic build.
- system.img fits and is clean ext4, but that does not guarantee a framework boot.
