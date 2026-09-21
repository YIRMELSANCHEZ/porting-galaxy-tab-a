# Phase 5 -- V10 diagnosis (failed): no /proc/device-tree at runtime

Date: 2026-09-17. Source: `results/fase-5/v10-bootloop-recovery/last_kmsg.txt` +
ADB inspection of the device in recovery.

## Result

V10 (fstab in the DTB) did **not** fix the loop. `last_kmsg`:

```
init: init first stage started!
init: [libfs_mgr]ReadFstabFromDt(): failed to read fstab from dt
init: [libfs_mgr]ReadDefaultFstab(): failed to find device default fstab
init: Failed to fstab for first stage mount
init: execv("/system/bin/init") failed: No such file or directory
init: #00 pc 000a4ab8  /init (match+19056)
init: Reboot ending, jumping to kernel
```

`ReadFstabFromDt` keeps failing even though `dt.img` contains the `android,fstab`
node (verified with `strings`). And `execv("/system/bin/init")` fails with
`No such file or directory` (confirms `/system` is not mounted).

## Cause (decisive, verified by ADB)

On the device (in recovery): **`/proc/device-tree/` does NOT exist.**

```
$ adb shell ls /proc/device-tree/
No such file or directory
```

This Spreadtrum kernel/bootloader **does not expose the device tree at runtime**
(the `dt.img` is used for board selection at early boot, but the kernel does not
publish `/proc/device-tree`). Therefore `ReadFstabFromDt()` **always** fails and
the "fstab in the DTB" path (V10) is unviable at the root. There is also no
`Hardware` field in `/proc/cpuinfo`.

## State of Android 10's two first-stage fstab mechanisms

- `ReadFstabFromDt()` -> **dead**: no `/proc/device-tree`.
- `ReadDefaultFstab()` -> `GetFstabPath()` -> **dead**: needs `ro.hardware`
  (from `androidboot.hardware`), which the bootloader does not pass (it ignores
  the boot.img cmdline).

## Fix -> V11 (fs_mgr patch)

Since the ramdisk (V9) already has `/fstab.sc8830`, the `/system` mountpoint and
`init.rc`, the only missing piece is for first-stage to **find** the fstab.
Patch `system/core/fs_mgr/fs_mgr_fstab.cpp` (`GetFstabPath()`) to use
`/fstab.sc8830` as a fallback when there is no `ro.hardware`. Detail in
`results/fase-5/PHASE5-V11-FSTAB-FALLBACK.md`.

Warning: the cmdline also carries (or not) `androidboot.selinux=permissive`; since
the bootloader ignores it, **SELinux could stay enforcing** and be the next
blocker after mounting `/system`. It will be treated as the next variable if it
appears.
