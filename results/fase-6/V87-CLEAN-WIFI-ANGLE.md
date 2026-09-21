# V87 -- Clean SwiftAngle, Wi-Fi SDIO retry and persistent app configuration

Status: **PARTIAL ON HARDWARE -- SCALE 2 FAILS; SCALE 1 RECOVERS THE LOGIN**
Date: 2026-09-21

## Goal

Produce a single cumulative iteration over V86 that removes the temporary instrumentation before measuring
the target app, makes the Wi-Fi load deterministic, keeps the SwiftAngle opt-in after a data wipe and
allows testing a lower resolution without generating extra packages. Camera and GNSS remain out of scope.

## Changes

1. Removed all V82/V83 traces from `libEGL`, `FrameBufferAndroid` and the GLES `Context`.
2. `libwifi_hal` retries `finit_module(sprdwl)` when it returns `EPERM`, which is the error emitted by the
   driver while `get_sdiohal_status()!=1`. Maximum 30 retries every 500 ms. `EEXIST` is still success;
   other errors are not hidden.
3. `SwiftAngle.apk` adds a `BOOT_COMPLETED` receiver, signed with platform and with `WRITE_SECURE_SETTINGS`,
   that restores ANGLE only for `com.example.app`.
4. SwiftShader sets its ANativeWindow to `1/scale` per axis. The default is `persist.swiftangle.scale=2`:
   1280x800 becomes 640x400 and SurfaceFlinger scales it up to the SurfaceView. Values 1..4 are accepted;
   anything else is treated as 1.
5. No camera provider or GNSS were added.

## Build result

- `V87_STATIC_VERIFY_PASS`
- `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`
- `V87_BUILD_AND_PACKAGE_PASS`
- Exact Odin content: `boot.img` + `system.img`
- Boot V75 unchanged: `fe89ef3181bfecea8d4bb24ceaed026a38f4005a8891a447c045b82781033be8`
- V87 package: `eecab5a10e6335bc137afa2dcfaeaf2810c353521f721d151069b90d14928872`

Package: `sm-t280-phase6/packages/SM-T280-android10-clean-wifi-angle-PHASE6-v87-DO-NOT-FLASH.tar.md5`

## Hardware validation pending

Flashing is done by the user in Odin AP, with Auto Reboot disabled, no PIT and no Re-Partition. Before
capturing results, the real state of the tablet, display, button and ADB will be expressly confirmed; none
will be assumed.

Planned checks:

1. Full boot and absence of regressions in display, touch, button, audio and Bluetooth.
2. Wi-Fi must create `wlan0` and connect automatically, without a manual module reload. Repeat across
   several boots before closing WIFI1.
3. Confirm `angle_gl_driver_selection_pkgs=com.example.app`, value `angle`, and `persist.swiftangle.scale=2`.
4. Open the target app: initial video, login visible, touch aligned and no scaling artifacts.
5. Measure frame time without traces. A/B comparison on the same system: change the scale to 1 or 2, force
   stop and relaunch the app. No reflash required.
6. Only if performance is acceptable: real login, content, lessons, video/audio, Bluetooth, suspend/resume
   and a long temperature/stability test.

## Scale rollback without reflashing

With ADB working, set `persist.swiftangle.scale=1`, force stop the target app and relaunch it. The value is
read when creating the EGL WindowSurface; it does not apply to Mali or the rest of the system.

## Hardware result

- Scale 2: black screen. SurfaceFlinger had a 640x400 buffer allocated, but the SurfaceView had no
  `activeBuffer`; EGL stayed at 1280x800 and rejected the smaller buffer.
- Scale 1: after closing and relaunching only the target app, `activeBuffer=1280x800 RGBA_8888`; the user
  confirmed the login visible after about a minute.
- The tablet is left configured at `persist.swiftangle.scale=1`.
- Successor fix: V88 syncs the EGL/FrameBuffer dimensions with the ANativeWindow.
