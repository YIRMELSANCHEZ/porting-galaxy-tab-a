# Phase 4 -- Recovery v12, stock ramdisk recompressed with LZMA

## Objective

Isolate the ramdisk compression after V11's boot loop. V12 keeps the Linux
3.10.108/GCC 4.8 kernel validated in V10 and preserves exactly the file tree of
the functional stock recovery. The ramdisk's only difference is recompression
from gzip to LZMA.

## Verification

- Kernel SHA-256: `55084029bccc464a505bd1569215c39cea3b66f3393749ec36280de6d72df902`.
- Stock gzip ramdisk: `3,662,533` bytes.
- Stock LZMA ramdisk: `2,272,544` bytes.
- Extracted content of both ramdisks: identical per `diff -qr`.
- DT: identical to stock.
- Cmdline: `console=ttyS1,115200n8`.
- Image: `14,144,676` bytes.
- Margin in RECOVERY: `2,632,540` bytes.
- Image SHA-256: `6979a6ddb89e58767f96de3572d6686059f7ab83ec32ee0846bd31250b23c8c8`.
- Odin package: `SM-T280-recovery-stock-ramdisk-lzma-PHASE4-v12-DO-NOT-FLASH.tar.md5`.
- Internal MD5: `eafe4be13697c92bbbc8ad442a242b1d`.
- Package SHA-256: `751ea3998c6d871d447aab91bf75eb014abca7fdde9d60f53fafbee7420585aa`.

**STOCK_RAMDISK_LZMA_V12_OFFLINE_VERIFY_PASS**

## Interpretation of the pending test

- V12 PASS: LZMA works and the V11 failure lies in the Android 10 init/userspace.
- V12 FAIL: the kernel declares LZMA support but does not decompress this format
  correctly on hardware; the next image will have to use gzip and shrink the
  ramdisk.

## Hardware result

- Odin: `PASS`; only the `RECOVERY` partition was written.
- Direct boot: **PASS**.
- The recovery menu and `reboot system now` appeared correctly.

**STOCK_RAMDISK_LZMA_V12_BOOT_PASS**

The LZMA decompression path is validated. The V11 loop lies in the content or
behavior of the Android 10 recovery userspace.
