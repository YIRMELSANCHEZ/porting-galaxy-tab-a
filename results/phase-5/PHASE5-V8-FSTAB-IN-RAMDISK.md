# Phase 5 -- V8: fstab.sc8830 in the boot ramdisk

Date: 2026-09-17. Status: built and verified offline; `DO-NOT-FLASH` until the
user flashes it.

## Reason (from the V7 diagnosis)

V7 stopped aborting in first-stage but **skipped** it because it did not find the
fstab, and without `/system` init rebooted to bootloader (loop). Root cause: the
V6 fix builds the boot ramdisk from `TARGET_RAMDISK_OUT` (only `init`), while
`fstab.sc8830` is installed in `TARGET_ROOT_OUT` (`root/`). With
`ro.hardware=sc8830`, first-stage init looks for `/fstab.sc8830` in the ramdisk
and it was not there. See `results/phase-5/v7-bootloop-recovery/DIAGNOSIS.md`.

## Change (a single variable)

`device/samsung/gtexswifi/mkbootimg.mk`: before `MKBOOTFS`, copy
`$(TARGET_ROOT_OUT)/fstab.sc8830` to `$(TARGET_RAMDISK_OUT)/fstab.sc8830`, so the
boot ramdisk includes the fstab while keeping the V6 `/init` binary. Applied with
`sm-t280-phase5/scripts/apply-v8-fstab-ramdisk.py` (idempotent).

system.img, kernel, DT and cmdline were not touched. The package's system is the
same legacy-sparse validated since V5.

## Build and validation

- Rebuild: `rebuild-bootimage.sh` (`m bootimage`), OK in 01:13.
  Log: `results/phase-5/v8-rebuild-bootimage.log`.
- Boot ramdisk: `verify-boot-ramdisk.sh` ->
  **BOOT_RAMDISK_INIT_AND_FSTAB_PASS**
  (init binary `-rwxr-x--- 1376316` + `fstab.sc8830 2316`). boot 12,643,508 B.
  The verifier was extended to also require the fstab (before, only init).
- Packaging + verification: `prepare-v8-package.sh` -> **V8_PACKAGE_PASS**
  (`ODIN_SYSTEM_PACKAGE_PASS` + `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`).
  Legacy sparse OK: `file_hdr_sz=32 chunk_hdr_sz=16`, 524288 blocks of 4096.

## Artifact

- Package: `sm-t280-phase5/packages/SM-T280-android10-fstab-in-ramdisk-PHASE5-v8-DO-NOT-FLASH.tar.md5`
  (1,012,807,776 B). Content: exactly `boot.img` + `system.img`.
- package_sha256: `d1e8a82107972ffdd4d46f6a302b973e176e3aa1f67ed28e21f7dd05abfcd461`
- embedded_md5: `09753a096b8c753ab8cfa0de5f742dcd`
- boot_sha256: `1b2bac7e807e30e67e67d31e9344bce7dc87ef4dbc7e9af3a01e5171db0b63dd`
- system (legacy sparse) sha256: `15e45f117e3e64115ab659c68391206da1599d1cd5f51db82caca6c9105724f1`

## Hardware test (pending the user)

Odin AP, Auto Reboot OFF, no PIT/Re-Partition. Flash the V8 package, boot to
system and capture `last_kmsg` with `capture-first-boot.sh`.

## Expected interpretation

- If first-stage finds the fstab and mounts `/system`, the message "First stage
  mount skipped / failed to find device default fstab" must disappear and the
  boot advances to second-stage.
- **Probable next blocker (warning for the next iteration):** the boot ramdisk
  still has only `init` + `fstab.sc8830`; it does NOT carry `init.rc` or
  `init.*.rc` (they live in `root/` / `/system/etc/init`). After mounting
  `/system`, second-stage init will load its `init.rc`; if it does not resolve
  it, V9 will have to add the `init.rc`/`init.*.rc` to the ramdisk or confirm the
  system-as-root path (`/system/etc/init/hw/init.rc`). Keep the one-variable-per-
  iteration criterion and capture `last_kmsg` before proposing the next.
