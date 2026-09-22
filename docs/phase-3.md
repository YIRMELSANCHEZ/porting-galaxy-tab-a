# Phase 3 -- Environment preparation, initial port and build

## Description and goal

Build a reproducible Linux environment for LineageOS 17.1, import the CM 14.1 baseline and obtain a tree
capable of attempting `kernel`, `ramdisk` and `systemimage`, without interacting with the tablet.

## Detailed plan

### 1. Host gate

- Ubuntu 20.04 or WSL2, with sources on a Linux filesystem.
- At least 16 GB of RAM and 250 GB free; 32 GB and 300 GB preferred.
- Check Java, Git, Python, compilers and Android tools.
- Do not install WSL or system packages without specific authorization.

### 2. Reproducible baseline

- Initialize `LineageOS/android` on `lineage-17.1`.
- Lock the SM-T280 repositories by commit and emit `repo manifest -r`.
- Keep the proprietary vendor separate and do not publish it automatically.

### 3. Minimal product migration

- Create `AndroidProducts.mk` and lunch `lineage_gtexswifi-userdebug`.
- Migrate the `vendor/cm` inheritance to `vendor/lineage`.
- Keep ARMv7-A/NEON and the stock layout.
- Enable the low-RAM profile and legacy LMK, since kernel 3.10 lacks PSI.
- Exclude GApps from the first build.

### 4. Kernel

- Build the community defconfig first, unchanged.
- Then evaluate namespaces, memcg/cgroup-device and pstore one by one.
- Preserve 32-bit Binder, ashmem, sync and legacy ION initially.
- Treat any fragment as a proposal until real support is confirmed.

### 5. HAL, blobs and security

- Build HWC/gralloc, audio, power, Wi-Fi and OMX as modules.
- Produce the unresolved ELF dependencies and justify each shim.
- Block graphics until the exact Mali userspace is available.
- Block multimedia acceptance until hardware H.264 is demonstrated.
- Keep SELinux enforcing as the final criterion.

### 6. Boot and partitions

- Reproduce offsets, 2048-byte page, separate DT and DHTB.
- Build the DHTB tools from source.
- Reject a boot over 16 MiB and a system over 2 GiB.
- Do not repartition or produce flashing instructions.

### 7. Order and traceability

1. Host tools and product.
2. Isolated kernel.
3. Ramdisk and init.
4. HALs and ELF check.
5. Minimal `systemimage`.
6. Diagnostic packaging, without installing it.

Each attempt keeps the manifest, commit, command, environment, full log, the first causal error and
hashes/sizes.

## Exit criterion

`PHASE_3_BUILD_PASS` if kernel, ramdisk and system image are produced within the limits, or
`PHASE_3_BUILD_BLOCKED` with a precise blocker. No result authorizes a test on the tablet.

## Execution performed

The preparation ran on WSL2 with Ubuntu 22.04.5, 8 CPUs, 24 GiB of RAM and 16 GiB of swap. LineageOS 17.1
was synced, the full manifest was pinned and the conservative product migration was applied. Soong/Kati
complete, Ninja enters a 68,027-task build and the kernel builds `gtexswifi-dt_defconfig` correctly.

Final state: `PHASE_3_BUILD_PASS`. Kernel, ramdisk, DT, `boot.img` and `system.img` were produced; both
partition images stay within their physical limits. The AOSP Android 10 recovery exceeds its 16 MiB
partition and was excluded from the diagnostic product without altering the declared limit. A copy marked
as non-flashable is kept for future shrinking and analysis.

This result attests to a build, not to booting or working. Tests on hardware belong to a later phase and
require a separate safety gate. The results are kept in `results/phase-3/`.
