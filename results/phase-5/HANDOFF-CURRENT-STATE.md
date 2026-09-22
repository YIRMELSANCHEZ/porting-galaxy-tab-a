# Handoff -- current project state

Date: 2026-09-18  
Project: LineageOS 17.1 / Android 10 for Samsung Galaxy Tab A 7.0 2016 SM-T280 (`gtexswifi`).

## *** PHASE 5 CONSOLIDATED (2026-09-18) -- animation VISIBLE on screen

Read first: **`PHASE5-COMPLETE.md`** (summary + V5-V34 chain + findings) and then
**`PHASE6-START.md`** (framework bring-up). Flashed and verified candidate:
**V34** -- `sm-t280-phase5/packages/SM-T280-android10-fbpan-PHASE5-v34-DO-NOT-FLASH.tar.md5`
(package_sha256 `29fed506e552ad1f03ce69773ec95cf1a4ee8b4b947f94d5a409f958cec69882`,
boot `8e11eb52...` FDA kernel). Tree consistent with V8-V34 (verified markers);
regenerable with `scripts/apply-vNN-*.py` (git not initialized).

**Graphics: SOLVED** -- the key was the **BINDER_TYPE_FDA backport** to the kernel (V31);
the rest: SPRD gralloc/HWC/fb from source (`hardware/sprd/gralloc/scx30g_v2`), HIDL
-impl, usage bits, FB adapter, FBIOPAN in fb_post.

**PHASE 6 IN PROGRESS -- plan: `results/phase-6/PHASE6-PLAN.md`.**
- **6.1 SOLVED (V35):** `setprop ro.crypto.state unencrypted` + `trigger nonencrypted`
  at the end of `on post-fs-data` -> the framework auto-starts (zygote/system_server on their own).
- **ROOT CAUSE of the hang (V35 diag): hwservicemanager CRASHES (SIGSEGV)** with a null-deref
  in `libvintf HalManifest::getInstances` when querying the VINTF manifest -- because **the
  device had NO VINTF manifest**. Its onrestart restarts system_server in cascade ->
  broken HIDL -> system_server hangs (AMS->memtrack getService), audioserver/keystore
  crash. It is the common root of the 4 symptoms. Detail: `phase-6/v35-system-live/DIAGNOSIS.md`.

Current candidate: **V36** (device VINTF manifest).
`sm-t280-phase5/packages/SM-T280-android10-vintf-manifest-PHASE6-v36-DO-NOT-FLASH.tar.md5`
- package_sha256: `531ddfc4720f0abed6cf3f62a9236476a50c3d8ff4007630529565d706c86d5b`
- boot_sha256: `27c04393efb4ad77c6cc2df3fe5b3ac25cf1f1513d6f8f8502d207187b5fb5a4` (= V35, crypto ramdisk + FDA kernel)
- legacy_system_sha256: `1cc7e89aab389bafbcfcc103ed44240e35dae950a046913081efaf30f875ca60` - size 1014825055
- `apply-v36-vintf-manifest.py`: creates `device/samsung/gtexswifi/manifest.xml` (graphics
  allocator/composer/mapper, configstore, health, memtrack) + `DEVICE_MANIFEST_FILE` ->
  `/vendor/etc/vintf/manifest.xml`. Non-null manifest -> getInstances does not crash.
- After flashing: verify hwservicemanager does NOT crash (dmesg without `signal 11`) and that
  system_server passes AMS/memtrack. Re-diagnose whatever remains (audioserver, PMS, SF).

---
## (historical) PREVIOUS CURRENT STATE: SF composes (V25); SPRD HWC broken; V27 = FB adapter

**V25 (MILESTONE):** SurfaceFlinger composes, registers its binder, powers the display
(`power mode 2`) and launches bootanim. HIDL composer/gralloc/mapper stack + SF operational.

**V26 (flashed, partial):** the flag `ADDNL_GRALLOC_10_USAGE_BITS += (1<<25)` fixed
the CLIENT usage-bit validator (`libui`). But the real failure was lower down:
```
E GraphicBufferAllocator: Failed to allocate 800x1280 fmt 1 usage 3000000: 5 (NO_RESOURCES)
E SPRDHWComposer: SprdPrimaryPlane::open failed / Init EGL ENV failed
```
usage 0x3000000 = SPRD private bits 24+25. Error 5 = NO_RESOURCES: the **blob
`gralloc.sc8830` alloc() fails** when reserving the HWC overlay buffer (overlay ION
heap unavailable). It is INSIDE the blob -> not patchable.

**V27 (flashed, advances):** `apply-v27-force-fb-adapter.py` forced the FB adapter
(`HwcLoader::loadModule` skips the HWC -> HWC2OnFbAdapter). ALL SPRD HWC errors
disappear; SF sets power mode 2 and launches bootanim. New blocker:
```
E BufferQueueProducer: [FramebufferSurface] allocateBuffers: failed to allocate (0 x 0 ...)
```
`HWC2OnFbAdapter` copies `mFbDevice->width/height/fps` from framebuffer_device_t, and the
gralloc.sc8830 fb HAL leaves them at **0** -> FramebufferSurface 0x0 -> fails. The sprdfb
kernel DOES know 800x1280.

**V28 (flashed, advances):** `apply-v28-fbadapter-dims.py` -- the `HWC2OnFbAdapter` reads
the dimensions from `/dev/graphics/fb0` (kernel) when the fb HAL reports 0. It worked:
SF now allocates at **800x1280**. New blocker: gralloc fails `alloc()`:
`Failed to allocate 800x1280 fmt 1 usage 1a00: 5 (NO_RESOURCES)`. usage 0x1a00 = HW_FB
-> `gralloc_alloc_framebuffer_locked` exhausts the 3 page-flip buffers (SF +
HWC2OnFbAdapter share the fb) -> -ENOMEM.

