# Phase 5.3 -- System first-boot procedure

Status: prepared offline; pending physical flash (requires the user).

## Authorization

The user pre-authorized (2026-09-17) the destructive flashing of `boot` +
`system` after passing the 5.1 offline validation. `/data` may be lost. Stock
rollback available. Touching PIT/modem/BL/param without specific authorization
remains forbidden.

## What is flashed

AP package (only `KERNEL` + `SYSTEM`; does not touch `RECOVERY`, which keeps V21):

- Package: `sm-t280-phase5/packages/SM-T280-system-android10-PHASE5-v1-DO-NOT-FLASH.tar.md5`
- Contains: `boot.img` (-> KERNEL partition) and `system.img` (-> SYSTEM partition).
- Hashes: filled in after 5.2 (see ARTIFACTS.sha256 and the final block of this doc).

## User steps (on return)

1. Put the tablet in **Download Mode** (Vol- + Home + Power, then Vol+).
2. Odin 3.13.1: load the `.tar.md5` in **AP**. **Auto Reboot OFF**, F. Reset Time ON.
   No Re-Partition, no PIT.
3. Press Start; wait for `PASS`.
4. Manual boot to **system** (not recovery): hold **Power only** until it
   reboots, or Vol- + Power to leave Download and let it boot normally.
5. Connect USB and notify Claude. Claude runs the diagnostic capture.

## What Claude does after boot (autonomous)

```bash
bash sm-t280-phase5/scripts/capture-first-boot.sh 120
```

Waits for ADB up to 120 s (even if the screen stays on the logo), and captures in
`results/phase-5/first-boot-runtime/`: `logcat`, `dmesg`, `getprop`,
`last_kmsg`/`pstore`, `ps`, mounts, boot markers. Classifies the stage:

- `NO_ADB` -> bootloader/kernel/init very early (no adbd).
- `INIT_OR_EARLY` -> init's adbd up, framework did not start.
- `FRAMEWORK_STARTING` -> zygote up, no `sys.boot_completed`.
- `FRAMEWORK_BOOT_COMPLETED` -> Android booted.
- `RECOVERY` -> booted to recovery, not system.

## Stop / rollback criteria

Restore stock if: abnormal temperature, no response in any mode, or the user
asks. Rollback:

- Full firmware: `sm-t280-phase4/stock/SAMFW.COM_SM-T280_TPA_T280XXU0AQJ1_fac.zip`.
- Stock recovery: `sm-t280-phase4/packages/SM-T280-AQJ1-STOCK-RECOVERY-RESTORE-v2.tar.md5`.

## Expectation

The first system boot is **diagnostic**. A bootloop or pre-framework stop
(init/SELinux/Mali graphics HAL) is likely. That is an expected and recoverable
result; it opens the 5.4 bring-up iteration (one variable per round).

## Package hashes (5.2 completed 2026-09-17)

- Package: `sm-t280-phase5/packages/SM-T280-system-android10-PHASE5-v1-DO-NOT-FLASH.tar.md5` (1,012,336,726 B)
- package_sha256: `998da11be181f9e7d90eee3c741fb18134b0f9eb30c4df2eb0a18343848b189d`
- boot_sha256: `cf3adde786b8aa7887d920f92fad8b6c7fb09d4c26cc5cec07c92149f18f648a`
- system_sha256: `6fa4a9496355a494e41aa3a0934e3e498ff858d63e4bd18ef2c757753d223e8c`
- embedded_md5: `5ca6dd05645ca034f729ab3208ef79e5`
