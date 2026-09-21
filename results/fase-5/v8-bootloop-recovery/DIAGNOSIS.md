# Phase 5 -- V8 diagnosis (failed) and the real root cause of the loop

Date: 2026-09-17. Source: `results/fase-5/v8-bootloop-recovery/last_kmsg.txt`
(captured via ADB from recovery, stable root shell).

## Result

V8 (fstab.sc8830 in the boot ramdisk) did **not** fix the loop. `last_kmsg`
shows exactly the same failure as V7:

```
init: init first stage started!
init: [libfs_mgr]ReadFstabFromDt(): failed to read fstab from dt
init: [libfs_mgr]ReadDefaultFstab(): failed to find device default fstab
init: Failed to fstab for first stage mount
init: First stage mount skipped (missing/incompatible/empty fstab in device tree)
init: Restarting system with command 'bootloader'
```

## Real root cause (confirmed by code and by artifacts)

The init flow was read in the tree:

- `first_stage_init.cpp`: after `DoFirstStageMount()`, init does
  `execv("/system/bin/init")` (second-stage). If `/system` is not mounted,
  `execv` fails -> `PLOG(FATAL)` -> reboot to bootloader. **That is the loop.**
- `DoFirstStageMount()` with an empty fstab prints "First stage mount skipped" and
  returns `true` (it does not reboot on its own); the reboot comes from the `execv`.
- `GetFstabPath()` checks `/odm/etc/fstab.sc8830`, `/vendor/etc/fstab.sc8830`,
  `/fstab.sc8830`. The flashed cmdline does carry `androidboot.hardware=sc8830`.

Decisive comparison of the build's two ramdisks:

- **TARGET_RAMDISK_OUT** (what V6/V7/V8 used): the **minimal system-as-root**
  ramdisk -- only `init`, `dev`, `proc`, `sys`, `apex`, `debug_ramdisk`
  and (V8) `fstab.sc8830`. **It has NO `/system` mountpoint, no `init.rc`, no
  `init.*.rc`, no `sepolicy`.**
- **TARGET_ROOT_OUT** (full legacy rootfs): `/system` (mountpoint), `init.rc`
  (34 KB), `init.sc8830.rc`, `sepolicy`, `default.prop`, `fstab.sc8830`, and the
  symlinks (`bin`->`/system/bin`, etc.). But `/init` is a **symlink ->
  `/system/bin/init`**.

Conclusion: the V6 fix (use RAMDISK_OUT to have a binary `/init`) **discarded the
whole legacy rootfs**. Without a `/system` mountpoint or a usable fstab in
first-stage, `/system` is not mounted and the `execv("/system/bin/init")` fails.
Adding only the fstab (V8) is not enough: the legacy rootfs structure is missing.

## Fix -> V9

Build the boot ramdisk from **TARGET_ROOT_OUT** (full legacy rootfs) replacing
the `/init` symlink with the real `init` binary from RAMDISK_OUT. That way the
ramdisk has: binary `/init` + `init.rc` + `init.*.rc` + `/system` mountpoint +
`sepolicy` + `fstab.sc8830`. Detail and implementation in
`results/fase-5/PHASE5-V9-LEGACY-ROOTFS.md`.
