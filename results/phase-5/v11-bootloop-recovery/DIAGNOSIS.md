# Phase 5 -- V11 diagnosis (failed) + first_stage_mount filter

Date: 2026-09-17. Source: `results/phase-5/v11-bootloop-recovery/last_kmsg.txt`.

## Result

V11 (fallback in `GetFstabPath`) did **not** fix the loop. Same failure:
`ReadDefaultFstab(): failed to find device default fstab` -> `First stage mount
skipped` -> `execv("/system/bin/init") failed`.

Confirmed positive: `SELinux: Starting in permissive mode` (the SELinux path is
fine).

## Findings

1. `ForceNormalBoot()` reads `androidboot.force_normal_boot=1` from the cmdline;
   it is not there, so **there is no SwitchRoot** (ruled out as a cause). `/` is
   the ramdisk.
2. Despite the fallback, `GetFstabPath()` still returns empty (the `access(
   "/fstab.sc8830")` does not resolve in the first-stage environment for a not-
   fully-determined reason). The file-based path is fragile here.
3. **Decisive filter in `ReadFirstStageFstab()`** (`first_stage_mount.cpp:151`):
   after `ReadDefaultFstab`, it **discards every entry without the
   `first_stage_mount` flag**. The `/system` entry of `fstab.sc8830` does not have
   it, so even if it were read, it would be filtered out and the fstab empty
   anyway.

Conclusion: the three paths (DT, file+hardware, file+flag) are fragile or dead on
this device. `first_stage_mount` is a valid fstab flag (`CheckFlag`), and there
is an in-tree pattern `BuildGsiSystemFstabEntry()` that builds a `FstabEntry` by
hand with `first_stage_mount=true`.

## Fix -> V12

Inject the first-stage `/system` entry **by hand in `ReadFirstStageFstab()`**
when the fstab comes out empty, following the GSI pattern:

```
FstabEntry system = {.blk_device = "/dev/block/platform/sdio_emmc/by-name/SYSTEM",
                     .mount_point = "/system", .fs_type = "ext4",
                     .flags = MS_RDONLY, .fs_options = "errors=panic"};
system.fs_mgr_flags.wait = true;
system.fs_mgr_flags.first_stage_mount = true;
```

Removes all dependency on DT, `ro.hardware`, file and fstab flags. Detail in
`results/phase-5/PHASE5-V12-HARDCODED-FSTAB.md`.
