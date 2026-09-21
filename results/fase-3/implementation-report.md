# Phase 3 -- Implementation report

## Host and environment

| Check | Result | Status |
|---|---|---|
| Host | Windows 11 Pro | PASS |
| WSL | WSL2 | PASS |
| Distribution | Ubuntu 22.04.5 LTS | PASS |
| WSL resources | 8 CPUs, 24 GiB RAM, 16 GiB swap | PASS |
| Java | OpenJDK 8 | PASS |
| `repo` | Google's official launcher | PASS |
| Sources | 112 GiB on a Linux filesystem | PASS |
| Free space | 842 GiB | PASS |

Ubuntu 22.04 was used because Ubuntu 20.04 was no longer available in the current WSL catalog. The
compatibility dependencies, including Java 8, were installed explicitly.

## Reproducible baseline

| Tree | Commit |
|---|---|
| `device/samsung/gtexswifi` | `0826fd4d9714e0c5568383a408a55801b958c9c2` |
| `kernel/samsung/gtexswifi` | `af605083776fb8ec1197e7aafb291bff6043c0a2` |
| `hardware/sprd` | `13ebb821b17fcd53e7c02dc1b11374f56046109a` |
| `vendor/samsung/gtexswifi` | `b65668464d13a608d74670fad197d351c71e3e0c` |

The full pinned manifest has SHA-256 `5a852ead59e2cd71c87ce42757b9c0e90ff82f610534831feb3e29b252f66c1a`.
The sync needed retries against transient Git failures. The obsolete `external/nano` project is fetched
directly from its official branch because the `repo` server returned a persistent error for that project.

## Applied migrations

- Modern `lineage_gtexswifi-userdebug` registration and LineageOS inheritance.
- ARMv7-A/NEON, low-RAM and legacy LMK without PSI profile.
- Kernel GCC 4.9 toolchain included in LineageOS 17.1.
- Disabling nine incompatible CM 14.1 automatic patches.
- Adapting inherited ARM module and source labels.
- Isolating the old `audio_effects.conf`.
- Removing duplicate source/blob producers and using ClearKey Q.
- Using the Android 10 init services for media and SurfaceFlinger.
- Adapting the separate DT rule to the modern kernel task.
- Initial compatibility adjustments for Bluetooth and Power HAL.

`BUILD_BROKEN_DUP_RULES` was not enabled; every collision was resolved explicitly. The proposed Android 10
kernel fragment remains review-only and was not merged automatically.

## Build result

The build completed Soong/Kati and Ninja and correctly generated kernel, ramdisk, DT, `boot.img` and
`system.img`. The last incremental run finished with `#### build completed successfully (01:31) ####`.

During the adaptation, the Spreadtrum Wi-Fi type errors, old graphics/ION/OMX APIs, init rules, SELinux
policy, explicit `liblog` dependencies, `SensorManager`, `GraphicBufferMapper` and `AudioSystem`
migrations, and obsolete linker options were resolved in a bounded way.

The Chromium WebView ARM prebuilt had been left as a 133-byte Git LFS pointer. The exact 96,200,674-byte
object with SHA-256 `bd638537aec0fe398c2bae0487947029a6705fd8497f5909e7b6608dd5760bc6` was downloaded. The
build script now detects, resolves and validates this case.

`boot.img` uses 12,580,020 bytes of 16,777,216 and `system.img` 1,000,157,572 bytes of 2,147,483,648.
Their hashes are recorded in `PHASE-3-STATUS.md`.

The AOSP recovery, even with LZMA, uses 17,098,752 bytes and exceeds the 16 MiB partition by 321,536 bytes.
It was excluded from the diagnostic product without altering the physical size and a local copy marked
`DO-NOT-FLASH` was kept.

## Assessment

Phase 3 reaches `PHASE_3_BUILD_PASS`: a complete diagnostic set for boot/system within limits exists. This
does not prove booting or operation. Wi-Fi, graphics, OMX/multimedia, audio, cameras, sensors and SELinux
still lack functional validation on hardware. Recovery requires shrinking before it can be a use candidate.

The tablet was not interacted with and this result does not authorize flashing.
