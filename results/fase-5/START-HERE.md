# START HERE -- onboarding for the next agent (Phase 5)

Date: 2026-09-18. LineageOS 17.1 / Android 10 port for Samsung SM-T280
(`gtexswifi`). This document is the entry point. Read it in full before touching
anything.

> *** UPDATE 2026-09-18 -- PHASE 5 CONSOLIDATED: animation VISIBLE on screen.**
> Read **`PHASE5-COMPLETE.md`** (summary, V5-V34 chain, findings) and **`PHASE6-START.md`**
> (next phase: framework bring-up). Final flashed candidate: **V34**
> (boot `8e11eb52` with binder FDA kernel). Graphics are solved; active work now
> is getting the framework (zygote/system_server) to boot up to the launcher.
> The rest of this document remains valid for environment, rules and method.

## 1. Reading order

1. **`results/fase-5/HANDOFF-CURRENT-STATE.md`** -- live state, current candidate,
   next step, uncommitted source changes to preserve. It is the source of truth
   for "right now".
2. **`results/fase-5/LOG-CAPTURE-METHOD.md`** -- HOW to debug with ADB without
   running out of data (the previous agent could not read logs). Essential.
3. **`results/fase-5/ARTIFACTS.sha256`** -- verifiable hashes of the current
   package and the stock rescue.
4. Per-version diagnoses (the "why" history), in order:
   `v7..v11-bootloop-recovery/DIAGNOSIS.md`, `v12..v14-hang-recovery/DIAGNOSIS.md`,
   `v15-hang`, `v15b-postformat`, `v15c-recovery/DIAGNOSIS.md`, and
   `PHASE5-V8..V16-*.md` (what each version changed).
5. `sm-t280-phase4/docs/HANDOFF-PHASE4.md` -- WSL access, Odin, stock rescues.
6. `PLAN-PHASE5-ENTRY.md` -- the phase's original plan.

## 2. Environment (summary)

- Windows workspace: `C:\Dev\Experiments\porting-galaxy-tab-a`.
- Build in WSL Ubuntu-22.04, user `lineage`, tree
  `/home/lineage/android/lineage-17.1`. Windows mount: `/mnt/c/Dev/...`.
- ADB: `sm-t280-phase1\tools\platform-tools\adb.exe` (ALWAYS use this one).
- Odin: `sm-t280-phase4\tools\downloads\odin-extracted\...\Odin3 v3.13.1_3B_Patched_Samfw.com.exe`.

## 3. Golden rules (or you get stuck like the previous agent)

- **ADB / Unix paths:** before commands with `/...` paths run
  `export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'`; otherwise Git Bash rewrites
  `/proc/last_kmsg` to a Windows path and "there is no data". (See LOG-CAPTURE-METHOD.)
- **WSL / variables:** inside `wsl.exe ... bash -c` inline shell variables do NOT
  expand here; use absolute paths or `.sh` files.
- **The hung system gives NO ADB.** To capture: force reboot to recovery (V21,
  Vol+ + Home + Power -> Enable ADB) and read `/proc/last_kmsg` (previous boot,
  persists in ramoops) or mount `/data` and read `/data/tombstones/`.
- **No** `repo sync` / `git checkout` in the Android tree: there are many
  uncommitted changes that would be lost (list in HANDOFF).
- **Safety:** only `boot`(KERNEL)+`system`(SYSTEM) are flashed via Odin AP, Auto
  Reboot OFF, no PIT/Re-Partition. `/data` is expendable (pre-accepted). Tested
  stock rescue: `sm-t280-phase5/packages/SM-T280-AQJ1-STOCK-BOOT-SYSTEM-ONLY-RESTORE.tar.md5`.

## 4. Iteration cycle (how each version is done)

1. Apply the change with an `apply-vNN-*.py` (idempotent) to the WSL tree.
2. Rebuild: `rebuild-bootimage.sh` (boot only; recompiles the kernel if `binder.c`
   changed) or `build-full-rom.sh` (full ROM).
   - **GOTCHA ramdisk files:** if you touch `fstab.sc8830` or `init.rc`, refresh
     their copy in `out/.../root/` (`cp` from the source) before building; they go
     in the boot ramdisk and `m bootimage` does not always regenerate them.
   - **GOTCHA init.cpp / init source (CRITICAL -- there are TWO different inits):**
     * The **ramdisk** init (`out/.../ramdisk/init`, ~1.37 MB) is **STATIC**
       (first-stage; runs BEFORE mounting /system). NEVER copy `system/bin/init`
       here: `system/bin/init` is **DYNAMIC** (linked against /system/lib) and in
       first-stage there are no libs -> immediate reboot loop (happened to V17).
     * `/system/bin/init` (inside **system.img**, ~540 KB, dynamic) is the
       **second-stage** init: there run `export_kernel_boot_props` (ro.hardware),
       `LoadBootScripts`/imports and `mount_all`. A change in init.cpp affecting
       second-stage (e.g. ro.hardware) goes to system.img, not the ramdisk.
     * `m bootimage` does NOT reliably recompile either. For ANY change in
       `system/core/init/*` or `fs_mgr`, the reliable path is **`build-full-rom.sh`
       (full mka)**, which rebuilds the ramdisk's static init AND system.img's
       `/system/bin/init` consistently, then repackage boot+system. ALWAYS verify
       that boot_sha256 (and system if applicable) changed.
3. Verify: `verify-boot-ramdisk.sh`, `verify-system-boot-candidate.sh`.
4. Package: `prepare-vNN-package.sh` -> `.tar.md5` Odin (`DO-NOT-FLASH`). Verify
   with `verify-odin-boot-system-package.sh`. SYSTEM goes in **legacy sparse**
   (headers 32/16), not modern AOSP, or Odin rejects it (finding V5).
5. Update docs (HANDOFF + PHASE5-VNN + diagnosis) and `ARTIFACTS.sha256`.
6. The USER flashes (you do not flash) and takes the tablet to recovery to capture.
7. Capture via ADB (section 3) -> diagnose -> next variable (one per iteration).

## 5. Where we are (as of this doc)

Hardware-verified progression: bootloop -> Android 10 second-stage (V12) ->
binder multi-device (V13) -> binder scatter-gather (V14) -> `/data` RW + format
(V15) -> unblocking `post-fs-data` (V16, current candidate).

Current candidate and exact next step: **see HANDOFF-CURRENT-STATE.md**. Open
blockers: `/data`/post-fs-data structure, HIDL layer
(`hwservicemanager`/`installd`/`keystore` looping) and, ahead, the Mali-400
graphics HAL. The immediate priority is to **regain visibility** (V16 seeks to
have `/data/*` and `/data/tombstones` created to read the real hwservicemanager
crash).

## 6. Key scripts

- Apply changes: `sm-t280-phase5/scripts/apply-vNN-*.py`.
- Build: `rebuild-bootimage.sh`, `build-full-rom.sh`.
- Verify: `verify-boot-ramdisk.sh`, `verify-system-boot-candidate.sh`,
  `verify-odin-boot-system-package.sh`.
- Package: `prepare-vNN-package.sh`, `package-system-for-odin.sh`,
  `legacy_sparse.py`.
- Runtime capture: `capture-first-boot.sh` (when there is ADB in system).
