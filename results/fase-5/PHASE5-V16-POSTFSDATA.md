# Phase 5 -- V16 (diagnostic): unblock post-fs-data

Date: 2026-09-18. Status: in offline build/validation; `DO-NOT-FLASH`.

## Reason (from v15c + offline reading of init.rc)

After formatting /data (RW), the boot creates NO `/data` structure (stays empty:
only `lost+found`), and keystore/installd/zygote crash in a loop. Reading
`system/core/rootdir/init.rc` `on post-fs-data` shows, BEFORE the `mkdir /data/*`
(line 466):

```
start vold
exec - system system -- /system/bin/vdc checkpoint prepareCheckpoint   # blocking
...
installkey /data                                                       # FBE
```

The `exec ... vdc checkpoint prepareCheckpoint` is **synchronous and depends on
vold** (which in turn depends on binder/keystore, broken). If it blocks,
post-fs-data does not reach the `mkdir` -> /data without structure -> crash
cascade. It is userdata checkpointing (A/B feature) that this device does not
need.

## Change

`system/core/rootdir/init.rc` (applied with
`sm-t280-phase5/scripts/apply-v16-postfsdata.py`, idempotent): comments out
`exec ... vdc checkpoint prepareCheckpoint` and `installkey /data`
(checkpoint/FBE machinery that blocks; /data goes unencrypted since V15).

`init.rc` goes in the boot ramdisk (ROOT_OUT/root/init.rc); there is NO duplicate
in system (`/system/etc/init/hw/init.rc` does not exist). Only boot is recompiled;
kernel and system.img unchanged.

## Objective

Twofold: (1) unblock post-fs-data so it creates the `/data` structure (attacking
the cause) and (2) restore visibility -- if /data structures,
`/data/tombstones` exists and the crashes are written to disk (readable by
mounting /data from recovery), instead of only in the overlapped `last_kmsg`.

## Offline validation

- Build: `rebuild-bootimage.sh`. Log `results/fase-5/v16-rebuild-bootimage.log`.
- Ramdisk: `verify-boot-ramdisk.sh` + confirm `# V16 diag` in the ramdisk init.rc.
- Packaging: `prepare-v16-package.sh`.

## Artifact

- Package: `sm-t280-phase5/packages/SM-T280-android10-postfsdata-PHASE5-v16-DO-NOT-FLASH.tar.md5`
- package_sha256: `e97f4d3243d2aa11a067a989bb0bedcd4899876477033bb33a2562923bf5b26f`
- boot_sha256: `f1fe2be58123c8cb89f3f32f029b0b2bcf8039890bc16fc57170e7e906494771`
- Ramdisk carries `# V16 diag` (checkpoint disabled); `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`.

## Expected interpretation

- If post-fs-data advances: `/data/misc`, `/data/dalvik-cache`,
  `/data/tombstones`, etc. are created; keystore/installd stop crashing over
  missing dirs; and we will be able to read tombstones on disk (e.g. the
  hwservicemanager one).
- If it still does not create /data: the blocker is in another post-fs-data step
  (fsverity_init, apexd) or in vold itself; isolate with the now-readable /data.
