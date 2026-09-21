# Phase 4 -- Recovery v7, kernel isolation

V7 changes a single component from the v5 base that booted:

- kernel: Android 10 recompiled with LZMA support;
- ramdisk: stock AQJ1 byte-for-byte;
- DT: stock AQJ1 byte-for-byte;
- cmdline: stock `console=ttyS1,115200n8`;
- offsets and page size: stock.

| Field | Value |
|---|---:|
| Image | `15,940,772` bytes |
| Margin | `836,444` bytes |
| SHA-256 | `02f6fe5bb42516945b0283155198a69238f1a416beb01b254d6ae0bda1afbed9` |

**KERNEL_ISOLATION_V7_OFFLINE_VERIFY_PASS**

Future interpretation:

- if v7 boots, the kernel can start hardware and the stock gzip ramdisk; the v6
  hang is in the Android 10 ramdisk;
- if v7 fails, the Android 10 kernel is itself incompatible and must be debugged
  before working on recovery or system.

Odin package: `SM-T280-recovery-kernel-isolation-PHASE4-v7-DO-NOT-FLASH.tar.md5`,
internal MD5 `cba2893fe06c91e2d962839170e9894f`, SHA-256
`cc5e3d4ffa917c7fadb440c8edc8e20bccdd16038353c5c466fcaaab3a6645fb`.

## Hardware result

Odin wrote v7 with `PASS`. The direct boot hung at the logo and showed no
recovery or ADB:

**KERNEL_ISOLATION_V7_BOOT_FAIL**

Since the gzip ramdisk, DT, cmdline and offsets were byte-for-byte stock and v5
with those same components did boot, the failure is isolated to the recompiled
Android 10 kernel.

Only stock AQJ1 recovery v2 was restored; Odin reported `PASS` and stock Android
booted again:

**STOCK_RECOVERY_ROLLBACK_AFTER_V7_PASS**

No other recovery should be tested until the kernel is debugged (`Image` format,
load, configuration, compiler, DT handling and differences from the stock
kernel).
