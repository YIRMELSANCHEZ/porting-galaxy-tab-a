# Phase 4 -- Recovery v10, kernel 3.10.108 with GCC 4.8

## Objective

Confirm whether the Linux 3.10.108 base adapted for Android 10 boots when using
the GCC 4.8 toolchain validated by V9. To isolate the kernel, V10 keeps the
stock ramdisk, DT, cmdline, offsets and signing format.

## Build

- Source: revision `95996f393501a578f0d0d263e6e1de5eefa819e9`.
- Kernel: Linux `3.10.108`.
- Toolchain: AOSP `arm-eabi-gcc (GCC) 4.8`.
- `CONFIG_RD_GZIP=y`.
- `CONFIG_RD_LZMA=y`.
- `CONFIG_DECOMPRESS_LZMA=y`.
- Kernel: `11,486,464` bytes.
- Kernel SHA-256: `55084029bccc464a505bd1569215c39cea3b66f3393749ec36280de6d72df902`.

## Artifact

- Image: `recovery-kernel-3.10.108-gcc48-v10-DO-NOT-FLASH.img`.
- Size: `15,535,268` bytes.
- Margin in RECOVERY: `1,241,948` bytes.
- Image SHA-256: `1948945c17360ce7cf1bad6df2b559ba376a8fa45ff5b2e86bd5559207a4dcf8`.
- Odin package: `SM-T280-recovery-kernel-3.10.108-gcc48-PHASE4-v10-DO-NOT-FLASH.tar.md5`.
- Internal MD5: `d348f4fff88dcc4fb8fa849a02ccc292`.
- Package SHA-256: `9bc79d954e6419b97fe4a613803bcc011645d6ce9989d36885c69808830c5419`.

Ramdisk, DT and cmdline match stock byte-for-byte.

**KERNEL_3_10_108_GCC48_BUILD_PASS**  
**KERNEL_3_10_108_GCC48_V10_OFFLINE_VERIFY_PASS**

## Pending test

- If V10 boots, the 3.10.108 update is viable with GCC 4.8 and the next step will
  be to introduce the Android 10 recovery ramdisk.
- If V10 fails, 3.10.65 will be kept temporarily and the essential Android 10
  support will be ported selectively.

## Hardware result

- Odin: `PASS`; only the `RECOVERY` partition was written.
- Direct boot to recovery: **PASS**.
- The stock recovery menu, including the `reboot system now` option, appeared
  correctly.

**KERNEL_3_10_108_GCC48_V10_BOOT_PASS**

Linux 3.10.108 was not the cause of the hang. The V8 FAIL, V9 PASS and V10 PASS
result shows the deciding factor was GCC 4.9 versus GCC 4.8.
