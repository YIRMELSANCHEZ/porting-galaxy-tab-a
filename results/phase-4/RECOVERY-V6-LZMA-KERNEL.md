# Phase 4 -- Recovery v6 with LZMA ramdisk support

Date: September 16, 2026.

## Finding

V5 showed the packaging chain boots. The Android 10 kernel configuration used by
v4 contained `CONFIG_RD_GZIP=y`, but not `CONFIG_RD_LZMA`. At the same time, the
device tree generates the recovery ramdisk in LZMA format
(`LZMA_RAMDISK_TARGETS := recovery`).

The missing decompressor explains with high confidence the early hang of v4: the
kernel could not extract the initramfs it was supposed to run.

## Fix

The following were enabled and verified:

- `CONFIG_RD_LZMA=y`
- `CONFIG_DECOMPRESS_LZMA=y`

The kernel recompiled correctly. V6 keeps the full `Image` kernel, the Android
10 DT and the reduced LZMA diagnostic ramdisk used by v4.

| Field | Value |
|---|---:|
| Kernel | `11,891,524` bytes |
| LZMA ramdisk | `4,457,036` bytes |
| DT | `380,928` bytes |
| v6 image | `16,735,396` bytes |
| Recovery limit | `16,777,216` bytes |
| Margin | `41,820` bytes |
| Image SHA-256 | `cbec7c4a36bb5f665524ae9417439ea59eff9c8a8b74d959d32ed3ea8046a3b4` |

The independent extraction confirmed kernel and DT byte-by-byte, LZMA and CPIO
integrity and the presence of `init`, `recovery`, `adbd`, shell, linker and menu
resources.

**RECOVERY_V6_OFFLINE_VERIFY_PASS**

## Odin package

- `SM-T280-recovery-lzma-kernel-PHASE4-v6-DO-NOT-FLASH.tar.md5`
- Internal MD5: `fda47054d23f3d0d4183e2f8735977bf`
- SHA-256: `ae5e4914e164c43e89b5aa5b31f998992f5a511d115a4a05968eae056a4c45a1`

V6 remains marked `DO-NOT-FLASH` until authorization.

## Hardware result

Odin wrote v6 with `PASS`, but the direct boot hung at the `Samsung Galaxy Tab
A6` logo and showed no recovery or ADB:

**RECOVERY_V6_BOOT_FAIL**

The authorized rollback was run, writing only stock AQJ1 recovery v2. Odin and
the subsequent Android boot were correct:

**STOCK_RECOVERY_ROLLBACK_AFTER_V6_PASS**

LZMA support was a necessary fix, but not sufficient. V6 must not be flashed
again. The next isolation must use the Android 10 kernel with stock ramdisk, DT
and cmdline to evaluate the kernel only.