**GRALLOC IS SOURCE (patchable), real directory = `scx30g_v2`:** the module
`gralloc.sc8830` is compiled from `hardware/sprd/gralloc/**scx30g_v2**/alloc_device.cpp`
(NOT from `sc8830/`; both define the module and scx30g_v2 wins -- confirmed by the build
log). Any gralloc patch goes to scx30g_v2. (Same: the SPRD HWC is source in
`hardware/sprd/hwcomposer/`, and the ION in `hardware/sprd/libion_sprd/`.)

**V29 (flashed, patch active but not enough):** `apply-v29-gralloc-fb-ion.py` in
`scx30g_v2/alloc_device.cpp` -- the ION copy path for HW_FB runs (logs
`V29 alloc` + `V29: HW_FB via ION copy` appear in pid 216=allocator). BUT gralloc
allocates successfully (no AERR) and yet SF (228) reports `Failed to allocate 800x1280
usage 1a00: 5 (NO_RESOURCES)`. And the bootanim buffer (0xf02, -22 EINVAL) does NOT reach
gralloc (no `V29 alloc`) -> fails on the client. Contradiction unresolved by static
analysis (the whole gralloc chain returns 0).

**V30 (diagnostic, RESOLVED the root cause):** the logs proved that ALL graphics
work -- gralloc allocates via ION (ret=0), allocator returns NONE (result=0) -- but
SF receives NO_RESOURCES. `kTransactionError=NO_RESOURCES(5)` in Gralloc2.cpp = the
**binder transaction fails**. dmesg: `binder: got transaction with invalid object
type/size, 66646185` = `BINDER_TYPE_FDA`. The kernel binder does not know how to pass the
buffer's `native_handle` (with fd) between processes.

### => V31 (flashed, MILESTONE): binder wall BROKEN. V32 = current candidate (usage bit)

**V31 (flashed, SUCCESS):** the binder FDA error disappeared (clean dmesg) and
**SurfaceFlinger allocates its FramebufferSurface** (3x usage 0x1a00, result=0). The
native_handle transport over HIDL works. One failure remains: the bootanim buffer
(usage 0xf02) is rejected by libui -- `invalid usage bits 0x400` (bit 10 = HW_2D,
which V26 did not add). -> -22 before reaching gralloc.

**V32 (flashed, graphics MILESTONE):** with the usage bits, bootanim allocates and draws.
`dumpsys SF`: composes the BootAnimation#0 layer and **`gralloc: fb_post fps=14`** -> SF
posts frames to the fb. The ENTIRE graphics pipeline works. Only failure: each post gives
`kernel: ion_invalidate_for_cpu: dmabuf is error ... fffffff7` (-9) -> the ION buffer's
cache sync (V29 hack) fails -> the fb receives stale data -> the uboot logo is shown.

