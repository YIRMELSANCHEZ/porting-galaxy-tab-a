# SM-T280 -- Phase 6 (framework boot, HALs, connectivity)

LineageOS 17.1 / Android 10 port to the Samsung Galaxy Tab A 7.0 2016 (SM-T280,
`gtexswifi`, Spreadtrum SC8830, Mali-400). This folder contains the **phase 6** work.

## Structure
- `packages/` -- Odin AP packages (`boot.img` + `system.img` in `.tar.md5`), V35..V55.
  Name: `SM-T280-android10-<topic>-PHASE6-vNN-DO-NOT-FLASH.tar.md5`.
- `scripts/` -- idempotent tree patchers (`apply-vNN-*.py`), packagers
  (`prepare-vNN-package.sh`) and copied build infrastructure (`legacy_sparse.py`,
  `package-system-for-odin.sh`, `verify-odin-boot-system-package.sh`,
  `prepare-legacy-sparse-system-odin-candidate.sh`).
- Docs and diagnostic logs: `../results/phase-6/` (includes `ARTIFACTS.sha256` =
  current index with hashes, `PHASE6-PLAN.md`, `*-wifi*.md`, `vNN-system-live/DIAGNOSIS.md`,
  and the `diag-*` folders from the `diag-device.ps1` script).

## Flash authorization (current)
Only `boot.img` (KERNEL) + `system.img` (SYSTEM) via **Odin AP**, with **Auto Reboot OFF** and
**no Re-Partition/PIT**. No BL/CP/CSC/modem/recovery/data wipe. The agent does NOT flash
or physically reboot; the user does.

## Status (V55)
Android 10 boots to the launcher. Mali-400 GPU (GLES2) in HW, audio OK, WiFi 2.4GHz +
internet OK. V55: power button (WAKE) + software video (the SPRD HW codecs are
Android 5.1 blobs, ABI-incompatible with Android 10) + `low_ram=true`. Current boot =
`dd2d8154` (V53). Pending: zram (V56, requires recompiling the kernel + WiFi module).

## Maintenance notes
- Phase 5 (graphics, V19..V34) is in `../sm-t280-phase5/` + `../results/phase-5/`.
- The shared build infra exists in both phases (copied) so each is
  self-contained. The Android tree is in WSL: `/home/lineage/android/lineage-17.1`.
- Always build as user `lineage` (`wsl.exe -u lineage`). Changes in `rootdir/*.rc`
  go to the RAMDISK -> require rebuilding `boot.img` (`mka bootimage`).
