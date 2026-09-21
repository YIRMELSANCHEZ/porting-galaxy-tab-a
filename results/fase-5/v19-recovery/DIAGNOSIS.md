# Phase 5 -- V19: pthread_t resolved; per-HAL frontier (Mali composer)

Date: 2026-09-18. Source: `results/fase-5/v19-recovery/last_kmsg.txt` + /data.

## Advance

- The abort `invalid pthread_t ... passed to pthread_getschedparam` **disappears**
  (0 occurrences). The bionic shim (V19) worked. `surfaceflinger` advances further.

## New blocker: Mali composer/gralloc HAL + keymaster

- `surfaceflinger` keeps aborting (signal 6), now with
  `Failed HIDL return status not checked: Status(EX_TRANSACTION_FAILED)`: the
  HIDL call to the `android.hardware.graphics.composer@2.1::IComposer/default` HAL
  (lazy HAL, started via `ctl.interface_start`) fails -> the Mali composer service
  does not come up / crashes.
- `keymaster`: `Check failed: kmDevices[TRUSTED_ENVIRONMENT] no viable keymaster
  device found` -- the keymaster HAL is not there either.
- surfaceflinger backtraces pass through `libvintf`/`libhidlbase` (looking for the
  HAL in the manifest and transacting).

It is the **per-HAL frontier** of the proprietary blobs (Mali graphics, keymaster,
audio): each Android 5-7 era one may need its own shim/adapter
(gralloc0->mapper2, hwc1->hwc2on1adapter, etc.).

## Visibility limitation

`/data/tombstones/` is still **empty** (tombstoned does not get to write crashes
this early), and the `last_kmsg` (ramoops) overlaps. Per-HAL diagnosis is blind
except what shows in `last_kmsg`.

## State / assessment

Progression (HW-verified): bootloop -> Android 10 second-stage -> binder
(multi-device+SG) -> /data + all the plumbing (V18) -> graphics HAL layer: pthread_t
resolved (V19) -> **Mali composer/gralloc + keymaster (per-HAL)**.

The next work is a per-HAL bring-up of Android-5 blobs on Android 10 (the most
uncertain front), with limited visibility. Candidates: gralloc/hwcomposer
adapters (hwc2on1adapter, gralloc mapper), and isolating why the composer@2.1
service does not come up. It is a long effort with an unguaranteed result (the
Android 5 Mali-400 may not compose on Android 10).
