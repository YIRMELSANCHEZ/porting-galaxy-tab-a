# Phase 5 -- CONSOLIDATION (2026-09-18): graphics solved, image on screen

Status: **MILESTONE reached** -- LineageOS 17.1 / Android 10 on the SM-T280
(`gtexswifi`) boots to showing the **boot animation on the physical screen**
(confirmed by the user). The whole graphics chain works end to end. The Java
framework (zygote/system_server) boots but does not yet auto-start or reach the
launcher -> **phase 6**.

Current candidate: **V34**
`sm-t280-phase5/packages/SM-T280-android10-fbpan-PHASE5-v34-DO-NOT-FLASH.tar.md5`
- package_sha256: `29fed506e552ad1f03ce69773ec95cf1a4ee8b4b947f94d5a409f958cec69882`
- boot_sha256:    `8e11eb52af6151e27b5c9c48fec83809a270b4095ede8656a2c0ed219f99832c` (FDA kernel, since V31)
- legacy_system_sha256: `187bfa718d7ae423fdbe15d7b23e4c4ca27cd74b5691e07918360e4c6d5ad411`
- Verified: `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`, sha256 == manifest.

## Bring-up chain (what each version solved)

| V | Area | Fix (script apply-vNN.py) |
|---|------|---------------------------|
| V5-V9 | boot/ramdisk | legacy sparse (hdr 32/16); ramdisk rootfs + real init binary |
| V10-V12 | first-stage | no /proc/device-tree; /system entry hardcoded in first_stage_mount |
| V13-V15 | binder kernel | multi-device (binder/hwbinder/vndbinder) + scatter-gather (PTR) + /data |
| V16-V18 | /data / init | post-fs-data; **ro.hardware=sc8830** (unblocked /data + HAL resolution) |
| V19 | bionic | pthread_t shim (old blobs vs strict bionic) |
| V20/V25 | graphics HIDL | services + **-impl** of composer@2.1/allocator@2.0 (passthrough) |
| V22-V24 | logd | logcat recovered (ambient caps nonexistent in kernel 3.10) |
| V26/V32 | libui | legacy gralloc usage bits (0x2000000 bit25, 0x400 bit10) |
| V27 | composer | HwcLoader forced to **HWC2OnFbAdapter** (SPRD HWC overlay broken) |
| V28 | fb adapter | panel dimensions from `/dev/graphics/fb0` (fb HAL reported them as 0) |
| V29 | gralloc | HW_FB buffers via **ION** (native page-flip exhausts the 3 slots) |
| **V31** | **kernel binder** | **BINDER_TYPE_FDA** -- pass native_handles (fd) over HIDL. *Root cause of all graphics.* |
| V34 | framebuffer | **FBIOPAN_DISPLAY** after the memcpy -> the panel latches each frame |

**Discarded:** V17 (dynamic init wrong), V30 (diagnostic), V33 (revert V29 -> real -ENOMEM).

## Key findings (so as not to repeat)

1. **The Spreadtrum bootloader ignores the boot.img cmdline** -> `ro.hardware` is
   forced in `init.cpp`; there is no `/proc/device-tree`.
2. **The SPRD gralloc/HWC/ION are SOURCE**, not blobs: `hardware/sprd/{gralloc,hwcomposer,libion_sprd}`.
   The `gralloc.sc8830` module is compiled from **`hardware/sprd/gralloc/scx30g_v2/`**
   (NOT `sc8830/`; both define the module and scx30g_v2 wins). Patch scx30g_v2.
3. **Kernel 3.10 without ambient capabilities** -> logd (V22-24) and HALs suffer.
4. **BINDER_TYPE_FDA was missing** in the binder backport -> no native_handle
   crossed HIDL -> the whole graphics chain died in the buffer reply. **The most
   important fix.**
5. Environment: WSL opens as **root** by default after reboots -> the build MUST
   run as `lineage` (`wsl.exe -u lineage`). Avoid inline variables in `wsl.exe -lc`.

## Uncommitted tree (reproducible with the apply-vNN; git not initialized)

- **Kernel** (`kernel/samsung/gtexswifi`, git repo): `drivers/staging/android/binder.c`
  (V13/14/15 multibinder+SG + V31 FDA), `.../uapi/binder.h` (SG+FDA),
  `arch/arm/boot/dts/sprd-scx35_gtexswifi_rev05.dts` (V10, inert).
- **Android** (no per-project .git): `system/core/init/{init.cpp,first_stage_mount.cpp}`,
  `system/core/fs_mgr/fs_mgr_fstab.cpp`, `system/core/rootdir/init.rc`,
  `system/core/logd/{main.cpp,logd.rc}`, `bionic/libc/bionic/pthread_internal.cpp`,
  `hardware/sprd/gralloc/scx30g_v2/{alloc_device.cpp,framebuffer_device.cpp}`,
  `hardware/interfaces/graphics/composer/2.1/utils/{passthrough/.../HwcLoader.h,hwc2onfbadapter/HWC2OnFbAdapter.cpp}`,
  `device/samsung/gtexswifi/{device.mk,BoardConfig.mk,mkbootimg.mk,rootdir/fstab.sc8830}`.
- All regenerable by running the `sm-t280-phase5/scripts/apply-vNN-*.py` in order.

## -> PHASE 6 (framework): see `PHASE6-START.md`

Blockers diagnosed and validated live (`v34-system-live/DIAGNOSIS.md`):
1. **zygote does not auto-start**: `class_start main` does not fire because
   `ro.crypto.state` is empty (triggers init.rc:638/770). Validated: `ctl.start
   zygote` by hand -> system_server rises to 32 services. Proposed fix (V35): force
   `ro.crypto.state=unencrypted` after post-fs-data.
2. **PackageManagerService** stalls the main thread (Watchdog WAITED_HALF).
3. **SurfaceFlinger restarts** when system_server connects.
4. **audioserver** SIGSEGV in a loop (audio HAL).
