# Phase 5 -- V15c: /data RW but empty; diagnostic visibility wall

Date: 2026-09-18. Source: `/proc/last_kmsg` + `/data` mounted from recovery.

## Facts

- `/data` (mmcblk0p27) mounted from recovery: **RW correct**, but **empty
  (only `lost+found`)**. The boot does NOT create any `/data` structure
  (`/data/misc`, `/data/dalvik-cache`, `/data/tombstones`... do not exist).
- Consequently: `keystore` aborts (`chdir /data/misc/keystore`), `installd`
  aborts, `zygote` aborts (dalvik-cache), in a **loop**.
- Since `/data/tombstones` does not exist, **there are no tombstones on disk** to
  read the full `hwservicemanager` crash.

## Cause (post-fs-data level)

With `/data` now RW, the fact that the structure is not created means init's
`post-fs-data` flow does not complete: probably the storage/encryption step
(`vdc --wait cryptfs init_user0` / vold) blocks or fails before the
`mkdir /data/...`. It is Android 10's storage/FBE layer.

## The real wall: VISIBILITY

The kernel buffer (`ramoops`/`last_kmsg`, ~400-500 KB) **fills with the tombstones
of the crash loop** and pushes out the start of the boot. In all captures (v14,
v15, v15b, v15c) only the tail of the loop is visible, not the root cause
(vold/cryptfs/servicemanager/mount_all). Without more buffer or breaking the loop,
diagnosis is blind. There is also no:
- ADB in system (adbd does not come up; the loop cuts before),
- tombstones on disk (/data/tombstones is not created).

## Pending interdependent blockers

1. **Storage/FBE**: post-fs-data does not complete -> /data without structure.
2. **HIDL**: `hwservicemanager`/`keystore`/`installd` crash in a loop (root cause
   hidden by the visibility wall; possible VINTF manifest, or effect of 1).
3. **Graphics** (ahead): Mali-400 HAL on Android 10.

## Recommendation

To advance efficiently, we must **restore visibility first**:
- Enlarge `ramoops`/`CONFIG_LOG_BUF_SHIFT` so the whole boot fits, or
- Break the crash loop (crashing services to `oneshot`/`disabled`
  temporarily) so `last_kmsg` keeps the first failure.

Without that, each iteration is blind. It is a natural point to consolidate: the
state (V1->V15 + capture method + diagnoses) remains reproducible and
documented. Continuing implies a long storage/HIDL/graphics bring-up with
degraded visibility.

## Accumulated progression (hardware-verified)

bootloop -> second-stage (V12) -> binder multi-device (V13) -> binder SG (V14) ->
/data RW (V15+format) -> wall in the storage/HIDL layer + visibility (current).
