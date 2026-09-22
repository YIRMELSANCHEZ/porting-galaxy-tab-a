# Phase 5 -- V18: V17 (ro.hardware=sc8830) built correctly (full build)

Date: 2026-09-18. Status: in offline build/validation; `DO-NOT-FLASH`.

## Reason

V17 (patch `ro.hardware` default = sc8830 in `init.cpp`) was built wrong:
`m bootimage` does not recompile init, and the workaround (copying
`system/bin/init` to the ramdisk) put the DYNAMIC init in first-stage -> reboot
loop. Also the change is **second-stage** (`/system/bin/init` in system.img), not
the ramdisk. See `results/phase-5/v17-recovery/DIAGNOSIS.md`.

## Change

Same patch as V17 (`apply-v17-ro-hardware.py`, `init.cpp` default sc8830) +
V16 (init.rc checkpoint off), but rebuilt with a **full build
(`build-full-rom.sh` = mka)**. Consistent result:
- ramdisk `/init`: **static 1,375,992 B** (first-stage, with V11/V12).
- `/system/bin/init`: dynamic, recompiled with V17 (second-stage).
- `system.img` **rebuilt** (no longer the legacy-sparse reused from V5;
  incorporates all current source patches).

Fresh **boot + system** are packaged (both change).

## Offline validation

- Build: `build-full-rom.sh` OK (50:27). Log `results/phase-5/v18-full-build.log`.
- Boot: `verify-boot-ramdisk.sh` (static init 1.37MB + fstab + init.rc + /system).
- Packaging: `prepare-v18-package.sh` (new system -> legacy sparse 32/16).

## Artifact

- Package: `sm-t280-phase5/packages/SM-T280-android10-ro-hardware-full-PHASE5-v18-DO-NOT-FLASH.tar.md5`
- package_sha256: `ad005e0954d3d84a1f13aaafb6c712e15f74c8a1367eabd136a1b10685e8cf1c`
- boot_sha256: `dedb19b4ff171fc00936f6a8625928a1a0bfce6a114b491b4a55413330b56851`
- system_sha256 (legacy sparse): `f910786768d612d68228b3c82cce07876b45bc9849d2b7e5aa63e3848ee15e7b`
  (CHANGES from V5: system.img rebuilt)
- Boot: static ramdisk init 1,375,992 B; `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`.

## Expected interpretation

With `ro.hardware=sc8830` effective in second-stage:
- `import /init.sc8830.rc` works -> `mount_all /fstab.sc8830` -> `/data`/`/cache`
  mount RW -> post-fs-data creates the structure -> keystore/installd/zygote stop
  failing over missing dirs.
- `<name>.sc8830.so` HALs locatable (relevant for hwservicemanager/graphics).

Verify after flashing: mount /data from recovery and check structure +
`/data/tombstones/`.