**V33 (flashed, discarded):** revert V29 to native page-flip -> REAL `-ENOMEM` in a
loop (the page-flip exhausts the fb's 3 slots; it does not fit with FramebufferSurface). ->
**V29 (ION alloc) IS necessary.** It also confirmed that V32's "frozen logo" was not the
alloc but the presentation: the **memcpy** branch of `fb_post` (for ION buffers)
copied the frame to the fb but **did not do `FBIOPAN`** -> the DPI panel did not latch ->
the uboot logo remained. Detail: `results/phase-5/v33-system-live/DIAGNOSIS.md`.

**V34 (current candidate):** reapplies V29 (ION alloc) + `apply-v34-fbpost-refresh.py`:
in the memcpy branch of `fb_post`, after the memcpy, `FBIOPAN_DISPLAY` (yoffset=0) to
force the panel latch/refresh. Keeps V31 (FDA) + V32 (usage). Change in
gralloc.sc8830 (system.img); boot = V31 (8e11eb52, unchanged).
Expected success: each fb_post latches -> **visible animation**.
- V34 package (`V34_PACKAGE_PASS`, `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`):
  `sm-t280-phase5/packages/SM-T280-android10-fbpan-PHASE5-v34-DO-NOT-FLASH.tar.md5`
  - package_sha256: `29fed506e552ad1f03ce69773ec95cf1a4ee8b4b947f94d5a409f958cec69882`
  - boot_sha256: `8e11eb52af6151e27b5c9c48fec83809a270b4095ede8656a2c0ed219f99832c` (= V31)
  - legacy_system_sha256: `187bfa718d7ae423fdbe15d7b23e4c4ca27cd74b5691e07918360e4c6d5ad411`
  - size: `1014825046`
- Tree (preserve): gralloc scx30g_v2 (V29 ION + V34 FBIOPAN) + framebuffer_device.cpp
  (V34) + BoardConfig (V26+V32) + binder FDA (V31) + the rest.
- Tree (preserve): gralloc scx30g_v2 (V33 = V29/V30 reverted; stays clean) +
  BoardConfig (V26+V32) + binder FDA (V31) + the rest of V25-V31.
- V32 package (`V32_PACKAGE_PASS`, `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`):
  `sm-t280-phase5/packages/SM-T280-android10-gralloc-usage2-PHASE5-v32-DO-NOT-FLASH.tar.md5`
  - package_sha256: `37c30f21eff264b209c5de813b0958300c4504aad8c337e4ac65fdd7646e95d6`
  - boot_sha256: `8e11eb52af6151e27b5c9c48fec83809a270b4095ede8656a2c0ed219f99832c` (= V31, FDA kernel)
  - legacy_system_sha256: `41e485f3872b579236bc129e5edb78ff5e448b8a4ff17d78f270c433b7fd8a57`
  - size: `1014825055`
- Tree (preserve): BoardConfig.mk (V26+V32) + everything from V25-V31 (binder FDA, gralloc
  scx30g_v2, HWC2OnFbAdapter, HwcLoader, device.mk).

---
### (historical) V31 -- BINDER_TYPE_FDA backport to the kernel

**V31 (candidate):** `apply-v31-binder-fda.py` backports `BINDER_TYPE_FDA` (fd
array) to the kernel 3.10 binder (the previous V13/V14/V15 backport added PTR/SG but not
FDA): type + `struct binder_fd_array_object` (uapi), `binder_object_size`, translation
in `binder_transaction` (finds the PTR parent buffer and translates each fd as
BINDER_TYPE_FD), and a case in the release. **Recompiles the kernel -> boot.img CHANGES**
(first boot change since V20). system also changes (drags V29+V30, inert/droppable).
Detail: `results/phase-5/v30-system-live/DIAGNOSIS.md`.
- V31 package (`V31_PACKAGE_PASS`, `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`):
  `sm-t280-phase5/packages/SM-T280-android10-binder-fda-PHASE5-v31-DO-NOT-FLASH.tar.md5`
  - package_sha256: `72ea4b4eacb72c1878b42fb04eab633f909f1eb2817eb37364f99f0115e375fe`
  - **boot_sha256: `8e11eb52af6151e27b5c9c48fec83809a270b4095ede8656a2c0ed219f99832c` (NEW, FDA kernel)**
  - legacy_system_sha256: `d53eb2f7206b950b17c4d3f8624ed1dd77748c744885499b300d00a6c0fbea0c` (= V30, unchanged system)
  - size: `1014825051`
- Expected success: the buffer reply reaches SF -> composes and presents -> boot animation;
  it also unblocks any HAL passing native_handles.
- Tree (preserve): `.../drivers/staging/android/binder.c` + `.../uapi/binder.h` (V31,
  FDA) + everything from V25-V30 (gralloc scx30g_v2, HWC2OnFbAdapter, HwcLoader, BoardConfig,
  device.mk). The V13/V14/V15 binder (PTR/SG) remains.

**Secondary blockers (do NOT block UI; later):** `mediaserver` linker
`ion_is_legacy`; `audioserver` SIGSEGV in `AudioFlinger::AudioFlinger()` (audio HAL).

---
### History: `logd` fix chain (V22->V24, to recover `logcat`)
- **V22 (flashed, partial):** shim of the `logd` binary (`cap_set_proc` non-fatal in
  `drop_privs`). Advanced but fell on the next step: `setgroups()` ->
  `failed to set AID_READPROC groups` -> status 1 in a loop.
- **Full root cause:** `logd.rc` launches logd with `user logd` (uid 1036) +
  `capabilities SYSLOG AUDIT_CONTROL SETGID` via **ambient caps**, which kernel
  **3.10 does not have** -> logd runs without effective CAP_SETGID -> `cap_set_proc`,
  `setgroups`, `setgid` fail. Validated live: running `/system/bin/logd` **as root**
  passes `drop_privs` without errors.
- **V23 (flashed, partial):** `user root` in `logd.rc`. Passed cap_set_proc and
  setgroups (root has CAP_SETGID) but fell on `setuid(AID_LOGD)` ->
  `failed to set AID_LOGD uid`. Reason: `drop_privs` does `cap_set_proc` which clears
  `CAP_SETUID`; then `setuid(0->1036)` needs that cap. In the normal flow init
  starts logd ALREADY as uid 1036, so `setuid(1036)` is a no-op.
  Detail: `results/phase-5/v23-system-live/DIAGNOSIS.md`.
- **V24 (current candidate):** `apply-v24-logd-privs.py` -- (1) the `.rc` returns to
  `user logd` (init sets uid 1036 + groups); (2) `main.cpp` makes `setgroups`/`setgid`/
  `setuid` of `drop_privs` **non-fatal** (extends the V22 cap_set_proc shim).
  With init's uid 1036: setgroups is skipped (keeps init's groups incl readproc),
  setgid(1036)/setuid(1036) are no-ops -> `drop_privs` completes -> **logcat returns**.
  Change in system.img (logd.rc + binary). boot unchanged.
  - V24 package (`V24_PACKAGE_PASS`, `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`):
    `sm-t280-phase5/packages/SM-T280-android10-logd-privs-PHASE5-v24-DO-NOT-FLASH.tar.md5`
  - package_sha256: `1c7c040ff52e4feba304270f3da75d719dc5fbb2d638e60ad7d2b100e4f9ce03`
  - boot_sha256: `75b50216b1124af9f8d23e159b8ba02b58632ee795b68eb15b3ca9dbcd6d4b18` (= V20/V21/V22/V23)
  - legacy_system_sha256: `cd5fc0da4d18ed0ce560b09db20dbf9514aeed36823260cb6a09821ae26892d1`
  - size: `1014548571`
  - Tree (preserve): `system/core/logd/logd.rc` (V24) + `system/core/logd/main.cpp` (V22+V24).



**Maximum milestone reached (V21, live over ADB):** `zygote` + **`system_server`
alive**, allocator@2.0 and composer@2.1 **running** (no longer looping status 1), 25
services registered. The boot reaches the Java framework; the frozen logo is the
tip of the iceberg. Full diagnosis: `results/phase-5/v21-system-live/DIAGNOSIS.md`.

**Current root blocker:** `SurfaceFlinger` (pid 660) **1 thread asleep in
`binder_thread_read`** -> hung in a synchronous binder call of the display boot
(getService of the composer / display init); it does not register its binder ->
`system_server` does not advance -> freeze on the logo. The exact SF error is **only in
`logcat`**.

**Visibility blocker:** `logd` falls into a status-1 loop -> `logcat` dead. Exact cause
(dmesg): `logd: failed to set CAP_SETGID, CAP_SYSLOG or CAP_AUDIT_CONTROL`; on
kernel 3.10 `cap_set_proc` fails (no ambient caps) -> `drop_privs` returns -1.

**V22 (current candidate):** `logd` shim -- `cap_set_proc` non-fatal in
`drop_privs` (`apply-v22-logd-caps.py`, V19 pthread shim pattern) -> logd lives ->
**logcat returns**, to finally see the SurfaceFlinger error. Change in
system.img (full build). Detail: `results/phase-5/v21-system-live/DIAGNOSIS.md`.

**Environment GOTCHA (after compaction):** WSL opens as **root** by default; nsjail
(soong) fails with `chdir Permission denied` -> `Don't have a product spec`. **The
build MUST run as `lineage`**: `wsl.exe -u lineage bash -lc '...'`.

