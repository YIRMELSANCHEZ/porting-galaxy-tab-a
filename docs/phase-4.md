# Phase 4 -- Build and controlled boot

## Description

Production of a first build and a carefully authorized validation of the boot path. This is the first
potentially destructive phase.

## Goal

Achieve a minimal Android 10 boot while preserving a documented way to restore the original firmware.

## Checks and steps

1. Verify the tablet's identity, charge, cable, ports and authorized backups.
2. Obtain the official stock firmware and validate integrity/provenance.
3. Document the restore with Samsung tools and the data-loss risks.
4. Build a clean build and keep logs, manifest and hashes.
5. Validate image sizes against the real partitions.
6. Review boot image, ramdisk, fstab, SELinux and modules before using it.
7. Request explicit authorization for any unlock, recovery or flash.
8. Run the minimal approved method and capture serial/ADB/last_kmsg boot logs when possible.
9. Classify the result: bootloader, kernel, init, framework or graphical UI.
10. Restore stock if any stop criterion is triggered.

## Exit criterion

A first build that reaches ADB/bootanimation/UI, or a diagnosed and recovered failure. It does not
automatically continue to hardware bring-up.

## Execution completed

Status: `PHASE_4_RECOVERY_OBJECTIVE_MET` (2026-09-17).

The phase's recovery goal is met: there is an Android 10 / Lineage 17.1 recovery **validated on hardware**
(V21) with display, rotation, keys and ADB in the `recovery` state. The SM-T280/AQJ1 stock firmware was
verified and the restore path was tested repeatedly on hardware.

Path taken, summarized:

- Kernel bisect (v5->v10): the blocker was isolated to the **GCC 4.9 vs GCC 4.8 toolchain**, not the
  version; base kernel pinned at Linux 3.10.108 with GCC 4.8.
- Android 10 recovery userspace bring-up (v11->v21): fix of `mmap_rnd_bits` in the legacy kernel,
  single-buffer display/rotation and the ADB fix via FunctionFS without AIO. V20 was the first working
  runtime test; V21 the clean candidate verified on hardware.

Active gate: **recovery-only**. Booting a full Android 10 `system` is out of scope for this phase and
requires separate explicit authorization (it means writing `boot`/`system`).

Full detail and traceability in `results/phase-4/PHASE-4-STATUS.md` (v8-v21 consolidation section),
`results/phase-4/RECOVERY-V21-HARDWARE-VERIFY.md`, `sm-t280-phase4/docs/HANDOFF-PHASE4.md` and the manifest
`results/phase-4/ARTIFACTS.sha256`.
