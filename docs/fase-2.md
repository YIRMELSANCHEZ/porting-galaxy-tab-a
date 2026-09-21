# Phase 2 -- Port research and strategy

## Description

Technical, documentary and code research to decide how Android 10 / LineageOS 17.1 could be built for the
Samsung SM-T280 (`gtexswifi`). This phase turns the Phase 1 findings into a verifiable architecture.

Phase 2 is **non-destructive**: it does not unlock, flash, install, reboot into special modes or alter the
tablet. It is allowed to consult public sources, download code to the computer, analyze files and, if
needed, repeat read-only ADB queries.

## Goal

Answer, with evidence:

1. Is there a correct kernel source that can be adapted to Android 10?
2. Is there a reliable device-tree base for `gtexswifi`?
3. Can the critical blobs and HALs be identified, especially graphics and multimedia?
4. Can an ARM32 build fit in the existing partitions without repartitioning?
5. Is there a sufficiently safe boot, diagnosis and restore strategy?

## Inputs

- Report: `../results/fase-1/PHASE-1-SM-T280.md`.
- ADB evidence: `../sm-t280-phase1/raw/`.
- Identity: `SM-T280`, `gtexswifi`, build `T280XXU0AQJ1`.
- Platform: Spreadtrum `sc8830` / `SC7730SW`, 32-bit ARMv7.
- Stock kernel: Linux `3.10.65-10429622`.
- Limits: boot 16 MiB, recovery 16 MiB, system 2 GiB and 1.5 GB RAM.
- Critical risks: kernel, Mali-400 and Spreadtrum OMX/Stagefright.

## Deliverables

Execution must create `results/fase-2/` with:

| File | Content |
|---|---|
| `source-inventory.md` | Sources, provenance, license, status and relevance |
| `repository-lock.md` | Exact URL, branch and commit of each candidate repository |
| `baseline-comparison.md` | Stock vs historical CM/Lineage and LineageOS 17.1 |
| `kernel-gap-analysis.md` | Defconfig, Android 10 patches and kernel blockers |
| `blob-hal-inventory.md` | Blobs/HALs, dependencies and availability per subsystem |
| `graphics-strategy.md` | Mali/EGL/gralloc/HWC strategy and alternative |
| `multimedia-strategy.md` | OMX/MediaCodec strategy and target-app requirements |
| `partition-budget.md` | Budget for boot, recovery, system and RAM |
| `security-strategy.md` | SELinux, namespaces and legacy HAL compatibility |
| `risk-register.md` | Risks, impact, mitigation and stop criterion |
| `PHASE-2-DECISION.md` | Decision `GO`, `CONDITIONAL_GO` or `NO_GO` |

No tokens, credentials, keys, full MACs or personal data are stored.

## Source priority

1. Android Open Source Project and official LineageOS documentation.
2. Samsung Open Source Release Center and Samsung Developer.
3. Official LineageOS repositories.
4. Public community repositories with an auditable Git history.
5. Forums only as leads; every claim must be confirmed via code or evidence.

For each download, record URL, date, license, hash and commit/tag. No community binaries are run during
this phase.

## Execution plan

### Step 0 -- Prepare the research

1. Create separate directories for sources, notes, tools and results.
2. Start a provenance log for every download.
3. Save the workspace Git state before adding material.
4. Define names for the device, kernel and vendor trees.
5. Do not mix stock captures with third-party code.

**Deliverable:** reproducible structure and inventory template.

### Step 1 -- Pin the exact baseline

1. Extract model, codename, build, bootloader, SoC, ABI and partitions from Phase 1.
2. Create a table of device invariants.
3. Exclude T285/`gtexslte` trees, except for expressly justified common references.
4. Compare partition names/sizes, page size, offsets and boot image of each candidate.
5. Reject ARM64, Treble, A/B or physical `vendor` assumptions.

**Gate G1:** every main candidate corresponds to `gtexswifi/SM-T280` or documents exactly the shared part.

### Step 2 -- Locate and verify the kernel source

1. Look for Samsung's GPL package for SM-T280 and the `T280XXU0AQJ1` family.
2. Record base version, defconfig, DTS/DTB and the expected toolchain.
3. Compare the official source with community `gtexswifi/sc8830` trees.
4. Identify built-in drivers and `mali`/`sprdwl` modules.
5. Assess history quality: real upstream, snapshot or untraceable fork.
6. Inventory the patches required for binder, ashmem, SELinux, seccomp, namespaces, cgroups and Android
   10.
