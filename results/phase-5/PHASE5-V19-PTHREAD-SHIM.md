# Phase 5 -- V19: pthread_t shim in bionic (Mali graphics HAL)

Date: 2026-09-18. Status: in offline build/validation; `DO-NOT-FLASH`.

## Reason (from the V18 diagnosis)

With the plumbing now working (V18: /data + services), `surfaceflinger` aborts:
`invalid pthread_t 0xb6f86328 passed to pthread_getschedparam`, triggered by the
`android.hardware.graphics.composer@2.1` HAL (Mali-400). Android 10's bionic
validates `pthread_t` in `__pthread_internal_find` and aborts if it is not in
`g_thread_list`; the Android 5-7 era Mali blobs pass untracked pthread_t. The
upstream comment itself anticipates this ("...when Treble lets us keep vendor
blobs on an old API level"). See `results/phase-5/v18-recovery/DIAGNOSIS.md`.

## Change

`bionic/libc/bionic/pthread_internal.cpp` -> `__pthread_internal_find`
(`apply-v19-pthread-shim.py`): in the `async_safe_fatal` branch, instead of
aborting on an unknown pthread_t, warn (WARN) and **return the pointer**
(`return thread`). It is the standard shim of Android 10 ports with old blobs.

It goes in bionic (libc) -> **system.img**. Rebuilt with a full build
(`build-full-rom.sh`); **boot + system** are repackaged.

## Offline validation

- Build: `build-full-rom.sh` (recompiles libc + system.img). Log
  `results/phase-5/v19-full-build.log`.
- Boot: `verify-boot-ramdisk.sh` (static init 1.37MB).
- Packaging: `prepare-v19-package.sh`.

## Artifact

- Package: `sm-t280-phase5/packages/SM-T280-android10-pthread-shim-PHASE5-v19-DO-NOT-FLASH.tar.md5`
- package_sha256: `ffd889a16f7be31e2407c61b0957b218d4cd38ca15e206cdbe7edf974167feb4`
- boot_sha256: `6d1db53d14ab85df17c5d4937010d6aa3ec6fefcd0f289f8fceaa305f391ee6a`
- system_sha256 (legacy sparse): `39724458b8eeab89bc75f8b2ae5c9d5061bcae8df091d26d87968a362da2c1aa`
- Boot: static ramdisk init 1,376,260 B; `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`.

## Expected interpretation

- Success: `surfaceflinger` stops aborting over pthread_t; the Mali
  composer/gralloc HAL advances. Possible boot animation or next graphics problem
  (gralloc/EGL/formats/fences) -- which will decide whether the Android 5 Mali
  composes on Android 10.
- Also watch `audioserver` (SIGSEGV, audio HAL) -- probably another blob that will
  need its own adjustment.
- Verify after flashing: mount /data from recovery and read `/data/tombstones/`
  (already structured), plus the `last_kmsg`/`logcat`.
