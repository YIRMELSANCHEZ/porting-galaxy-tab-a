# V68 -- consolidated hardware and usability candidate

Build date: 2026-09-20. Status: **BUILD/OFFLINE PASS; physical test pending**.

V68 is a single cumulative iteration over V67. A single Odin package with `boot.img` and `system.img` was
prepared; no intermediate `.tar.md5` packages were generated.

## Changes included

- Keeps the V67 screen off/on, touch recovery and late-suspend cancellation solution entirely.
- HIDL services for the existing legacy HALs: Bluetooth 1.0, sensors 1.0, power 1.0, camera provider 2.4,
  GNSS 1.0 and light 2.0.
- Binderized memtrack 1.0 service.
- ClearKey DRM 1.2. Does not include Widevine.
- VINTF manifest updated with the above interfaces and instances.
- Stock `libiwnpi.so` installed for `wcnd`; the source implementation, incompatible with Android 10's
  private libnl headers, is renamed and left out of the product.
- Early `/efs` and `/productinfo` mount points, with the SELinux labels needed for system-as-root.
- Gralloc: no ION invalidation is requested on descriptors that are not valid ION.
- SystemUI: the capture is copied to software `ARGB_8888` before compressing to PNG.
- Composer: it first tries Spreadtrum's native HWC1/GSP via `HWC2On1Adapter`; if opening or initializing it
  fails, it falls back to the V67 gralloc/framebuffer path.
- Audio: disables the modem-monitor retry thread on this Wi-Fi-only model.

## Deliberate exclusions

- **Gatekeeper HIDL:** no usable legacy HAL exists; the default HIDL service would abort. Android's software
  fallback is kept.
- **Spreadtrum OMX:** stays disabled due to the demonstrated ABI incompatibility between the 5.1 blobs and
  Android 10 Stagefright. Codec2 software codecs are kept.
- **Widevine:** no suitable blobs exist; ClearKey is not equivalent to Widevine.
- **Thermal:** the kernel already protects via thermal zones/cooling device and there is no suitable HAL.
- **Vibrator:** no node or motor evidence was found on the SM-T280.
- **Wi-Fi scan timeout:** no speculative patch was applied; association, DHCP and Internet already work and
  there is no proven cause to justify changing the timeout.

## Offline validation

- `V68_MANIFEST_XML_PARSE_PASS`
- `V68_STATIC_VERIFY_PASS`
- module compilation: 6850/6850, PASS
- `system.img` rebuild: PASS
- `V68_OUTPUT_VERIFY_PASS` for all HALs, implementations, SystemUI, audio, gralloc, mountpoints, boot and
  system
- Odin legacy sparse image: Android sparse 1.0, 524288 blocks of 4096 bytes
- `ODIN_SYSTEM_PACKAGE_PASS`
- `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`
- `V68_CONSOLIDATED_PACKAGE_PASS`

The tree's `checkvintf` utility had a host defect: it computed the incompatibility but did not update its
return code. Only the host tool was fixed to get a real result. V68 adds no new incompatibilities. Exactly
the three known legacy exceptions persist: `IGatekeeper/default`, `IOmxStore/default` and `IOmx/default`;
they correspond to the software fallbacks noted above.

## Artifact

`sm-t280-phase6/packages/SM-T280-android10-consolidated-PHASE6-v68-DO-NOT-FLASH.tar.md5`

- Size: 1,022,259,293 bytes
- Exact content: `boot.img` + `system.img`
- Embedded Odin MD5: `cc0a26e060342bd7c64deb5ab3d3bf0e`
- Package SHA-256: `a626e314470dfff7b9a7b6a316e3b30f76551efbdc71f0f7c0641da67219148a`
- boot SHA-256: `302e7fe2d52f25b946ea2a1e0ec46e7f471a3140e86dc4d7009c38d83b5a727f`
- standard system SHA-256: `bec65f69ddff74808d8737e7c2e66d9c5521a03e2e151ef4e02f48c1071ae92e`
- Odin sparse system SHA-256: `0e50bf2f58e0d488462c0d23f0b0b93ddf6549f89a3cac068394ada99a554e97`

## Single physical test matrix

1. Boot to launcher and `sys.boot_completed=1`; stability of `system_server`, keystore, audioserver and
   SystemUI.
2. V67 regression: turn off/on with POWER normally and quickly; verify screen and touch.
3. `lshal`: check stable registration of Bluetooth, sensors, power, camera provider, GNSS, light, memtrack
   and ClearKey.
4. Auto-rotation and sensor listing.
5. Bluetooth: enable, get the adapter and pair a device.
6. Power HAL: interaction/scroll and absence of service crashes.
7. Rear and front camera: enumeration, preview and capture.
8. GNSS/location: provider available; the fix requires open sky and may take time.
9. Brightness and light HAL.
10. POWER+VOL- capture: non-empty PNG visible in Gallery.
11. Graphics: identify one of the two V68 paths in the log and measure FPS/CPU. The fallback must keep the
    V67 behavior if the native HWC1 does not open.
12. Wi-Fi 2.4 GHz and Internet, audio, microphone and software video playback.
13. Confirm the absence or reduction of the ION `EBADF` spam and the audio modem retry.
14. Verify `/efs` and `/productinfo` mounted, without publishing full MAC addresses.
15. Test PIN/pattern with the software fallback before considering it supported.

A HAL must not be declared functional just because it appears in `lshal`: all these subsystems remain
**DETECTED / PENDING FUNCTIONAL TEST** until this matrix is completed on hardware.
