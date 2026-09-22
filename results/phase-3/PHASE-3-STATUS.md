# Samsung SM-T280 -- Phase 3 Status

## Result

**PHASE_3_BUILD_PASS**

The diagnostic build of `lineage_gtexswifi-userdebug` for Android 10 / LineageOS 17.1 finished correctly on
September 16, 2026. Kernel, ramdisk, DT, `boot.img` and `system.img` were generated without interacting
with the tablet.

## Validated artifacts

| Artifact | Size | SHA-256 | Limit |
|---|---:|---|---|
| `kernel` | 11,883,332 B | `c0e49c31d16cd0a35d6cee37a4b1c71d7135ac22f4897daf6f92affe3fd4f4c5` | Included in boot |
| `ramdisk.img` | 309,312 B | `858f83dcd176309fbfa70b7c805949e0949f9bd29bbbd63d5b9cee7331424612` | Included in boot |
| `dt.img` | 380,928 B | `cd9e9b8970603606f1f9004cb4e1bad6a9f5712a3bfcdb43c2a8b42cf0f2b0c1` | Included in boot |
| `boot.img` | 12,580,020 B | `02f7b8223886b8cf63b019fa9f0db6b533b35b00a2967273f39a27613629588c` | PASS: 16,777,216 B |
| `system.img` | 1,000,157,572 B | `ecd57582e8c7887a31692b441faa4ef2a1d5e0ff5ca69d70b4f6b9994530be5d` | PASS: 2,147,483,648 B |

## Recovery limitation

The Android 10 AOSP recovery, already LZMA-compressed, produced a 17,098,752 B image versus a 16,777,216 B
physical partition. The diagnostic product sets `TARGET_NO_RECOVERY := true`; the partition size was not
faked. Shrinking recovery is left as separate work.

It is kept locally as `artifacts/recovery-oversize-DO-NOT-FLASH.img`, with SHA-256
`4aa1495b76f3f174ad0f408a2f72613acadba0b6347a7493c8d4813341eee4da`. The name and documentation expressly
state that it must not be flashed.

## Scope of the PASS

This PASS proves the build and the `boot`/`system` budget, not booting or hardware operation. GPU, video,
audio, Wi-Fi, Bluetooth, cameras, sensors and SELinux need later on-device validation. No flashing
authorization was generated and the tablet was not modified.