7. Classify the patches as upstream, known backport, community or new development.
8. Review compiler/toolchain compatibility; do not build yet.

**Gate G2:** legally usable source, tied to the hardware and with sufficient defconfig/DTS. Any missing
critical driver must have a concrete alternative.

### Step 3 -- Audit the device trees

1. Inventory the repositories and branches of `android_device_samsung_gtexswifi`.
2. Review `BoardConfig.mk`, products, fstab, init, sepolicy, overlays and recovery.
3. Check partition sizes against the real evidence.
4. Review base/offsets/page size, separate DT and ramdisk compression.
5. Audit `extract-files.sh`, `setup-makefiles.sh` and `proprietary-files.txt` without running them.
6. Identify common trees and missing dependencies.
7. Compare related SC8830 devices only for verifiably common components.
8. Classify each element: reusable, portable or rewrite needed.

**Deliverable:** file/component/origin/quality/action matrix in `baseline-comparison.md`.

### Step 4 -- Inventory blobs and HALs

Split by subsystem:

- Graphics: Mali EGL/GLES, gralloc, HWC, ION and sync.
- Multimedia: OMX core, VPU, codecs, Stagefright extensions and firmware.
- Audio: primary/audio policy, mixer paths and codecs.
- Camera: HAL, sensors, ISP and firmware.
- Wi-Fi: `sprdwl`, firmware and private supplicant libraries.
- Bluetooth/FM: vendor library, firmware and bdroid config.
- Sensors, GPS, lights, power, vibrator and USB.

For each blob record path, ELF architecture, bitness, `NEEDED` dependencies, symbols, text relocations,
origin, license, consuming interface, shim need and risk.

In this phase `proprietary-files.txt` and the ADB listings are used as an initial inventory. No partitions
or private data are copied. A later extraction, if any, needs a separate procedure and authorization.

**Gate G3:** plausible coverage must exist for display/touch, GPU, H.264+audio, storage, Wi-Fi and USB.
Without a path for GPU or multimedia, the research stops or is widened.

### Step 5 -- Graphics strategy

1. Identify the version and full set of Mali r5p0 blobs.
2. Determine the interfaces of `gralloc.sc8830` and `hwcomposer.sc8830`.
3. Compare them with Android 10's SurfaceFlinger/gralloc/HWC.
4. Look for auditable Mali-400 + Android 10 ARM32 precedents.
5. Enumerate namespace, ION, sync-fence and symbol incompatibilities.
6. Compare three paths: stock blobs with shims, a later Spreadtrum BSP or temporary software rendering.
7. Do not accept software rendering as a final solution.
8. Define future tests for composition, rotation, video and suspend/resume.

**Deliverable:** main option, alternative and abandonment criterion in `graphics-strategy.md`.

### Step 6 -- Multimedia strategy

1. Relate stock OMX components to their libraries and dependencies.
2. Separate active, commented-out and software codecs.
3. Prioritize H.264 AVC, AAC/MP3 and A/V sync; do not assume HEVC/VP9.
4. Investigate Stagefright/OMX changes between Android 5.1 and 10.
5. Assess wrappers, codec XML, namespace exemptions and shims.
6. Define free samples and a profile/resolution matrix for Phase 5.
7. Identify the legitimate metadata needed from the target app: version, SDK, ABI, codecs, DRM and
   WebView.
8. Set the minimum: stable hardware H.264 at the resolution the app requires.

**Gate G4:** if only insufficient software decoding remains, or there is no stable H.264+audio, the risk
is `CRITICAL` and final use is not recommended.

### Step 7 -- Android 10 architecture and security

1. Design a non-A/B layout without modifying the partition table.
2. Assess system-as-root and ramdisk on the legacy Samsung/Spreadtrum boot.
3. Conceptually integrate vendor inside system, since there is no dedicated partition.
4. Review linker namespaces and pre-Treble blobs.
5. Study binder, servicemanager, hwservicemanager and legacy HALs.
6. Keep SELinux enforcing as the goal; permissive is not a final solution.
7. Compare stock/historical sepolicy with Android 10 domains.
8. Identify obsolete properties, init services and `/dev` permissions.

**Deliverable:** `security-strategy.md` with priority domains and a policy of not hiding denials.

### Step 8 -- Partition and memory budget

