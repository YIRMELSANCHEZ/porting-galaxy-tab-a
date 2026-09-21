# Phase 5 -- V17: reboot loop from a badly built init (two different inits)

Date: 2026-09-18. Source: `results/fase-5/v17-recovery/last_kmsg.txt` (only ~41 KB,
ends at the bootloader `jump into kernel` -> very early reset).

## What happened

V17 returned to the **power on/off loop** (early reset), not the hang. Cause:
when building V17 I made two mistakes.

### Error 1 (the one that caused the reboot)

`m bootimage` did not recompile the `init` executable, so I copied
`system/bin/init` to the ramdisk as a workaround. But:

- `out/.../ramdisk/init` (~1.37 MB) is **STATIC** -- it is the **first-stage**
  init, runs BEFORE mounting `/system`.
- `out/.../system/bin/init` (~543 KB) is **DYNAMIC** (`interpreter
  /system/bin/bootstrap/linker`) -- it is the **second-stage**.

Putting the dynamic init in the ramdisk, in first-stage there are no
`/system/lib/*` -> the linker fails -> init does not start -> immediate reset (the
verified `boot.img` showed a 543404 B `init` in the ramdisk, when it should be
~1.37 MB).

### Error 2 (underlying: V17 goes in system.img, not the ramdisk)

The V17 change --`ro.hardware` default in `export_kernel_boot_props` and the
`import /init.${ro.hardware}.rc` in `LoadBootScripts`-- happens in **second-stage
init**, that is in **`/system/bin/init` (inside system.img)**. But since V12 the
V5 `system.img` has been reused (only boot changed). Therefore V17 **could not
take effect** without rebuilding system.img.

## Fix -> V18

Full build (`build-full-rom.sh` = `mka`): consistently rebuilds
- the ramdisk's **static** init (first-stage, with the V11/V12 patches), and
- system.img's `/system/bin/init` (second-stage, with V17 ro.hardware).
Then **boot + system** are repackaged (both fresh; the system_sha256 changes, no
longer the V5 legacy-sparse). Methodology note in START-HERE.md.

## Lesson (critical for the handoff)

There are TWO inits: static (ramdisk/first-stage) and dynamic (system/second-stage).
Never copy `system/bin/init` to the ramdisk. For changes in init/fs_mgr, do a
full `mka` and repackage boot+system.
