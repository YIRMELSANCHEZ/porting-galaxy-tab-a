# Phase 4 -- Android 10 recovery v11 with GCC 4.8

## Objective

First combination of the two required, already-isolated components:

- the Linux 3.10.108 kernel that booted in V10, compiled with GCC 4.8;
- the Android 10 recovery ramdisk compressed with LZMA.

The DT keeps the byte-for-byte match with stock. The ramdisk omits only four
text images used during install/wipe and the recovery Wi-Fi module to respect
the 16 MiB physical limit; it keeps `init`, recovery, ADB, shell, linker, fonts,
icons and the `no command` screen.

## Artifact

- Image: `recovery-android10-gcc48-v11-DO-NOT-FLASH.img`.
- Kernel: `11,486,464` bytes.
- Kernel SHA-256: `55084029bccc464a505bd1569215c39cea3b66f3393749ec36280de6d72df902`.
- LZMA ramdisk: `4,458,317` bytes.
- Ramdisk SHA-256: `20b9df4e5dcad141aadead0907deb91d62f7a46f5a1376345692a31a7eabd494`.
- DT SHA-256: `cd9e9b8970603606f1f9004cb4e1bad6a9f5712a3bfcdb43c2a8b42cf0f2b0c1`.
- Image: `16,329,892` bytes.
- Margin in RECOVERY: `447,324` bytes.
- Image SHA-256: `049dcd4399a18eab809574da3de834ad8ffdae99063bcea8455c297ee4037324`.
- Odin package: `SM-T280-recovery-android10-gcc48-PHASE4-v11-DO-NOT-FLASH.tar.md5`.
- Internal MD5: `3b1be8a14295f22c34a4b5ac2f951a27`.
- Package SHA-256: `a3392fcfbede00c4cc7980199511bef20a34ed24ece8b8e5e1ef77bc600186d0`.

**RECOVERY_ANDROID10_GCC48_V11_OFFLINE_VERIFY_PASS**

## Pending test

V11 requires a direct boot test. A correct boot would show the kernel can
decompress and start the Android 10 recovery userspace; it would not yet prove
the full `system` boot or the functionality of all proprietary HALs.

## Hardware result

- Odin: `PASS`; only the `RECOVERY` partition was written.
- Direct boot: **FAIL**.
- Symptom: intermittent Samsung logo; the device tries to boot and returns
  repeatedly to the logo, without showing the recovery menu.
- Stock recovery v2 restored via Odin: `PASS`.
- Stock Android booted fully after the restore.

**RECOVERY_ANDROID10_GCC48_V11_BOOTLOOP**

V10 uses the same kernel, DT, signing and packaging and does boot. The failure
is therefore isolated to the Android 10 ramdisk/userspace or its compression
format, not the kernel or the Odin container. The next iteration must prioritize
persistent logs and prevent `critical` services from restarting the device
before ADB can become available.
