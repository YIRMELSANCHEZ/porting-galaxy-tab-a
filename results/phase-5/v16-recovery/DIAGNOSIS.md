# Phase 5 -- V16: /data root cause found (ro.hardware="unknown")

Date: 2026-09-18. Source: `results/phase-5/v16-recovery/last_kmsg.txt` +
offline inspection of init.rc/init.cpp.

## What V16 showed

- With the `checkpoint` disabled (V16), the post-fs-data `mkdir /data/*` **do
  appear** in the log -- the checkpoint blocked less than thought.
- But they **still fail with "Read-only file system"**, and `/data` (mmcblk0p27)
  mounted from recovery is still **empty** (only `lost+found`).
- Verified: `/data` **mounts RW without a problem** from recovery with the EXACT
  fstab options (incl. `journal_async_commit`). The fs is valid.

Intermediate conclusion: `/data` **is not being mounted during boot**; the
`mkdir` fall on the empty mountpoint of the **read-only rootfs** (ramdisk).

## ROOT CAUSE: ro.hardware = "unknown"

`mount_all /fstab.sc8830` lives in `device/.../rootdir/init.sc8830.rc`, which
`init.rc:9` imports with:

```
import /init.${ro.hardware}.rc
```

But `system/core/init/init.cpp` (props table) derives `ro.hardware` from
`ro.boot.hardware` with **default "unknown"**:

```
{ "ro.boot.hardware", "ro.hardware", "unknown", },
```

Since the **bootloader does not pass `androidboot.hardware`** (already seen in
first-stage; there is also no Hardware field in /proc/cpuinfo), `ro.hardware =
"unknown"`. Therefore `import /init.unknown.rc` -> does not exist -> **`init.sc8830.rc`
is NEVER imported** -> `mount_all` never runs -> `/data`/`/cache` unmounted -> mkdir
RO -> cascade (keystore/installd/zygote).

Also `${ro.hardware}` is used to load **HALs** (`<name>.${ro.hardware}.so`) and
more configs; "unknown" also contributes to the HIDL/graphics failures.

It is the SAME root cause as first-stage (bootloader ignores the cmdline), now in
second-stage.

## Fix -> V17

One-line patch in `init.cpp`: default `ro.hardware` to **"sc8830"** instead of
"unknown". Fixes the import of init.sc8830.rc (-> mount_all -> /data) and the
resolution of `${ro.hardware}` across the system (HALs included). Detail in
`results/phase-5/PHASE5-V17-RO-HARDWARE.md`.
