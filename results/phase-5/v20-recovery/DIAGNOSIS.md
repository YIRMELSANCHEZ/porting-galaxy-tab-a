# Phase 5 -- V20: composer@2.1 starts but exits (HWC1); V21 = adb in system

Date: 2026-09-18. Source: `results/phase-5/v20-recovery/last_kmsg.txt` + build.

## Advance

- With the graphics HIDL services added (V20), `surfaceflinger` **no longer
  aborts** with `EX_TRANSACTION_FAILED`. The composer service `vendor.hwcomposer-2-1`
  (`android.hardware.graphics.composer@2.1-service`) **starts**.

## Blocker

- The composer **exits with status 1** (no signal -> no tombstone) and restarts in
  a loop. surfaceflinger waits for a composer that never registers.
- Offline: `hwcomposer.sc8830.so` is **HWC1** (symbols `hwc_display_contents_1`,
  `hwc_procs`, `SprdHWComposer`, `registerProcs`, `commitDisplays`). There is no
  `composer@2.1-impl.so` (the default service wraps HWC1 with hwc2on1adapter).
  Something in that load/open of HWC1 fails -> status 1.

## Visibility problem -> V21

The composer error (status 1, no signal) is only in **logcat**, not in
`last_kmsg`. And in system there is no UI to enable ADB. system ALREADY carries
`ro.adb.secure=0` and `persist.sys.usb.config=mtp,adb`, but it is **missing the
FunctionFS compat props** (`ro.adb.nonblocking_ffs=false`, `sys.usb.ffs.aio_compat=
true`) that in phase 4 were applied only to the recovery ramdisk; without them adbd
does not enumerate on the 3.10 kernel.

V21 (`apply-v21-adb-ffs.py`): adds those props to `device.mk`
PRODUCT_PROPERTY_OVERRIDES -> adbd should come up in the system boot even if it
stays on the logo. With adb: `adb logcat` gives the exact composer error to
unblock graphics without going blind.

## After V21 (plan)

1. Flash V21, boot to system (leave it on the logo), **try `adb` directly**
   (without recovery).
2. If adbd responds: `adb logcat -b all -d > .../logcat.txt` and look for the
   composer error (`SprdHWComposer`, `hwc`, `open`, `HWC2On1Adapter`, gralloc).
3. With the error, decide the HWC1 fix (explicit hwc2on1adapter, display init, or
   a specific Spreadtrum composer service).
