# Phase 3 results

Status: **PHASE_3_BUILD_PASS**.

The LineageOS 17.1 diagnostic build correctly produced kernel, ramdisk, DT, `boot.img` and `system.img`.
`boot.img` and `system.img` are within the known physical limits. The Android 10 recovery does not fit in
its 16 MiB partition and was excluded from the diagnostic product.

Evidence:

- `implementation-report.md`: implementation, adaptations and remaining risks.
- `PHASE-3-STATUS.md`: result, sizes and hashes.
- `phase3-pinned-manifest.xml`: exact tree revisions.
- `kernel-generated.config`: generated kernel configuration.
- `phase3-build.log`: kept log of previous attempts; the last full log also resides in WSL as
  `/home/lineage/android/lineage-17.1/phase3-build.log`.
- `artifacts/recovery-oversize-DO-NOT-FLASH.img`: recovery kept only for later analysis; it does not fit in
  the partition and must not be flashed.

The artifacts are experimental and must not be flashed yet.