- V22 package: `sm-t280-phase5/packages/SM-T280-android10-logd-caps-PHASE5-v22-DO-NOT-FLASH.tar.md5`
  (`V22_PACKAGE_PASS`, `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`).
  - package_sha256: `bf42fccd01ddf8bc20a18dbf10035b0318981c84228765b9b648653bf0a10c0e`
  - boot_sha256: `75b50216b1124af9f8d23e159b8ba02b58632ee795b68eb15b3ca9dbcd6d4b18` (unchanged vs V20/V21)
  - legacy_system_sha256: `3255b3527251ebea622c3baaff320aa340da2096b4c456b4005b08780f239e5d`
  - embedded_md5: `ba28d5d928c89afa3f9c5501809a3cec` - size: `1014548570`

**Uncommitted changes in the tree (preserve, do not resync/checkout):** everything from
V11-V21 + `system/core/logd/main.cpp` (V22, `drop_privs` cap_set_proc non-fatal).

## Limits and current authorization

The user authorizes only the physical flashing, done by them, of
`boot.img` (KERNEL) and `system.img` (SYSTEM) via Odin AP. Auto Reboot and
Re-Partition must stay unchecked. Do not use PIT, BL, CP, CSC, modem,
recovery, data wipe, bootloader or partition modifications without new
authorization. The agent does not flash or physically reboot the tablet.

## Environment

