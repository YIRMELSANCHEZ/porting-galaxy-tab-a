# Phase 4 -- Recovery write attempt 2

Date: September 16, 2026.

## Odin result

**ODIN_RECOVERY_WRITE_PASS**

The user explicitly authorized writing the `recovery` partition only again,
accepting the possible irreversible Knox change. Before starting, the following
was verified visually:

- device detected by Odin at `0:[COM4]`;
- only the `AP` field contained a file;
- `BL`, `CP`, `CSC` and `USERDATA` were empty;
- package: `SM-T280-recovery-zimage-PHASE4-v3-DO-NOT-FLASH.tar.md5`;
- MD5 check completed correctly;
- FRP had been previously verified as `OFF`.

The user started the operation and reported Odin's `PASS` result.

## Later state

The first manual attempt to enter recovery directly did not complete the key
combination and the tablet booted stock Android. ADB then confirmed:

- model `SM-T280`;
- device `gtexswifi`;
- firmware `LMY47V.T280XXU0AQJ1`;
- stable normal boot;
- absence of `/system/bin/install-recovery.sh`,
  `/system/etc/install-recovery.sh` and `/system/recovery-from-boot.p`.

A later reboot via `adb reboot recovery` left the device hung at the `Samsung
Galaxy Tab A6` logo. The custom recovery never showed a UI or ADB:

**CUSTOM_RECOVERY_BOOT_FAIL**

The persistent boot-to-recovery command caused the device to return to the same
point after a forced reboot. Only the stock AQJ1 recovery was restored via Odin
with the corrected package `SM-T280-AQJ1-STOCK-RECOVERY-RESTORE-v2.tar.md5`.
Odin reported `PASS`.

The stock recovery booted, `reboot system now` was selected without performing
wipes and stock Android booted fully again:

**STOCK_RECOVERY_RESTORE_PASS**

The v3 candidate must not be flashed again without an offline fix and a new
technical review.
