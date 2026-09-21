# Phase 4 -- Recovery v9, kernel 3.10.65 with GCC 4.8

## Reason

V8 kept stock ramdisk, DT, cmdline and packaging, but the Linux 3.10.65 kernel
compiled with GCC 4.9 hung at the logo. The stock kernel that does boot declares
GCC 4.8. V9 changes only the toolchain to the official AOSP GCC 4.8 version to
isolate that difference.

## Build

- Source: revision `74c1b5f015fd39a8eb5a30e7ec3ac242ace51721`.
- Kernel: Linux `3.10.65`.
- Toolchain: AOSP `arm-eabi-gcc (GCC) 4.8`, `lollipop-release` branch.
- Kernel: `11,350,120` bytes.
- Kernel SHA-256: `f7170e257354c37981192520816c000c282a6e1d5ba0d10bc65f50e5b80cf9b6`.
- Stock ramdisk SHA-256: `e696d7c1c9de7909afa26c7f81d61c481d76dc20749b87026a4c6c82be6b32d6`.
- Stock DT SHA-256: `cd9e9b8970603606f1f9004cb4e1bad6a9f5712a3bfcdb43c2a8b42cf0f2b0c1`.
- Stock cmdline: `console=ttyS1,115200n8`.

## Artifact

- Image: `recovery-kernel-3.10.65-gcc48-v9-DO-NOT-FLASH.img`.
- Size: `15,400,100` bytes.
- Margin in RECOVERY: `1,377,116` bytes.
- Image SHA-256: `ea3c9499c8c6e16a04f7198bc0ab9545469a79ec80436a1f9135b370e128d17e`.
- Odin package: `SM-T280-recovery-kernel-3.10.65-gcc48-PHASE4-v9-DO-NOT-FLASH.tar.md5`.
- Internal MD5: `9130bb5f5f9681c049929406392e14a6`.
- Package SHA-256: `47c0bf7547646fb3a5479f0f216aa4aea74effa86d5eaf578a7b6e1f3d2efcc2`.

**KERNEL_3_10_65_GCC48_BUILD_PASS**  
**KERNEL_3_10_65_GCC48_V9_OFFLINE_VERIFY_PASS**

## Interpretation of the pending test

- If V9 boots, GCC 4.9 was incompatible with this base/vendor and GCC 4.8 will be
  adopted for the port's initial kernel.
- If V9 fails, the next isolation will compare the Samsung production config and
  the available `gtexswifi-dt_defconfig`. The stock kernel does not expose
  `IKCONFIG`, so that comparison will require rebuild and symbol analysis, not a
  direct extraction from `/proc/config.gz`.

## Hardware result

- Odin: `PASS`; only the `RECOVERY` partition was written.
- Direct boot to recovery: **PASS**.
- The stock recovery menu appeared correctly.

**KERNEL_3_10_65_GCC48_V9_BOOT_PASS**

The GCC 4.9->GCC 4.8 change, keeping the same 3.10.65 revision and the same stock
boot environment, turns the failure result into success. GCC 4.9 is therefore
ruled out for this device's initial base. The port's boot kernel must be built
with GCC 4.8 until an isolated test proves another toolchain preserves
compatibility.