1. Budget kernel+DT+ramdisk within 16 MiB.
2. Estimate the LineageOS 17.1 ARM32 `system.img` without GApps.
3. Estimate a variant with minimal ARM32 GApps.
4. Reserve update headroom; do not fill 100% of `/system`.
5. Identify removable components and legitimate optimizations.
6. Do not base the plan on repartitioning the eMMC.
7. Estimate RAM for idle, system_server, SurfaceFlinger, WebView, GMS and video.
8. Design `low_ram`, LMK and swap/ZRAM for later validation, without applying them.

**Initial targets:** boot clearly under 16 MiB; system with at least 10% headroom in 2 GiB; GApps separate
from bring-up; no mandatory ARM64 dependency.

**Gate G5:** if the minimal build does not fit with headroom without repartitioning, `NO_GO` for this
approach.

### Step 9 -- Recovery and observability

1. Locate the exact official stock firmware without flashing it.
2. Record hashes, components and the intended restore tool.
3. Document soft brick, bootloop, kernel failure and ADB loss.
4. Identify the available logs: ADB, pstore/ramoops, last_kmsg or console.
5. Define the essential backups, especially EFS/prodnv, for a later authorized phase.
6. Do not create partition backups or enter Download Mode now.
7. Define stop/restore criteria for Phase 4.

**Gate G6:** do not authorize boot tests without a stock-restore procedure and verification of the correct
firmware.

### Step 10 -- Consolidate risks and decide

`risk-register.md` will have:

| ID | Subsystem | Evidence | Probability | Impact | Risk | Mitigation | Stop criterion | Status |
|---|---|---|---|---|---|---|---|---|

Mandatory initial risks:

- `KERNEL-01`: kernel 3.10 vs Android 10.
- `GPU-01`: Mali-400 + Android 5.1 EGL/HWC/gralloc.
- `MEDIA-01`: Spreadtrum OMX/VPU and H.264 for the target app.
- `VENDOR-01`: 32-bit pre-Treble blobs.
- `STORAGE-01`: 2 GiB system.
- `MEMORY-01`: 1.5 GB and GMS/WebView.
- `SECURITY-01`: SELinux enforcing and legacy HALs.
- `BOOT-01`: 16 MiB legacy boot and system-as-root.
- `RECOVERY-01`: safe restore before flashing.

## Recommended order

```text
Baseline
  -> kernel source
  -> device tree
  -> blob inventory
       -> graphics
       -> multimedia
  -> Android 10 architecture / SELinux
  -> partition and RAM budget
  -> recovery and observability
  -> risk register
  -> decision
```

Graphics and multimedia can be researched in parallel after the initial inventory. The decision waits for
both.

## Decision criteria

### GO

All of these hold:

- Kernel source/defconfig/DTS identified and legally usable.
- Verifiable device tree consistent with the real partitions.
- Plausible path for GPU/compositor and hardware H.264+audio.
- Sufficient inventory of critical blobs and dependencies.
- Boot and system fit with headroom without repartitioning.
- Complete ARM32 architecture with no mandatory ARM64 dependency.
- Documented SELinux/HAL strategy.
- Documented stock restore and stop criteria.

### CONDITIONAL_GO

Preparation/building can proceed in Phase 3 if the remaining blockers can be researched without flashing
and each has an alternative and an exit condition before Phase 4.

### NO_GO

Any one is enough:

- No sufficiently complete kernel source exists.
- No realistic strategy for GPU or H.264/audio.
- The minimal image does not fit without repartitioning.
- The critical blobs cannot be obtained legitimately or are unadaptable.
- A safe restore cannot be prepared.
- The effort exceeds the value of the goal versus safer alternatives.

## Validation

1. Every important claim links to code, official documentation or Phase 1 evidence.
2. Each repository is pinned to a commit, not just a branch.
3. Each critical blob has origin, architecture and dependencies.
4. Sizes state the method and margin of error.
5. Every `CRITICAL` risk has a verifiable mitigation or forces `NO_GO`.
6. A second review confirms that T285/`gtexslte` was not mixed in.

## Exit criterion

The phase ends with `results/fase-2/PHASE-2-DECISION.md` and one of:

- `PHASE_2_RESEARCH_PASS -- GO`
- `PHASE_2_RESEARCH_PASS -- CONDITIONAL_GO`
- `PHASE_2_RESEARCH_BLOCKED -- NO_GO`

Finishing the research does not authorize building or modifying the tablet. Moving to Phase 3 requires
reviewing the decision; unlock, recovery or flashing will always need explicit authorization.
