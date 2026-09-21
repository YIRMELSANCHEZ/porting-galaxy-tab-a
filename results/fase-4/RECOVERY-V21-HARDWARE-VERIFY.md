# Phase 4 -- Recovery v21, hardware verification

Date: September 17, 2026.

## Context

V21 is the clean candidate (no diagnostic traces) built on the functional
runtime tested in V20: kernel `kernel-v10-gcc48-3.10.108`, display, keys, ADB and
legacy USB compatibility. The user flashed V21 in Odin (AP, `RECOVERY` partition
only) and enabled ADB from `Advanced -> Enable ADB`.

Verified package:
`sm-t280-phase4/packages/SM-T280-recovery-android10-clean-candidate-PHASE4-v21-DO-NOT-FLASH.tar.md5`
SHA-256 `970d11f9582de738435087c54ca3270c41f6e01a7969a85ce1c6d06110bd7a4b`
(matches the HANDOFF).

## Result

**RECOVERY_V21_HARDWARE_VERIFY_PASS**

| Check | Expected | Observed |
|---|---|---|
| `adb get-state` | `recovery` | `recovery` |
| `adb devices -l` | `model:SM_T280 device:gtexswifi` | `3100315d********  recovery  product:lineage_gtexswifi model:SM_T280 device:gtexswifi transport_id:3` |
| `ro.adb.nonblocking_ffs` | `false` | `false` |
| `sys.usb.ffs.aio_compat` | `true` | `true` |
| `ro.minui.force_single_buffer` | `true` | `true` |
| `ro.minui.default_rotation` | `ROTATION_DOWN` | `ROTATION_DOWN` |
| `ro.sf.hwrotation` | `180` | `180` |
| kernel | 3.10.108 gcc48 | `Linux localhost 3.10.108-g95996f39350 #1 SMP PREEMPT Thu Sep 17 00:01:33 CEST 2026 armv7l` |

## BCB / `/misc`

The historical `Failed to clear BCB message` error no longer appears as a
failure. The BCB clear action is logged as informational, consistent with this
device's layout without `/misc`:

```
[    1.313354] I:Skipping BCB clear: this legacy device has no /misc partition
[   23.401764] I:Skipping BCB clear: this legacy device has no /misc partition
```

Two early `E:` lines persist during init (`failed to find /misc partition` /
`Failed to set BCB message`) inherent to the absence of `/misc`; they do not
prevent recovery from booting or working. Mounting and checking `/cache` (ext4)
is done correctly.

## Evidence

Captured in `results/fase-4/v21-runtime/`: `recovery.log`, `getprop.txt`,
`dmesg.txt`, `proc-mounts.txt`, `partitions-by-name.txt`, `input-devices.txt`,
`uname.txt`, `adb-id.txt`.

No other partition was written. `Auto Reboot` was disabled and the boot to
recovery was manual. The stock rollback package
`SM-T280-AQJ1-STOCK-RECOVERY-RESTORE-v2.tar.md5` remains available.

## Resulting status

V21 is promoted from candidate to **Android 10 / Lineage 17.1 recovery validated
on hardware**. It closes the Phase 4 functional-recovery objective. The next step
is no longer recovery: it is deciding on booting a full Android 10 system (not
covered by this test), which will require separate authorization because it
involves partitions other than `recovery`.
