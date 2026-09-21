# Phase 5 -- V15 after formatting /data: RW OK; falls in the HIDL/installd layer

Date: 2026-09-18. Source: `results/fase-5/v15b-postformat-recovery/last_kmsg.txt`.

## Advance

- **`/data` mounts RW** (0 "Read-only file system" errors). The ext4 format of
  `mmcblk0p27` resolved the RO mount.

## Current blocker

- **`installd` aborts repeatedly** (`exited with status 1`, "installd exited 4
  times before boot completed"). installd creates the `/data` structure on the
  first boot; when it fails, `/data/misc`, `/data/dalvik-cache`, etc. do not exist.
- Cascade: `keystore` aborts (`chdir /data/misc/keystore: No such file`),
  `zygote` aborts (`Error creating cache dir /data/dalvik-cache/arm`), loop.
- Chains with the **`hwservicemanager` SIGSEGV** (seen in V14/V15): if the HIDL
  service manager (`/dev/hwbinder`) falls, installd and the services do not
  register.

## Diagnostic limitation

The `last_kmsg` (ramoops, ~169 KB) fills with the tombstones of the installd loop
and **pushes out the start of the boot**: it no longer contains the
`hwservicemanager`/`servicemanager` crash or `mount_all`. To see the service
manager's root cause we would need more log buffer or to reduce the crash spam
(a diagnostic build that stops after the first failure, or `pstore`/`logcat` if
adbd came up).

## Linchpin hypothesis

The `hwservicemanager` SIGSEGV is probably the root cause of the whole cascade
(installd/keystore/zygote). Two possibilities:

1. SG data mis-delivered by the binder (subtle bug in the `BINDER_TYPE_PTR` case /
   parent fixup of V14) -> corrupt parcel -> null deref on parse.
2. Cause external to the binder: absent/malformed VINTF manifest, or a
   /vendor/HAL dependency.

## Next (options)

- Isolate the `hwservicemanager` SIGSEGV: a diagnostic build that captures its
  full tombstone (enlarge the log buffer / stop the installd loop) and/or review
  in detail the PTR case of `binder_transaction` against the upstream pattern.
- Alternative: continue via installd directly (why status 1).

Accumulated progression (all hardware-verified): bootloop -> second-stage (V12)
-> binder multi-device (V13) -> binder SG (V14) -> /data RW (V15+format) -> HIDL/
installd layer (current). Ahead, also: Mali-400 graphics HAL.
