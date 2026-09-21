# Phase 5 -- V14: binder SG at command level OK; remaining blockers

Date: 2026-09-18. Source: `results/fase-5/v14-hang-recovery/last_kmsg.txt`.

## Success

- `unknown command 0x40286211` (BC_TRANSACTION_SG): **0 occurrences**.
- `registerAsService=-2147483648`: **0 occurrences**.
- No kernel panic (the "BUG:" matches were noise from userspace tombstones, not
  kernel failures). The SG patch did not destabilize the kernel.

That is, scatter-gather is processed. Real progress.

## Remaining blockers

1. **`/data` not mounted** (high impact, separate). Cascade:
   `Error creating cache dir /data/dalvik-cache/arm`, `keystore chdir
   /data/misc/keystore: No such file`, uncrypt, etc. First-stage only mounts
   `/system` (V12 hardcoded entry); `/data` (and `/cache`) still need mounting in
   second-stage (`mount_all /fstab.sc8830`) or adding.
2. **`binder_transaction_buffer_release`: `bad object type 70742a85`**
   (`70742a85` = `BINDER_TYPE_PTR`). The `BINDER_TYPE_PTR` case is missing in
   `binder_transaction_buffer_release()` (omitted in V14). Not fatal, but it
   mismatches the release traversal; it must be added.
3. **SIGSEGV in `hwservicemanager`** (`getInstances`/`listManifestByInterface`,
   null deref) and **`audioserver`** (AudioFlinger ctor). Possible mis-delivered
   SG data (subtle bug in the copy/fixup of the PTR case) or side effect of 1/2.
   To confirm after fixing 1 and 2 (hwservicemanager does not depend on /data, so
   if it keeps crashing it points to the SG).

## Next step (V15)

- Add `BINDER_TYPE_PTR` case in `binder_transaction_buffer_release` (correct and
  silences the "bad object type").
- Ensure `/data` (+`/cache`) mount in second-stage.
- Re-evaluate the hwservicemanager SIGSEGV: if it persists, review the PTR case of
  `binder_transaction` (SG copy / parent fixup) in more detail.

## Scope note (honest)

Progression: bootloop -> second-stage (V12) -> binder multi-device (V13) -> binder SG
at command level (V14). Remaining: /data, SG corrections, and ahead the Mali-400
graphics HAL (for SurfaceFlinger/boot animation) -- which is a big challenge of
proprietary blobs (Android 5-era) on Android 10. It is a long, multi-subsystem
bring-up.
