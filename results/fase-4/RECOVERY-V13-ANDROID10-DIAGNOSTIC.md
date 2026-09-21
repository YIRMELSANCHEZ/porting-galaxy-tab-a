# Phase 4 -- Android 10 diagnostic recovery v13

## Objective

Get an early ADB channel and prevent automatic reboots while isolating the
userspace failure observed in V11. V12 showed LZMA works.

V13 keeps V11's kernel, DT and general content, with these temporary diagnostic
changes:

- removes `critical` from `ueventd` and `charger` to prevent four service
  failures from causing an automatic reboot;
- sets `ro.adb.secure=0`;
- sets `persist.sys.usb.config=adb`;
- requests ADB root and `adbd` startup during `late-init`.

These modifications are diagnostic only and must be removed from the final image.

## Artifact

- Image: `recovery-android10-diagnostic-v13-DO-NOT-FLASH.img`.
- Ramdisk: `4,457,454` bytes.
- Ramdisk SHA-256: `a4f8f2f81dbbfcdcecb64c789d6b47d8f3847075cee85296a66ba2ad283d73d8`.
- Image: `16,329,892` bytes.
- Margin in RECOVERY: `447,324` bytes.
- Image SHA-256: `e0f597e545fdf0e2590a1d60750a67508db1bcba61efc374faeec261879de3d2`.
- Odin package: `SM-T280-recovery-android10-diagnostic-PHASE4-v13-DO-NOT-FLASH.tar.md5`.
- Internal MD5: `2b703b3fcdf543aa6864e0ad4552f8e2`.
- Package SHA-256: `9089f4d218e03613f3d0e2174f5815d1ad3afda9e543ba14d7df1c51deb41d18`.

**RECOVERY_ANDROID10_DIAGNOSTIC_V13_OFFLINE_VERIFY_PASS**

## Planned test

After boot, up to 60 seconds will be waited and ADB checked even if the screen
stays on the logo. If ADB appears, `logcat`, `dmesg`, properties and service
state will be captured before rebooting or restoring stock.