- Windows workspace: `C:\Dev\Experiments\porting-galaxy-tab-a`
- Windows ADB: `sm-t280-phase1\tools\platform-tools\adb.exe`
- WSL: Ubuntu-22.04, user `lineage`
- Android tree: `/home/lineage/android/lineage-17.1`
- Windows path inside WSL: `/mnt/c/Dev/Experiments/porting-galaxy-tab-a`
- Avoid complex inline logic in `wsl.exe ... bash -c`; use `.sh` scripts.
- Do not run `repo sync`, `git checkout` or discard changes in the tree.
- **Log capture (ESSENTIAL): see `results/phase-5/LOG-CAPTURE-METHOD.md`.**
  Keys: use the repo's `adb.exe`; `export MSYS_NO_PATHCONV=1
  MSYS2_ARG_CONV_EXCL='*'` before commands with `/...` paths (otherwise Git Bash
  rewrites them and "there is no data"); the hung system gives NO ADB -> force a reboot to
  recovery (Vol+ + Home + Power, Enable ADB) and read `/proc/last_kmsg` (log of the
  failed boot, persists via ramoops).

## Recoverable tablet state

- Confirmed model: SM-T280, `gtexswifi`.
- FRP: OFF; OEM Unlock was enabled by the user.
- The AQJ1 `boot + system` stock rescue was accepted by Odin and Android 5.1.1
  booted fully. This proves cable, Download Mode, Odin and the SYSTEM
  partition are functional.
- Android 10 recovery (Phase 4) remains installed and allows enabling ADB.
- Current state: Android 10 recovery, `Enabled ADB` shown on screen;
  USB connected. The PC did enumerate it as `recovery`, but the ADB
  shell is not responding stably after the last reboot.

## Stock recovery available

- Full validated stock archive:
  `sm-t280-phase4/stock/SAMFW.COM_SM-T280_TPA_T280XXU0AQJ1_fac.zip`
- Stock recovery rescue:
  `sm-t280-phase4/packages/SM-T280-AQJ1-STOCK-RECOVERY-RESTORE-v2.tar.md5`
- Stock rescue limited to boot + system, tested with PASS and a correct boot:
  `sm-t280-phase5/packages/SM-T280-AQJ1-STOCK-BOOT-SYSTEM-ONLY-RESTORE.tar.md5`

## Phase 5 findings

### SYSTEM transfer

V1 (standard sparse), V2 (raw ext4), V3 (reduced raw ext4) and V4 (raw with
DHTB/signature) failed in Odin when writing `system.img`. The AQJ1 stock system
was accepted, ruling out size, cable and partition capacity as causes.

The stock SYSTEM uses legacy Android sparse:

- stock: `file_hdr_sz=32`, `chunk_hdr_sz=16`;
- modern AOSP: `file_hdr_sz=28`, `chunk_hdr_sz=12`.

V5 adapts only those headers and keeps the ext4 payload and the 524288
blocks of 4096 bytes. V5 was accepted by Odin (`PASS`).

V5 artifact:

`sm-t280-phase5/packages/SM-T280-system-android10-legacy-sparse-PHASE5-v5-DO-NOT-FLASH.tar.md5`

### First boot failure

After V5, the 3.10.108 kernel booted but panicked early:

`VFS: Unable to mount root fs on unknown-block(0,0)`.

It was found that `mkbootimg.mk` was building the ramdisk by mistake from
`TARGET_ROOT_OUT`, where `/init` was a symlink to `/system/bin/init`. On this
legacy hardware SYSTEM is not yet mounted at that point.

Fix applied in the Android tree:

`device/samsung/gtexswifi/mkbootimg.mk`

`TARGET_ROOT_OUT` was replaced by `TARGET_RAMDISK_OUT` for the boot ramdisk. The
new ramdisk contains `/init` as an executable binary; the validator
`sm-t280-phase5/scripts/verify-boot-ramdisk.sh` produced
`BOOT_RAMDISK_INIT_BINARY_PASS`.

### Second boot failure

After V6, `last_kmsg` showed that `/init` started correctly, but aborted in
the first-stage mount:

```
init: init first stage started!
init: [libfs_mgr]ReadFstabFromDt(): failed to read fstab from dt
init: [libfs_mgr]ReadDefaultFstab(): failed to find device default fstab
init: Failed to fstab for first stage mount
init: Reboot ending, jumping to kernel
```

The cause is that first-stage init needs to know the hardware before loading
`init.sc8830.rc`, to resolve `/fstab.sc8830`.

V7 fix applied in:

`device/samsung/gtexswifi/BoardConfig.mk`

Added to the cmdline:

`androidboot.hardware=sc8830`

The `bootimage` rebuild finished correctly and recompiled kernel,
ramdisk, DT and boot image.

## V7 diagnosed (blocker resolved) and V8 ready

V7's `last_kmsg` was captured (recovery ADB was stable; root shell OK):
`results/phase-5/v7-bootloop-recovery/last_kmsg.txt`. Full diagnosis:
`results/phase-5/v7-bootloop-recovery/DIAGNOSIS.md`.

V7 is not the same failure as V6: init no longer aborts in first-stage, it **skips**
it (`First stage mount skipped ...`) and, without `/system`, reboots to bootloader -> that
is the loop. Root cause: the V6 fix builds the boot ramdisk from
`TARGET_RAMDISK_OUT` (only `init`), but `fstab.sc8830` is in `TARGET_ROOT_OUT`
(`root/`); first-stage init does not find it.

V7: `sm-t280-phase5/packages/SM-T280-android10-fstab-first-stage-fix-PHASE5-v7-DO-NOT-FLASH.tar.md5`
(SHA-256 `51ba22175d0ce1304fdb3f92567fe9f886c5df02c3a40544488839b9b12856c1`).
Previous logs: `results/phase-5/v6-bootloop-recovery-last_kmsg.txt`,
`results/phase-5/v5-bootloop-recovery/last_kmsg.txt`.

### V8 (flashed, FAILED) and V9 (current candidate)

- **V8** (fstab in ramdisk) was flashed and **stayed in the loop**: same first-stage
  failure. `last_kmsg`: `results/phase-5/v8-bootloop-recovery/last_kmsg.txt`.
  Diagnosis and real root cause: `results/phase-5/v8-bootloop-recovery/DIAGNOSIS.md`.
  Summary: `first_stage_init` does `execv("/system/bin/init")`; since `/system` is not
  mounted, it fails -> FATAL -> reboot. The V6/V8 ramdisk (`TARGET_RAMDISK_OUT`) is
  the minimal system-as-root and **lacks the `/system` mountpoint, `init.rc` and
  `sepolicy`**. The V6 fix discarded the legacy rootfs.

- **V9 (current candidate)**: boot ramdisk from `TARGET_ROOT_OUT` (full legacy
  rootfs) with a real `/init` binary instead of the symlink. Verified:
  `BOOT_RAMDISK_V9_LEGACY_ROOTFS_PASS` (init binary + init.rc + fstab.sc8830 +
  /system mountpoint), `ODIN_SYSTEM_PACKAGE_PASS`,
  `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`.
  - Package: `sm-t280-phase5/packages/SM-T280-android10-legacy-rootfs-PHASE5-v9-DO-NOT-FLASH.tar.md5`
  - package_sha256: `99593976ba5c1597feb15e4a068b526c54db2bb81891b7cd1fbd2324b1d0ab11`
  - Detail: `results/phase-5/PHASE5-V9-LEGACY-ROOTFS.md`.

Uncommitted changes in the Android tree (preserve, do not resync/checkout):
`system/core/init/security.cpp` (mmap_rnd_bits), `device/.../mkbootimg.mk`
(V6->V9: ramdisk from ROOT_OUT + real init binary),
`device/.../BoardConfig.mk` (GCC4.8 + `androidboot.hardware=sc8830`).

### V9 (flashed, FAILED) -- definitive root finding

V9 stayed in the loop and init **crashes** in first-stage. The `last_kmsg` includes the
REAL bootloader cmdline: `console=null ... init=/init ...` **without
`androidboot.hardware=sc8830` or `console=ttyS1`**. That is, **the Spreadtrum
bootloader ignores the boot.img's `BOARD_KERNEL_CMDLINE`**. That is why `ro.hardware`
never reaches init, `GetFstabPath()` does not look for `/fstab.sc8830`, and it does not
matter where the fstab is (V7/V8/V9 fail identically). Also, our `dt.img` has no
`firmware/android/fstab` node. Detail: `results/phase-5/v9-bootloop-recovery/DIAGNOSIS.md`.
The DTB of our `dt.img` DOES load (it has `/chosen`), but the bootloader overwrites
`bootargs`; the body of the DTB is respected.

### V10 (flashed, FAILED) -- finding: there is no /proc/device-tree

It added the `firmware/android/fstab` node to the DTB, but `ReadFstabFromDt` still
failed: **the device does not expose `/proc/device-tree` at runtime** (confirmed by
ADB: `ls /proc/device-tree` -> does not exist). The DT path is unviable at the root. init
crashes at `execv("/system/bin/init") failed: No such file or directory`.
Detail: `results/phase-5/v10-bootloop-recovery/DIAGNOSIS.md`.

### V12 (flashed) -- MILESTONE: mounts /system and boots second-stage

**First-stage is solved.** V12 changed the symptom from a loop (~3 s) to a hang
(~3 min) because `/system` **mounts** and the second-stage init boots Android 10
(SVC_EXEC of art_apex_boot_integrity, healthd, vold, netd, hwservicemanager...).
The hardcoded `/system` entry worked. Evidence:
`results/phase-5/v12-hang-recovery/last_kmsg.txt` and `.../DIAGNOSIS.md`.

**New blocker: binder driver.** All HIDL services abort with
`Failed to setup binder polling: -9` / `Could not setThreadPoolConfiguration: -9`
(EBADF). Kernel 3.10 has `CONFIG_ANDROID_BINDER_IPC` but **not**
`CONFIG_ANDROID_BINDER_DEVICES`: it only creates `/dev/binder`; Android 10 needs
`/dev/hwbinder` and `/dev/vndbinder`. -> Next step V13 (multi-binder backport to the
kernel). It is a kernel driver change (recompiles kernel + boot).

### (historical) V12 -- first-stage /system entry hardcoded in init

V11 failed the same, but revealed TWO blockers: (a) `GetFstabPath` is still empty;
(b) `ReadFirstStageFstab()` filters out every entry without the `first_stage_mount` flag, and the
`/system` entry of `fstab.sc8830` does not carry it. Positive: SELinux now boots
permissive. Detail: `results/phase-5/v11-bootloop-recovery/DIAGNOSIS.md`.

V12 injects the `/system` entry by hand in `ReadFirstStageFstab()`
(`system/core/init/first_stage_mount.cpp`,
`sm-t280-phase5/scripts/apply-v12-hardcoded-fstab.py`), `BuildGsiSystemFstabEntry`
pattern, with `first_stage_mount=true` + `wait=true`. It removes
all dependency on DT, `ro.hardware`, file and flags. init recompiled with
the patch (verified: the ramdisk binary contains the `by-name/SYSTEM` path).

- Package: `sm-t280-phase5/packages/SM-T280-android10-hardcoded-fstab-PHASE5-v12-DO-NOT-FLASH.tar.md5`
- package_sha256: `1873981e65850d032db77b46186cd645e76a7663071184227f84e51734861410`
- Detail: `results/phase-5/PHASE5-V12-HARDCODED-FSTAB.md`.

Uncommitted changes in the tree (preserve): `system/core/init/security.cpp`,
`system/core/fs_mgr/fs_mgr_fstab.cpp` (V11), `system/core/init/first_stage_mount.cpp`
(V12), `device/.../mkbootimg.mk` (V6->V9), `device/.../BoardConfig.mk`,
`device/.../dts/sprd-scx35_gtexswifi_rev05.dts` (V10, inert).

### (historical) V11 -- fstab patch in fs_mgr

Both of Android 10's first-stage mechanisms are dead here (DT: no
/proc/device-tree; file: no `ro.hardware` because the bootloader ignores the
cmdline). Patch in `system/core/fs_mgr/fs_mgr_fstab.cpp` (`GetFstabPath()`,
`sm-t280-phase5/scripts/apply-v11-fstab-fallback.py`): fallback to
`/fstab.sc8830`. init recompiled with the patch (verified in the binary).
Legacy ramdisk (V9) intact.

- Package: `sm-t280-phase5/packages/SM-T280-android10-fstab-fallback-PHASE5-v11-DO-NOT-FLASH.tar.md5`
- package_sha256: `cf70ffebf3ff00a6e9e1537afaab765d489769e399d6decffc6aeb62a82eea64`
- Detail: `results/phase-5/PHASE5-V11-FSTAB-FALLBACK.md`.

Uncommitted changes in the tree (preserve; do not resync/checkout):
`system/core/init/security.cpp` (mmap_rnd_bits),
`system/core/fs_mgr/fs_mgr_fstab.cpp` (V11 fallback),
`device/.../mkbootimg.mk` (V6->V9 ROOT_OUT + init binary),
`device/.../BoardConfig.mk` (GCC4.8),
`device/.../dts/sprd-scx35_gtexswifi_rev05.dts` (V10 firmware/android/fstab; inert
without /proc/device-tree, can be left).

## Recommended next step

### V13 (flashed) -- binder multi-device OK; binder SG + /data missing

**Success:** the `binder polling: -9` disappear; zygote, surfaceflinger,
netd, media... start. Boot advances much further. **New blockers** (see
`results/phase-5/v13-hang-recovery/DIAGNOSIS.md`):
1. Binder without scatter-gather: `binder: unknown command 0x40286211 (BC_TRANSACTION_SG)`,
   `ioctl ... -22` -> surfaceflinger + HIDL fail `registerAsService=-2147483648`.
   -> **V14: SG backport to the binder.**
2. `/data` not mounted -> `dalvik-cache ... No such file` -> zygote aborts.
   -> ensure `mount_all`/fstab of `/data` in second-stage.

### (historical) V13 -- multi-binder backport to the kernel

Patch to `drivers/staging/android/binder.c` (kernel 3.10,
`sm-t280-phase5/scripts/apply-v13-multibinder.py`): per-device context manager
+ registration of `binder,hwbinder,vndbinder` (AOSP common kernel pattern).
16 context_mgr_node refs and 5 uid refs migrated to `proc->context->...`
(`binder_inc_node` uses `node->proc->context`). Kernel recompiled; the binary
contains `binder,hwbinder,vndbinder`.

- Package: `sm-t280-phase5/packages/SM-T280-android10-multibinder-PHASE5-v13-DO-NOT-FLASH.tar.md5`
- package_sha256: `6014cb981ba512adcfb3a1a4c74ffb90fd8d0453cb84ea4ab06e97dc73901a58`
- Detail: `results/phase-5/PHASE5-V13-MULTIBINDER.md`.

Additional uncommitted change (preserve): `.../drivers/staging/android/binder.c`.

### V14 (flashed) -- binder SG at command level OK; /data + fixes missing

**Success:** `unknown command 0x40286211` and `registerAsService=-2147483648` = 0
(the SG is processed). No kernel panic. **Remaining blockers** (see
`results/phase-5/v14-hang-recovery/DIAGNOSIS.md`):
1. `/data` not mounted -> cascade (dalvik-cache, keystore chdir /data/misc/...).
2. `binder_transaction_buffer_release: bad object type 70742a85` (=BINDER_TYPE_PTR):
   the PTR case is missing in that function (omitted in V14).
3. SIGSEGV in hwservicemanager/audioserver: possible mis-delivered SG data or
   effect of 1/2; re-evaluate after fixing them.
### V15 (current candidate) -- /data mountable + PTR case in binder release

`sm-t280-phase5/scripts/apply-v15-data-release.py`: (1) `BINDER_TYPE_PTR` case in
`binder_transaction_buffer_release` (silences "bad object type"); (2) fstab `/data`
-> `wait,check,formattable` (no FDE encryption, formats if the mount fails). Kernel
recompiled; ramdisk with `/data ... formattable` (verified).

- Package: `sm-t280-phase5/packages/SM-T280-android10-data-mount-PHASE5-v15-DO-NOT-FLASH.tar.md5`
- package_sha256: `c34d1399c8957f157a20c8da90580f4e698e7af71ebecb751e67e4f22121826e`
- Detail: `results/phase-5/PHASE5-V15-DATA-RELEASE.md`.

Additional uncommitted changes (preserve): `.../binder.c` (PTR release),
`.../rootdir/fstab.sc8830` (/data formattable).

## State after V15 + /data format (2026-09-18)

- `/data` (mmcblk0p27) formatted ext4 and mounting **RW** (confirmed). The binder's "bad
  object type" removed. Real progress.
- BUT the boot **does not create the `/data` structure** (stays empty: only
  `lost+found`) -> `keystore`/`installd`/`zygote` abort in a **loop**. Failure in the
  **post-fs-data/storage (FBE/vold)** layer.
- **Visibility wall:** the crash loop floods `ramoops`/`last_kmsg` and
  hides the root cause (vold/cryptfs/servicemanager). No ADB in system or
  tombstones on disk. Detail: `results/phase-5/v15c-recovery/DIAGNOSIS.md`.

### V18 (flashed) -- MILESTONE: /data + plumbing OK; graphics HAL layer (pthread_t)

`ro.hardware=sc8830` (V18) unblocked everything: **`/data` mounts RW and structures
fully** (misc, system, dalvik-cache, tombstones...), apexd,
hwservicemanager, logd, cryptfs init_user0, zygote start. /data root cause resolved.
**New blocker:** `surfaceflinger` aborts with `invalid pthread_t ... passed to
pthread_getschedparam` (`graphics.composer@2.1` Mali graphics HAL); audioserver
SIGSEGV. It is the known problem of Android 5-7 blobs vs Android 10's strict
bionic. See `results/phase-5/v18-recovery/DIAGNOSIS.md`.
### V20 (current candidate) -- graphics HIDL services missing from the device tree

Finding: the blob MODULES (`gralloc.sc8830.so`, `hwcomposer.sc8830.so`,
`libGLES_mali.so`) were there, but NOT the HIDL SERVICES Android 10 requires
(`composer@2.1-service`, `allocator@2.0-service`, `mapper@2.0-impl`) -> surfaceflinger
requested the composer and nobody provided it -> EX_TRANSACTION_FAILED. V20 adds them to
`device.mk` PRODUCT_PACKAGES (`apply-v20-graphics-services.py`); they are `vendor:`
modules -> installed in `system/vendor/bin/hw` + `system/vendor/lib/hw` with their
`.rc`. Full build; fresh boot+system.

- Package: `sm-t280-phase5/packages/SM-T280-android10-graphics-hidl-PHASE5-v20-DO-NOT-FLASH.tar.md5`
- package_sha256: `1c7e442f3fd2b70a77520dbd0059a78511d11056be189617f41a5a4614c7e753`
- Detail: `results/phase-5/PHASE5-V20-GRAPHICS-HIDL.md`.

Additional uncommitted change (preserve): `device/samsung/gtexswifi/device.mk`
(V20), `bionic/.../pthread_internal.cpp` (V19). After flashing: see whether composer@2.1
comes up and surfaceflinger composes (boot animation) or whether the default composer crashes
loading HWC1 (needing hwc2on1adapter) / gralloc1 allocator.

### (historical) V19 -- pthread_t resolved; per-HAL frontier (Mali composer)

The `invalid pthread_t` abort **disappeared** (shim OK). But `surfaceflinger` keeps
aborting: `Failed HIDL return status not checked: EX_TRANSACTION_FAILED` when calling
the `graphics.composer@2.1` HAL (Mali, lazy HAL that does not come up); `keymaster` with
no viable device. Per-HAL frontier of Android-5 blobs on Android 10; `/data/tombstones`
empty (limited visibility). Next: gralloc/hwcomposer adapters
(hwc2on1adapter, gralloc mapper) and isolate composer@2.1. See
`results/phase-5/v19-recovery/DIAGNOSIS.md`. Long effort, result not guaranteed.

### (historical) V19 -- pthread_t shim in bionic
(`__pthread_internal_find` returns the pointer instead of `async_safe_fatal` with
an unknown pthread_t). In system.img (full build). Package
`SM-T280-android10-pthread-shim-PHASE5-v19-DO-NOT-FLASH.tar.md5`, package_sha256
`ffd889a16f7be31e2407c61b0957b218d4cd38ca15e206cdbe7edf974167feb4`. After flashing:
see whether surfaceflinger stops aborting; watch audioserver and the next graphics
hurdle (gralloc/EGL). Detail: `results/phase-5/PHASE5-V19-PTHREAD-SHIM.md`.

### (reference) V18 -- ro.hardware built correctly (full build)

V17 was built wrong (dynamic init in the ramdisk -> reboot loop; and ro.hardware is
second-stage -> goes in system.img, not the ramdisk). V18 = same patch
(`init.cpp` default sc8830 + init.rc checkpoint off) rebuilt with
**`build-full-rom.sh` (mka)**: correct static ramdisk `/init` 1,375,992 B, and
`/system/bin/init` of **rebuilt system.img** with V17. Fresh boot+system are flashed
(system changes vs V5). See `results/phase-5/PHASE5-V18-*.md` and
`results/phase-5/v17-recovery/DIAGNOSIS.md`.

- Package: `sm-t280-phase5/packages/SM-T280-android10-ro-hardware-full-PHASE5-v18-DO-NOT-FLASH.tar.md5`
- package_sha256: `ad005e0954d3d84a1f13aaafb6c712e15f74c8a1367eabd136a1b10685e8cf1c`
- boot_sha256 `dedb19b4...`; system_sha256 `f9107867...`.

**RULE (critical):** there are TWO init -- STATIC ramdisk (first-stage) and
`/system/bin/init` DYNAMIC (second-stage/system.img). Never copy one over the
other. For changes in init/fs_mgr: full `build-full-rom.sh` + repackage
boot+system. See START-HERE.md.

### (historical) V17 -- force ro.hardware=sc8830 (built wrong)

`ro.hardware` stayed **"unknown"** (bootloader does not pass androidboot.hardware) ->
`init.rc:9 import /init.${ro.hardware}.rc` did not import `init.sc8830.rc` ->
`mount_all /fstab.sc8830` **never ran** -> `/data`/`/cache` unmounted -> mkdir RO
-> loop. V17 (`apply-v17-ro-hardware.py`) patches `init.cpp` to default
`ro.hardware="sc8830"`. It fixes the /data mount AND the `${ro.hardware}` resolution
(HALs included). Verified: the ramdisk init contains "sc8830".

- Package: `sm-t280-phase5/packages/SM-T280-android10-ro-hardware-PHASE5-v17-DO-NOT-FLASH.tar.md5`
- Detail: `results/phase-5/PHASE5-V17-RO-HARDWARE.md` - root cause in
  `results/phase-5/v16-recovery/DIAGNOSIS.md`.

Additional uncommitted changes (preserve): `system/core/init/init.cpp` (V17),
`system/core/rootdir/init.rc` (V16). After flashing: mount /data from recovery and
check structure + `/data/tombstones/`.

### (historical) V16 -- unblock post-fs-data (diagnostic)

`init.rc` `on post-fs-data` runs `exec ... vdc checkpoint prepareCheckpoint`
(blocking, depends on broken vold) BEFORE creating `/data/*`. V16
(`sm-t280-phase5/scripts/apply-v16-postfsdata.py`) comments out that checkpoint +
`installkey /data`. Boot only (init.rc goes in the ramdisk; there is no duplicate in
system). Verified: ramdisk with `# V16 diag`, checkpoint inactive.

- Package: `sm-t280-phase5/packages/SM-T280-android10-postfsdata-PHASE5-v16-DO-NOT-FLASH.tar.md5`
- package_sha256: `e97f4d3243d2aa11a067a989bb0bedcd4899876477033bb33a2562923bf5b26f`
- Detail: `results/phase-5/PHASE5-V16-POSTFSDATA.md`.

Additional uncommitted change (preserve): `system/core/rootdir/init.rc` (V16).

## Recommended next step

Flash **V16**, boot, force recovery, mount /data and read structure +
tombstones:
```
adb shell mount -t ext4 /dev/block/platform/sdio_emmc/by-name/userdata /data
adb shell 'ls /data; ls -l /data/tombstones/ 2>&1'
```
- If `/data` has structure (misc, dalvik-cache, tombstones): post-fs-data
  unblocked. Read the hwservicemanager tombstone (HIDL root cause at last).
- If it is still empty: the blocker is in another post-fs-data step (fsverity_init,
  apexd) or in vold; isolate with the now-readable /data.

--- (obsolete, reference) restore visibility ---
1. V16 diagnostic: enlarge `ramoops`/`CONFIG_LOG_BUF_SHIFT` (find the pstore/ramoops
   config in DTS/board) so the whole boot fits, or set the crashing looping
   services to `oneshot`/`disabled` temporarily.
2. With the boot readable, isolate why `post-fs-data` does not create `/data/*`
   (probable `vdc cryptfs init_user0`/FBE) and disable FBE for a diagnostic
   boot.
3. With `/data` structured, read tombstones on disk -> cause of the
   `hwservicemanager` SIGSEGV (VINTF manifest vs binder).
4. Then: Mali-400 graphics HAL.

Interdependent blockers (storage/FBE + HIDL + graphics) + degraded
visibility = long bring-up. A natural point to consolidate if preferred.

### (historical) V14 -- binder scatter-gather

Patch to `uapi/binder.h` + `binder.c` (`sm-t280-phase5/scripts/apply-v14-binder-sg.py`):
`BINDER_TYPE_PTR`, `binder_buffer_object`, `binder_transaction_data_sg`,
`BC_TRANSACTION_SG/BC_REPLY_SG`, `extra_buffers_size` in the allocator, size-aware
validation and PTR case with parent fixup. Kernel recompiled (binder.o OK).

- Package: `sm-t280-phase5/packages/SM-T280-android10-binder-sg-PHASE5-v14-DO-NOT-FLASH.tar.md5`
- package_sha256: `2034b319c7d6129d79d083414440f5a6cff7272631a03a43affbe540aed8fdfd`
- Detail/risk: `results/phase-5/PHASE5-V14-BINDER-SG.md`.

Additional uncommitted change (preserve): `.../uapi/binder.h` +
`.../binder.c` (SG).

## Recommended next step

1. Flash **V14** in Odin AP (Auto Reboot OFF, no PIT/Re-Partition), boot,
   force reboot to recovery, `adb pull /proc/last_kmsg`.
2. Success: `unknown command 0x40286211` / `registerAsService=-2147483648` disappear;
   surfaceflinger does not crash; HIDL services register.
3. Expected next fronts: (a) **Mali-400 graphics HAL** (gralloc/hwcomposer/
   EGL) so SurfaceFlinger composes -> boot animation; (b) **mount `/data`**
   (dalvik-cache) for zygote.
4. If a NEW kernel panic/instability appears, suspect the SG (PTR case / parent
   fixup) and consider a rollback to stock.
5. SELinux permissive OK; `ext4_find_entry` mmcblk0p25 under observation.

## Relevant scripts

- `sm-t280-phase5/scripts/rebuild-bootimage.sh`
- `sm-t280-phase5/scripts/verify-boot-ramdisk.sh` (V8: requires init + fstab)
- `sm-t280-phase5/scripts/apply-v8-fstab-ramdisk.py`
- `sm-t280-phase5/scripts/prepare-v8-package.sh`
- `sm-t280-phase5/scripts/package-system-for-odin.sh`
- `sm-t280-phase5/scripts/verify-odin-boot-system-package.sh`
- `sm-t280-phase5/scripts/legacy_sparse.py`
- `sm-t280-phase5/scripts/prepare-legacy-sparse-system-odin-candidate.sh`
- `sm-t280-phase5/scripts/capture-first-boot.sh`
