# V96 final package -- general-purpose tablet (camera + microG + microphone)

Goal: leave the SM-T280 as a usable general-purpose tablet, dropping the optimizations specific to an app
that requires GLES 3.0. Built on 2026-09-21.

Package: `sm-t280-phase6/packages/SM-T280-android10-general-microg-camera-PHASE6-v96-DO-NOT-FLASH.tar.md5`
Script: `scripts/build-v96-final.sh`. `V96_STATIC_VERIFY_PASS` + `V96_BUILD_AND_PACKAGE_PASS`.

| artifact | sha256 |
|---|---|
| Odin package (1.6 GB) | `0ed3d3d6d7512f181952bda84fe840336eb529744cec8a7687487332a24a06c6` |
| boot.img (kernel V75, unchanged) | `fe89ef3181bfecea8d4bb24ceaed026a38f4005a8891a447c045b82781033be8` |
| raw system.img | `1f6baa82d6b8ab7c6309e0a66050d72da0bc7970a1ffdba78ed7d335fc20b02e` |
| system in the package | `13625d95297bb807abe48e84ba10842dbe78a92a2c679bd2ce22be608fb9dc60` |

Flashing (as always): Odin AP, **Auto Reboot OFF, Re-Partition unchecked**, boot+system only. Validation
confirmed that the microG signature ("NOGAPPS Project") survives PRESIGNED, a requirement of the signature
spoofing.

## 1. Composition

Base **V95** (all platform fixes, see `TODO-ANALYSIS.md`): Android 10 boot, Wi-Fi, Bluetooth with
coexistence, power button, storage, rotation, hardware H.264 decoder, SwiftAngle (GLES 3.0 in software,
available as a general driver).

Added in V96:
- **V98 -- working camera.** Two software fixes: (1) the camera provider is launched with `LD_PRELOAD` of
  the `libcamera_shim.so` shim (Android 10's linker dropped `LD_SHIM_LIBS`, so the `libmemoryheapion.so`
  blob did not load `android_atomic_or`); (2) a patch in `CameraDevice::sGetMemory` to tolerate the
  `user=NULL` that the Spreadtrum 5.1 HAL passes from its preallocation thread (previously a SIGSEGV).
  Result verified live: `dumpsys media.camera` = 2 cameras, sensor and HAL working. Detail in
  `CAMERA-V98.md`.
- **V99 -- microG.** `GmsCore` (com.google.android.gms) and `FakeStore`/Companion (com.android.vending),
  official APKs v0.3.16.252432 signed with the "NOGAPPS Project" key, installed as priv-app via
  `PRODUCT_COPY_FILES` (byte-for-byte copy, no recompression or realignment, signature intact). LineageOS
  17.1 already ships microG-restricted signature spoofing (`PackageManagerService.isMicrogSigned`, active
  because `ro.debuggable=1`), so the **framework is not patched**. The exact privileged permissions are in
  `microg-permissions.xml` (extracted from the APKs themselves; the system is in
  `ro.control_privapp_permissions=enforce`).

Removed / not activated (target-specific): the per-app ANGLE opt-in and the `persist.swiftangle.*` tuning.
The props remain in `device.mk` but are inert without the ANGLE opt-in. SwiftAngle stays as a general
GLES 3 capability.

## 2. Real state of "functional apps"

Measured diagnosis: normal apps already rendered fine (Aurora, settings, launcher). The block on YouTube
and similar was not graphical but **the absence of Google Play Services** ("requires the Google Play
Store, but it is missing"). microG solves it for compatible apps. Apps that require real GLES 3.0 (heavy
3D games) will still be limited by the Mali-400 (GLES 2.0 in hardware); that is a physical limit.

## 3. microG configuration after flashing (one-time)

1. Flash V96 (boot + system) via Odin AP, Auto Reboot OFF, Re-Partition unchecked (as always).
2. On boot, open **microG Settings** (the "microG Services" app).
   - **Self-Check**: the "System spoofs signature" box must be checked (green). If not, microG is not
     recognized; check that `ro.debuggable=1` and that the APK was not altered.
3. In microG Settings enable: **Google device registration** and **Cloud Messaging** (for push
   notifications). Optional: **SafetyNet** (DroidGuard).
4. Grant microG the location permissions and whatever the self-check requests.
5. Reboot. Apps that use Play Services (Google login, FCM, maps) should now work.
6. Aurora Store is already installed; it can be used anonymously or with a Google account.

Note: `/data` survives a system-only flash. If the tablet had the target app with ANGLE enabled, that
setting persists; to leave it clean:
`settings delete global angle_gl_driver_selection_pkgs` and `settings delete global angle_gl_driver_selection_values`.

## 4. What remains to verify after the first boot

- Camera app preview: the HAL works, but the legacy Camera2 GL path failed to allocate the buffer
  (`gralloc usage 0x702`), possibly due to RAM pressure from the tests. Re-evaluated with the camera
  integrated and a clean boot. Alternatives if it persists in `CAMERA-V98.md` (preview section).
- microG self-check and registration. It is user configuration, not build.
