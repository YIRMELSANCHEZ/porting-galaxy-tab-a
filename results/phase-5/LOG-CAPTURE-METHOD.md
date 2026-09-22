# How boot logs are captured (the method that WORKS)

Date: 2026-09-18. This document explains exactly how the `last_kmsg`/logcat are
obtained in each Phase 5 test. The previous agent could not get data or recognize
the tablet even with ADB enabled; below are the reasons and the correct
procedure.

## 1. The right ADB (repo binary)

ALWAYS use the ADB that ships in the repo, not a system adb:

`sm-t280-phase1\tools\platform-tools\adb.exe`

Reason: it matches the installed Samsung USB driver and the project state. A
different `adb` (from PATH, from another SDK) may not enumerate the device or may
clash with another adb server already running. If in doubt: `adb kill-server` and
retry with the repo binary.

## 2. KEY GOTCHA: Git Bash / MSYS path conversion

Commands are launched from Git Bash (the Bash tool). Git Bash/MSYS **rewrites
Unix-style paths** (`/proc/last_kmsg`, `/sys/...`, `/data/...`) to Windows paths
(`C:/.../proc/last_kmsg`) BEFORE passing them to `adb shell`. Result:
`adb shell 'cat /proc/last_kmsg'` fails or returns garbage, and it looks like
"there is no data" or "the tablet does not respond".

**Solution (essential):** disable the conversion before each call:

```bash
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'
```

With that, `/proc/last_kmsg` reaches the device shell intact. This is the most
likely cause of the previous agent "getting no data".

(Related note, for the WSL/build side: inside `wsl.exe ... bash -c` inline shell
variables do not expand in this environment; you must use absolute paths or `.sh`
files. It is a different problem, of the build, not of ADB.)

## 3. Why there is NO ADB on the failed boot (and how to work around it)

When a system build hangs at the logo, the boot **does not reach bringing up
`adbd`** (the second-stage init dies before). That is why `adb devices` sees
nothing while the tablet is hung at the logo: **it is not that it is not
connected, it is that that boot does not expose ADB.** The previous agent
probably waited for ADB from the hung system and concluded the tablet was not
connected.

The key: the **already-installed Android 10 recovery (V21)** DOES have ADB, and
`/proc/last_kmsg` keeps the kernel log of the PREVIOUS boot (ramoops persists
across the reset). So:

1. With the tablet hung at the logo, the user **forces a reboot to recovery**:
   hold **Vol+ + Home + Power**.
2. In recovery: **Advanced -> Enable ADB** and connect USB.
3. Now `adb` sees it in `recovery` state and `/proc/last_kmsg` contains the log of
   the system boot that just failed.

`get-state` returns `recovery` (not `device`), with a root shell
(`uid=0 ... context=u:r:su:s0`). That is normal and enough for reading.

## 4. Exact capture sequence

```bash
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'
ADB=sm-t280-phase1/tools/platform-tools/adb.exe

"$ADB" devices -l          # must list ...  recovery  model:SM_T280 ...
"$ADB" get-state           # -> recovery
"$ADB" shell id            # -> uid=0(root) ... (confirms shell)

# Kernel log of the hung boot (the main source):
"$ADB" shell 'cat /proc/last_kmsg' > results/phase-5/<vNN>-...-recovery/last_kmsg.txt

# pstore as backup (sometimes empty):
"$ADB" shell 'cat /sys/fs/pstore/console-ramoops*' > .../pstore.txt

# If a boot does bring up adbd in system (rare until it boots):
"$ADB" logcat -d > .../logcat.txt
```

Details:
- `/proc/last_kmsg` = kernel log of the **previous boot** (the one that failed).
  It is the main source when the system hangs.
- The file comes out with interleaved/duplicated lines (ramoops is a multi-CPU
  circular buffer); to analyze it, filter with `grep -a` and `awk '!seen[$0]++'`
  to deduplicate.
- The script `sm-t280-phase5/scripts/capture-first-boot.sh` automates this when
  there IS ADB in system (waits for adbd, captures logcat/dmesg/last_kmsg/pstore
  and classifies the stage).

## 4bis. Read full tombstones by mounting /data (better than last_kmsg)

The `last_kmsg` (ramoops ~1MB, size fixed by the bootloader via `sec_log=...@...`)
is a circular buffer: when the boot enters a **crash loop**, the tombstones
**flood it and push out the start of the boot**, so the root cause is lost.
Enlarging it is not viable (the bootloader fixes it, and it ignores the boot.img
cmdline).

When `/data` mounts and its structure exists, `tombstoned` writes the FULL
crashes in `/data/tombstones/`. From recovery you can mount `/data` and read them
(much better than the overlapped last_kmsg):

```bash
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'
ADB=sm-t280-phase1/tools/platform-tools/adb.exe
"$ADB" shell 'mount -t ext4 /dev/block/platform/sdio_emmc/by-name/userdata /data'
"$ADB" shell 'ls -l /data/tombstones/'
"$ADB" shell 'cat /data/tombstones/tombstone_00'   # full crash backtrace
```

Note: if `/data` is empty (only `lost+found`), the boot did NOT create its
structure (failure in post-fs-data) and there will be no tombstones -- that fact
is itself a diagnosis. `userdata` = `mmcblk0p27` (as of 2026-09-18).

## 5. Checklist if "the tablet does not appear"

1. Are you using `sm-t280-phase1\tools\platform-tools\adb.exe` (not another adb)?
2. `export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'` before commands with `/...`
   paths?
3. Is the tablet in **recovery with Enable ADB**, not hung at the system logo? The
   failed system gives no ADB.
4. `adb kill-server` + retry if there is a foreign adb server.
5. Samsung USB driver installed (see `sm-t280-phase4` TOOLS-STATUS).
6. `adb devices -l` must show `recovery` state and `model:SM_T280`.
