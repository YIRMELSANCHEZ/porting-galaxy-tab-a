# Phase 4 -- Offline gate

## Status

**HOLD -- NO FLASH**

## Passed validations

| Check | Result |
|---|---|
| Target identity | SM-T280 / `gtexswifi` |
| Outer boot header | DHTB at offset 0 |
| Android boot header | `ANDROID!` at offset 512 |
| Kernel | 11,883,332 B |
| Declared ramdisk | 309,312 B |
| Declared device tree | 380,928 B |
| Boot page | 2,048 B |
| `boot.img` | 12,580,020 B / 16,777,216 B -- PASS |
| `system.img` | sparse ext4, 1,000,157,572 B / 2,147,483,648 B -- PASS |
| Expanded ext4 | 524,288 blocks of 4,096 B; clean state |
| `e2fsck -fn` | 3,657/131,072 inodes; 252,799/524,288 blocks; no errors |

## Blockers before interaction

1. **RESOLVED -- restore package:** exact `SM-T280` stock package, PDA/bootloader `T280XXU0AQJ1`, CSC `TPA`/`T280UVS0AQJ1`, verified offline by MD5, SHA-256 and internal inventory.
2. **HIGH -- functional recovery:** the original AOSP recovery is 17,098,752 B and does not fit. A separate candidate with a 10,484,900 B `zImage` was built offline that does respect the limit, but it has not yet been proven to boot.
3. **HIGH -- SELinux:** the boot cmdline contains `androidboot.selinux=permissive`. Useful for initial diagnosis, but does not meet the final security objective.
4. **PARTIAL -- write tool:** stock firmware and Samsung drivers are ready. Heimdall parses the PIT offline, but its USB compatibility with this unit is not yet demonstrated; the inspected Odin remains not approved for lacking a signature.
5. **RESOLVED -- data:** the user confirms they do not need to keep personal data and accepts that a restore may wipe `/data`.

## Decision

The images pass offline structural validation, but the interaction gate stays closed. Do not run Download Mode, recovery, Odin, Heimdall, ADB reboot or any write until the above blockers are resolved and reviewed.

## Recovery candidate

- File: `recovery-zimage-candidate-DO-NOT-FLASH.img`.
- Size: 10,484,900 B / 16,777,216 B -- structural PASS.
- SHA-256: `bf99e219db1df8343008f9551df0400550b9ff91f126a931bea96e15fdb6ea80`.
- Compressed kernel: 5,267,712 B; SHA-256 `923163f670e12c2c7a83be8ec9d2dc31dcf768352bf5a34d965a4288e03f2825`.
- Headers: DHTB at offset 0 and `ANDROID!` at offset 512.
- Status: **DETECTED/STRUCTURALLY VALIDATED, NOT BOOT TESTED**.
