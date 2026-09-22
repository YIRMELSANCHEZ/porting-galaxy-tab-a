# Phase 5 -- Entry plan (hardware bring-up)

Date: 2026-09-17. Execution status: **5.0/5.1/5.2 completed; 5.3 pending physical
user action** -- see `results/phase-5/PHASE-5-STATUS.md`.

## Phase objective

Get a LineageOS 17.1 / Android 10 ROM that **boots on the SM-T280** and, on top
of it, enable and stabilize the device subsystems up to a functional hardware
matrix (display, GPU, audio, Wi-Fi, BT, sensors, battery, storage, codecs) -- see
`docs/phase-5.md` for the checklist.

## Starting state (verified 2026-09-17)

- `device/samsung/gtexswifi` and `vendor/samsung/gtexswifi` present in the tree.
- `out/target/product/gtexswifi/` contains recovery components and `boot.img`,
  **but not `system.img`**: no full bootable system exists yet.
- Bootable-proven kernel: `kernel-v10-gcc48-3.10.108-out/arch/arm/boot/Image`
  (Linux 3.10.108, **GCC 4.8**). GCC 4.9 was ruled out in the bisect (v8 FAIL,
  v9/v10 PASS).
- Android 10 recovery (V21) validated on hardware.
- WSL with 794 GiB free; `out/` uses 42 GiB.

## Current authorization (recorded)

- The user **pre-authorizes the destructive flashing of `boot` + `system`** once
  the build passes the offline validation (2026-09-17).
- Conditions that remain:
  - No flashing if the offline validation does not pass.
  - Odin **AP**, `Auto Reboot OFF`; the physical boot is requested from the user.
  - No writing PIT, modem, `param` or unlisted partitions without new specific
    authorization.
  - `/data` loss accepted by the user; stock rollback available.

## Critical build gate: the boot.img kernel

The boot failure was isolated to the **GCC 4.9 vs GCC 4.8 toolchain**. The
Lineage tree's default build might not use GCC 4.8 and would reintroduce exactly
that failure. Therefore, **the ROM's `boot.img` must carry the kernel equivalent
to the already-tested V10 (3.10.108, GCC 4.8)**. Two paths:

1. Configure the device tree's kernel build to force GCC 4.8 and the same config
   as V10, and validate that the resulting `Image` matches in version and
   behavior.
2. Repackage the ROM's `boot.img` replacing its `Image` with the tested V10
   (same pattern used in the recovery v10-v21), keeping the ROM's `boot` ramdisk.

Path 1 is preferable (reproducible); path 2 is the fallback if 1 does not fit.

## Source changes and their scope in system

Of the 4 changes that "must remain":

- `system/core/init/security.cpp` (mmap_rnd_bits absent in kernel 3.10) --
  **also applies to the system boot**; init runs the same.
- `bootable/recovery/minui/graphics_fbdev.cpp`, `recovery.cpp`,
  `device/.../BoardConfig.mk` (rotation) -- specific to **recovery/minui**; they
  do not govern the system UI (SurfaceFlinger/HWC/gralloc with Mali blobs). The
  system boot will expose its own graphics bring-up.

**Realistic expectation:** just as recovery needed v11->v20, the first system
boot will probably require several iterations (init, SELinux, Mali/Spreadtrum
graphics HALs, services) before a stable UI. The first build is diagnostic.

## Plan by sub-phases

### 5.0 -- Full ROM build (offline)

```bash
cd /home/lineage/android/lineage-17.1
source build/envsetup.sh
lunch lineage_gtexswifi-userdebug
mka   # droid target: system.img, boot.img, ramdisk, etc.
```

- Ensure the kernel gate first (previous section).
- Keep build logs, source manifest and hashes.

### 5.1 -- Offline validation (blocking before any flash)

- Sizes against the `GTEXSWIFI_EUR_OPEN.pit` PIT: `SYSTEM` 2 GiB, `BOOT` 16 MiB,
  `RECOVERY` 16 MiB. `system.img` (sparse/raw) must fit in 2 GiB.
- Android/DHTB header of `boot.img`; embedded kernel = V10 (version and hash).
- `e2fsck -fn` on system's ext4 if raw; sparse consistency.
- Review fstab, SELinux (contexts/policy) and cmdline.
- Reuse/extend `sm-t280-phase4/scripts/verify-recovery-candidate-v4.sh` with an
  analogous verifier for `system`+`boot`.

### 5.2 -- Odin packaging (marked DO-NOT-FLASH until validation)

- **AP** package with `boot.img` + `system.img` (sparse). No PIT, no BL, no CSC.
- Decide on recovery: keep V21 (`RECOVERY` is not touched in this flash) or
  include its repackaging only if needed. By default: **do not touch recovery**.
- Valid MD5 footer; byte-by-byte payload verification.

### 5.3 -- Controlled diagnostic boot (requires the pre-authorized flash)

- Odin AP, `Auto Reboot OFF`. User flashes and boots to system manually.
- Wait up to ~120 s for ADB even if the screen stays on the logo.
- Capture `logcat`, `dmesg`, `getprop`, `last_kmsg`/`pstore`, services, in
  `results/phase-5/first-boot-runtime/`.
- Classify the result: bootloader / kernel / init / SELinux / HAL / framework /
  SurfaceFlinger / UI.
- Stock rollback if any stop criterion fires.

### 5.4+ -- Bring-up iteration

- Attack the first isolated blocker (predictably init/SELinux or graphics HAL),
  one variable per iteration, with the same rigor as the Phase 4 bisect.
- Progressively fill the hardware matrix of `docs/phase-5.md`.

## Rollback

- Full verified stock firmware:
  `SAMFW.COM_SM-T280_TPA_T280XXU0AQJ1_fac.zip`
  (MD5 `a0bf55d45cfcaf9197055bdd7a670a62`).
- Destructive restore of `/data` accepted by the user.
- Stock recovery `SM-T280-AQJ1-STOCK-RECOVERY-RESTORE-v2.tar.md5` available.

## Exit criterion for the boot sub-phase

A first boot that reaches ADB/bootanimation/system UI (even if unstable), or a
failure **diagnosed and recovered** to stock. It does not continue automatically
to subsystem stabilization without reviewing risks.

## Open risks

- Proprietary Spreadtrum/Mali blobs and multimedia acceleration: only validatable
  on hardware.
- A `boot.img` with SELinux permissive is acceptable only for initial diagnosis.
- An image fitting in its partition does not guarantee it boots.
- The first system boot may enter a bootloop; that is an expected and recoverable
  result, not a plan failure.
