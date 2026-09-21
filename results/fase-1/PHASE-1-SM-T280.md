# Samsung SM-T280 Phase 1 Hardware Assessment

Capture date: 2026-09-15 (Europe/Madrid)  
Method: ADB over USB, read-only queries exclusively.  
States: **PASS**, **PARTIAL**, **FAIL**, **UNKNOWN**, **NOT_APPLICABLE**.  
Evidence level: **DETECTED** means enumerated or evidenced by Android/kernel; **FUNCTIONALLY TESTED** requires a real manual test, which was not performed in this phase.

## Executive result

- **PHASE_1_DEVICE_ANALYSIS_PASS**
- **PORTING_FEASIBILITY_PRELIMINARY: POSSIBLE_WITH_MAJOR_WORK**
- Nothing was flashed, installed, rebooted or modified on the tablet. No `dd`, root, recovery, Download Mode or fastboot was used.
- Identity matches: **SM-T280 / gtexswifi**. It is not SM-T285/gtexslte.
- A standard GSI **is not viable**: the device predates Treble, has no `vendor` partition, is not A/B and has no dynamic partitions.

## 1. Device identity

**Status: PASS -- DETECTED**

| Field | Value |
|---|---|
| Manufacturer / brand | Samsung / samsung |
| Model | SM-T280 |
| Device codename | gtexswifi |
| Product | gtexswifixx |
| Board / hardware | sc8830 |
| Product hardware | SCX35_J3_3G_V1.0.0 |
| SoC family | Spreadtrum SC8830 platform; firmware identifies SC7730SW |
| Variant check | Matches SM-T280 Wi-Fi; no T285/gtexslte detected |

Serial numbers and physical addresses are kept only in the original captures and are omitted from this report.

## 2. Current firmware

**Status: PASS -- DETECTED**

| Field | Value |
|---|---|
| Android | 5.1.1 |
| API level | 22 |
| Build ID | LMY47V |
| Build / PDA | T280XXU0AQJ1 |
| Bootloader property | T280XXU0AQJ1 |
| Fingerprint | `samsung/gtexswifixx/gtexswifi:5.1.1/LMY47V/T280XXU0AQJ1:user/release-keys` |
| Build type/tags | user / release-keys |
| Security patch | 2017-07-01 |
| CSC | TPA; firmware CSC `T280UVS0AQJ1` |
| Baseband | `unknown` (expected/inconclusive on the Wi-Fi variant) |

Extremely old firmware with no modern patches. This does not by itself prevent a port, but it widens the gap between the original BSP/HALs and Android 10.

## 3. CPU and ABI

**Status: PASS -- DETECTED**

- CPU: four ARM Cortex-A7 cores (CPUID part `0xc07`), ARMv7 rev 5; `/sys` reports CPU 0-3 present. In the capture only CPU0 was online due to hotplug/power management.
- Community-documented nominal frequency: 1.3 GHz; no frequency or hotplug was forced in this phase.
- Extensions: VFP, VFPv3/v4, NEON, Thumb, integer divide.
- ABI: `armeabi-v7a`, secondary `armeabi`; 32-bit list the same.
- 64-bit ABI: empty.
- **Cannot run `arm64-v8a` binaries.** Only apps with Java/universal code or compatible ARM32 native libraries.

## 4. Kernel

**Status: PARTIAL -- DETECTED**

- Linux `3.10.65-10429622`, compiled with GCC 4.8.
- `SMP PREEMPT`; Samsung build from 2017-10-21.
- Effective ARM32 architecture.
- Loaded modules: `sprdwl` (Wi-Fi) and `mali`.
- `uname` does not exist in the old userspace; `/proc/version` provided the alternative.
- `/proc/cmdline`: permission denied without root.
- `/proc/config.gz`: absent/not readable.
- Device tree at `/proc/device-tree`: no usable content without privileges.

Android 10 risk **CRITICAL**: 3.10 is a very old BSP kernel, off the normal Android 10 line and tied to proprietary Spreadtrum/Mali drivers. Numerous kernel compatibility changes will be needed for binder/ashmem, SELinux, namespaces, seccomp and probably specific downstream-tree patches. No buildable configuration or boot has been validated yet.

## 5. RAM

**Status: PASS -- DETECTED**

- Visible RAM: **1,490,432 KiB (~1.42 GiB)**, consistent with the nominal 1.5 GB.
- In the capture: ~104 MiB free and ~479 MiB cache; these values vary with load.
- Swap: `/dev/block/vnswap0`, 786,428 KiB, with ~167 MiB used during the capture.
- No `/sys/block/zram0`: the current swap is **VNSWAP**, not standard ZRAM.
- Full `dumpsys meminfo` hung for more than 90 s; it was interrupted without modifying the device and the compact variant was saved.

1.5 GB is viable only with a very austere Android 10 configuration (low-RAM, limited services and minimal GApps). Modern Google Play Services can put considerable pressure on it.

## 6. Storage

**Status: PASS -- DETECTED**

| Volume | Visible size | Used | Available | FS |
|---|---:|---:|---:|---|
| `/system` | 1.9 GiB | 1.9 GiB | 75 MiB | ext4, read-only |
| `/data` | 4.8 GiB | 3.1 GiB | 1.7 GiB | ext4 |
| `/cache` | 192.8 MiB | 0.5 MiB | 192.3 MiB | ext4 |
| `/efs` | 15.7 MiB | 0.14 MiB | 15.5 MiB | ext4 |

- Enumerated total eMMC: 7,634,944 KiB (~7.28 GiB; 8 GB nominal).
- The `/system` space is a high risk: an Android 10 + GApps image must fit in roughly 2 GiB and currently only 75 MiB remain in stock.
- The `/storage/extSdCard` mountpoint exists, but no microSD appeared mounted in `/proc/mounts`; physical presence/read is left for manual testing.

## 7. Partition layout

**Status: PASS -- DETECTED**

Classic eMMC scheme with 27 physical partitions. Main map:

| Name | Block | Approx. size |
|---|---|---:|
| SBOOT | mmcblk0p1 | 2 MiB |
| SBOOT2 | mmcblk0p2 | 2 MiB |
| WDSP | mmcblk0p7 | 4 MiB |
| MODEM | mmcblk0p8 | 8 MiB |
| MODEM2 | mmcblk0p9 | 8 MiB |
| PARAM | mmcblk0p16 | 2 MiB |
| efs | mmcblk0p17 | 20 MiB |
| KERNEL (boot) | mmcblk0p20 | 16 MiB |
| RECOVERY | mmcblk0p21 | 16 MiB |
| PERSISTENT | mmcblk0p22 | 1 MiB |
| persdata | mmcblk0p23 | 9 MiB |
| CACHE | mmcblk0p24 | 200 MiB |
| SYSTEM | mmcblk0p25 | 2 GiB |
| HIDDEN / preload | mmcblk0p26 | 40 MiB |
| userdata | mmcblk0p27 | ~4.93 GiB |

There is no `vendor`, `odm`, `product`, `super`, `vbmeta` partition or `_a/_b` duplicates. No images or partitions were copied.

## 8. Boot architecture

**Status: PARTIAL -- DETECTED**

- Traditional Samsung/Spreadtrum boot: separate `SBOOT`, `KERNEL`, `RECOVERY`.
- Reported bootloader: `T280XXU0AQJ1`.
- Treble: **NO** (property absent, Android 5.1 firmware and no `vendor`).
- A/B: **NO** (no slot suffix and no duplicated partitions).
- Virtual A/B: **NO**.
- Dynamic partitions: **NO** (no `super` or dynamic mapper).
- Standard GSI: **NOT VIABLE**. A GSI assumes the vendor separation/contract this device does not have; a specific ROM with integrated kernel, ramdisk, HALs and blobs is required.
- Bootloader/OEM Unlock state: **UNKNOWN**; not queried through special modes and no option was changed.

As an architectural reference, AOSP documents that Treble separates the vendor implementation through VINTF and that Android 10 dynamic partitions use `super`/`dm-linear`; none of those structures are present here: [AOSP partitions](https://source.android.com/docs/core/architecture/partitions), [dynamic partitions](https://source.android.com/docs/core/ota/dynamic_partitions/implement).

## 9. GPU

**Status: PARTIAL -- DETECTED, compositor active; not FUNCTIONALLY TESTED**

- GPU: ARM **Mali-400 MP** (community device-tree documentation identifies it as MP2).
- EGL driver: `1.4 Linux-r5p0-01rel0`.
- Advertised OpenGL ES: **2.0** (`0x20000`).
- Kernel module `mali` loaded.
- HALs present: `gralloc.sc8830.so`, `hwcomposer.sc8830.so`.
- SurfaceFlinger uses HWC and produced buffer/composition statistics; this evidences an active accelerated path on stock, not its correctness under Android 10.
- No Vulkan and no OpenGL ES 3.x. High risk for modern UI and apps; the Android 5.1 EGL/HWC blobs may be incompatible with Android 10.

## 10. Multimedia

**Status: PARTIAL -- DETECTED, not FUNCTIONALLY TESTED**

- Spreadtrum OMX declared for hardware decoding of MPEG-4, H.263, **H.264/AVC** and **VP8**, with declared limits up to 1920x1088.
- Spreadtrum encoder declared for MPEG-4, H.263 and H.264.
- SEC software decoders exist for H.263/H.264/MPEG-4/VP8.
- **HEVC/H.265:** appears only inside a commented XML block for VPU and as a SEC software decoder; no usable hardware decoder is confirmed.
- **VP9:** no declared decoder was found.
- Android 5.1 does not expose the modern `media.codec` service; `/system/etc/media_codecs.xml` was read directly.

Hardware playback is the most critical point for the target app. The components are declared, but must be tested with real app videos or equivalent samples (codec, profile, level, audio, DRM and resolution).

## 11. Audio

**Status: PARTIAL -- DETECTED, not FUNCTIONALLY TESTED**

- Main HAL: `audio.primary.sc8830.so`; policy HAL `audio_policy.sc8830.so`.
- Primary output active at 44.1 kHz; built-in speaker enumerated.
- Declared routes: speaker, wired headset/headphones, Bluetooth SCO/A2DP, USB and FM.
- Declared inputs: built-in microphone, back mic, headset mic, Bluetooth SCO and FM tuner.
- `mDualMicMode=1` appears in AudioService, but does not prove two physically working microphones.
- No audio was played or recorded.

## 12. Cameras

**Status: PARTIAL -- DETECTED, not FUNCTIONALLY TESTED**

- HAL: `camera.sc8830.so`, "Sprd camera HAL" module, Spreadtrum Corporation.
- Camera HAL device API 1.0 / module API 1.
- Two cameras: camera 0 rear (orientation 90 degrees) and camera 1 front (270 degrees).
- Resolutions do not appear in `dumpsys` with the cameras closed. Community documentation of the old tree indicates 5 MP rear and 2 MP front, pending verification.

## 13. Sensors

**Status: PARTIAL -- DETECTED, spot readings available**

| Sensor | Vendor | Version | Detected |
|---|---|---:|---|
| K2HH accelerometer | STM | 1 | Yes; reading present |
| SX9306 grip sensor (Wi-Fi) | SEMTECH | 1 | Yes; reading present |
| Screen Orientation Sensor | Samsung Electronics | 3 | Yes; virtual sensor |
| Magnetometer | -- | -- | Not enumerated |
| Gyroscope | -- | -- | Not enumerated; 9-axis fusion disabled |
| Ambient light | -- | -- | Not enumerated |
| Proximity | -- | -- | Not enumerated |

The `sec_touchscreen` touch panel is detected with range 800x1280 and multitouch declared. No test of all zones or gestures was done.

## 14. Wi-Fi

**Status: PARTIAL -- DETECTED; historical operation evidenced, not actively tested**

- Interface `wlan0`; kernel module `sprdwl` loaded.
- Wi-Fi enabled during the capture; the interface was without carrier/disconnected at the queried instant.
- The `dumpsys wifi` history shows full WPA2 associations, scans and 39 Mbps links on 2.4 GHz, which is evidence of prior use.
- Chip/stack community-documented in the old device tree: Spreadtrum/Marlin, WLAN `sc2341`, NL80211 + `sprdwl` driver.
- 5 GHz was not confirmed; observed results were 2.4 GHz.
- Masked MAC: `D0:B1:28:**:**:**`. SSID/BSSID are omitted from the report.

## 15. Bluetooth

**Status: PARTIAL -- DETECTED; currently off**

- Local adapter enumerated; `bdroid Ver=4.1` stack.
- Capture state: OFF (`state=10`), Bluetooth service not connected.
- History shows prior ON/OFF transitions, but no pairing or transfer was performed.
- Android features declare classic Bluetooth and BLE.
- Observable profiles/routes: A2DP and SCO; the full set requires enabling Bluetooth and testing peripherals manually.
- Masked address: `D0:B1:28:**:**:**`.

## 16. Battery and power

**Status: PARTIAL -- DETECTED, no autonomy test**

- Li-ion battery present and health `Good`.
- Level during capture: 81%; voltage ~4.06 V; temperature 38.2 degrees C on the second reading.
- USB appeared to be powering the device; status/current readings are inconsistent between `dumpsys` and `uevent` (charging status 3 / `Discharging`, very low current), possibly from negotiation or driver semantics.
- Thermal zone 1: battery, 38.2 degrees C. Zone 0 `sec-fuelgauge` does not expose `temp` via standard reading.
- Nominal capacity of 4000 mAh appears in community material, but the driver did not expose `charge_full_design`; therefore real capacity and degradation are UNKNOWN.
- Power manager awake, screen ON. No states were forced.

## 17. USB

**Status: PASS -- DETECTED/FUNCTIONALLY TESTED for ADB and MTP only**

- Current config: `mtp,adb` (`persist.sys.usb.config`, `sys.usb.config`, `sys.usb.state`).
- Native Windows ADB 37.0.1 connected correctly through the official Samsung Android USB Driver 1.9.5.0.
- USB host and accessory appear as Android features, but no OTG peripherals were tested.
- USB mode was not changed from ADB.

## 18. SELinux/security

**Status: PARTIAL -- DETECTED**

- SELinux: **Enforcing**.
- Policy identified: `SEPF_SM-T280_5.1.1_0072`.
- `ro.secure=1`, `ro.debuggable=0`, `ro.adb.secure=1`.
- Build signed with `release-keys`.
- Security patch 2017-07-01: current security state unacceptable for sensitive Internet exposure.
- Verified Boot state, rollback protection and real bootloader lock: UNKNOWN from Android without entering special modes.

## 19. Google ecosystem

**Status: PARTIAL -- INSTALLED/DETECTED, not FUNCTIONALLY TESTED**

| Component | Active version | versionCode | targetSdk | ABI |
|---|---|---:|---:|---|
| Google Play Store (`com.android.vending`) | 39.7.34-21 | 83973410 | 34 | armeabi-v7a |
| Google Play Services (`com.google.android.gms`) | 23.45.23 | 234523000 | 34 | armeabi-v7a |
| Google Services Framework | 5.1-1743759 | 22 | 22 | armeabi-v7a |
| Android System WebView | 95.0.4638.74 | 463807400 | 31 | armeabi-v7a |

Older factory copies also remain under `/system`. The active versions are in `/data/app`. Presence does not equal correct operation, Play Protect certification or future compatibility. On Android 10 ARM32 a compatible, minimal ARM GApps package should be used; the RAM/storage pressure is high.

## 20. Target app status

**Status: NOT_APPLICABLE -- NOT INSTALLED**

`com.example.app` is not installed. No APK was installed and no private data was inspected. Compatibility of the current app version, its native ABIs, WebView/DRM requirements and codecs remains UNKNOWN.

## 21. Android 10 compatibility assessment

**Overall status: PARTIAL -- HIGH/CRITICAL engineering risk**

Favorable factors:

- ARMv7 + NEON can run Android 10 in an ARM32 configuration.
- 1.5 GB exceeds the practical minimum of many low-RAM ports, though with little margin.
- Display, touch, audio, cameras, sensors, Wi-Fi, GPU and OMX are represented through stock HALs/drivers.
- A historical community device tree for `gtexswifi` and downstream kernel code exist.

Blockers/risks:

- Kernel 3.10 and GCC 4.8 toolchain.
- Legacy Spreadtrum SC8830/SC7730SW BSP and 32-bit Android 5.1 blobs.
- Mali-400/OpenGL ES 2.0 with EGL r5p0 and old HWC/gralloc.
- No Treble or vendor partition: all HALs/blobs must be integrated and shimmed into a specific build.
- 2 GiB `/system`, almost full on stock.
- No A/B, modern AVB or dynamic partitions.
- Hardware HEVC and VP9 not confirmed.
- 1.5 GB RAM + modern GMS can cause aggressive LMK and a poor experience.
- Android 10 uses system-as-root in its builds; AOSP explains the transition for non-A/B devices: [AOSP system-as-root](https://source.android.com/docs/core/architecture/partitions/system-as-root).

## 22. LineageOS 17.1 porting risks

**PORTING_FEASIBILITY_PRELIMINARY: POSSIBLE_WITH_MAJOR_WORK**

No evidence of official LineageOS 17.1 support for SM-T280 was found. There is an archived community `gtexswifi` tree oriented to CM/Lineage 14.1, with partition configuration, blob extraction and product files: [historical device tree](https://github.com/gtexswifi/android_device_samsung_gtexswifi). Community-maintained, unofficial downstream SC8830/kernel trees also exist: [Samsung SC8830 repositories](https://github.com/samsung-sc8830), [kernel gtexswifi stock](https://github.com/19atlas/android_kernel_samsung_gtexswifi_stock).

Priority risks:

1. **CRITICAL -- Kernel bring-up:** port minimal Android 10 patches without breaking downstream drivers.
2. **CRITICAL -- Graphics:** make the pre-Treble Mali EGL/gralloc/HWC blobs compatible with Android 10 SurfaceFlinger.
3. **CRITICAL -- Multimedia:** adapt Spreadtrum Stagefright/OMX; validate H.264 and the target app's audio.
4. **HIGH -- Vendor blobs:** inventory and legally extract stock blobs, resolve dependencies/namespace and create shims.
5. **HIGH -- SELinux:** build a functional enforcing policy; the old trees may depend on permissive.
6. **HIGH -- Storage:** fit `system`, framework and GApps into 2 GiB without repartitioning.
7. **HIGH -- Camera/Wi-Fi/Bluetooth/audio:** legacy HALs may compile but fail at runtime.
8. **HIGH -- Performance:** ARM Cortex-A7, Mali-400 and 1.5 GB limit GMS, WebView and modern apps.
9. **MEDIUM -- Legacy boot image:** adapt ramdisk/system-as-root while keeping the Samsung Spreadtrum format.

Useful information already identified for a later phase:

- Device: `gtexswifi`; platform/hardware: `sc8830`; SoC firmware: `SC7730SW`.
- Kernel partition 16 MiB, recovery 16 MiB, system 2 GiB, cache 200 MiB.
- Kernel module names `sprdwl` and `mali`.
- HAL suffix `sc8830` for audio, camera, sensors, gralloc, hwcomposer and lights.
- The historical device tree includes `extract-files.sh`, `proprietary-files.txt`, `BoardConfig.mk`, `device.mk` and Wi-Fi/Bluetooth configuration; it must be audited, not blindly reused.

## 23. Missing information

Information not accessible or not tested without root/manual actions:

- `/proc/cmdline`, full kernel configuration and binary device tree.
- Unlock/OEM Unlock/Download Mode state and secure bootloader details.
- Dump/internal inspection of boot/recovery/system and verification of real blobs; forbidden in this phase.
- Full CPU frequencies under load and hotplug behavior (only CPU0 was online during the snapshot).
- Real battery capacity/degradation and charge curves.
- Effective camera resolutions/modes.
- Touch operation across the whole surface, buttons and rotation.
- Real H.264/VP8 playback, synchronized audio/video, DRM and streaming.
- Audio capture/playback and microphone quality.
- Sustained Wi-Fi, 5 GHz, Wi-Fi Direct and suspend/resume.
- Bluetooth pairing, BLE, A2DP/HID and resume.
- microSD and USB OTG read/write.
- Real target-app compatibility, because the app is not installed and no APK/public metadata was provided.
- Play Protect certification and effective Play Store/GMS login/update.

### Diagnostic log snapshot

**Status: PARTIAL -- snapshot obtained, causality not confirmed**

- `dmesg` was readable without root and kept in full.
- No kernel panic was observed in the snapshot.
- `logcat` repeats `ThermalSensor` warnings because it tries to open a nonexistent thermal zone 2; the system enumerated only zones 0 and 1. This suggests a Samsung configuration mismatch, though the battery zone does deliver temperature.
- ART warnings appear about failing to open `/system/framework/timakeystore.jar` and a one-off MTP read error. They must be correlated with functional tests; by themselves they do not prove `/system` corruption or a persistent USB failure.
- The full logs may contain network names, identifiers and historical activity; they must not be published without sanitization.

## 24. Conclusions

**PHASE_1_DEVICE_ANALYSIS_PASS**: enough information was obtained to characterize hardware, firmware, ABI, kernel, memory, partitions, graphics, declared multimedia, HALs, connectivity, sensors, security and Google software.

**PORTING_FEASIBILITY_PRELIMINARY: POSSIBLE_WITH_MAJOR_WORK**.

The hardware does not mathematically rule out Android 10 ARM32, but the work is not an ordinary update or a GSI: it is a specific pre-Treble port. The dominant risks are kernel 3.10, Mali-400, proprietary Spreadtrum multimedia/HALs, the absence of `vendor`, the 2 GiB `/system` and 1.5 GB of RAM. Before considering any flashing, a bootable Android 10 kernel, a viable blob/HAL scheme and stable H.264/audio acceleration must be demonstrated. Deciding on flashing is not recommended yet.

## Final matrix

| Component | Detected | Current status | Android 10 relevance | Porting risk |
|---|---|---|---|---|
| CPU | Yes | ARMv7 Cortex-A7 quad, only CPU0 online at snapshot | ARM32 build required | HIGH |
| ABI | Yes | armeabi-v7a/armeabi; no arm64 | Limits modern native apps/GApps choice | HIGH |
| RAM | Yes | 1.49 GB + 768 MB VNSWAP | Low-RAM tuning essential | HIGH |
| Kernel | Yes | 3.10.65 downstream | Large backport/compatibility gap | CRITICAL |
| Display | Yes | 800x1280@60, 213 dpi | Legacy display stack | MEDIUM |
| Touch | Yes | sec_touchscreen, multitouch | Input driver/policy adaptation | MEDIUM |
| GPU | Yes | Mali-400 MP, GLES 2.0, EGL r5p0 | Legacy proprietary graphics blobs | CRITICAL |
| Video decoder | Declared | H.264/MPEG4/VP8 OMX; not playback-tested | Critical for the target app | CRITICAL |
| Audio | Yes | sc8830 HAL, speaker/headset routes | Legacy HAL adaptation | HIGH |
| Microphone | Yes | Built-in/back mic routes | Recording policy/HAL | HIGH |
| Wi-Fi | Yes | sprdwl; prior association evidenced | Driver/firmware + SELinux | HIGH |
| Bluetooth | Yes | Classic/BLE declared; currently off | Legacy bdroid/vendor integration | HIGH |
| Camera | Yes | 2 cameras, Sprd HAL1 | HAL1/blobs compatibility | HIGH |
| Accelerometer | Yes | K2HH STM, live reading | Legacy sensors HAL | MEDIUM |
| Other sensors | Partial | Grip + virtual orientation; no gyro/mag/light/prox | Feature parity limited | MEDIUM |
| Battery | Yes | Good, 81%, ~4.06 V | Charger/fuel-gauge integration | MEDIUM |
| Charging | Yes | USB detected; status readings inconsistent | Charger HAL/kernel validation | MEDIUM |
| USB | Yes | MTP+ADB functional | Legacy USB init/HAL | MEDIUM |
| Internal storage | Yes | 8 GB nominal; ~7.28 GiB eMMC | Tight data/system budgets | HIGH |
| SD card | Mountpoint only | Not mounted/verified | Optional expansion, vold compatibility | MEDIUM |
| SELinux | Yes | Enforcing on stock | New policy required | HIGH |
| Google Play Services | Yes | 23.45.23 ARM32, detected only | Heavy RAM/storage use | HIGH |
| Play Store | Yes | 39.7.34 ARM32, detected only | GMS certification/compatibility | HIGH |
| WebView | Yes | Chromium 95 ARM32 | Old engine; modern app/web compatibility | HIGH |
| Target app | No | NOT INSTALLED | ABI/codecs/WebView unknown | UNKNOWN |

## Manual tests required to complete the next part of Phase 1

1. Display: color, brightness, rotation, sleep/wake and visual corruption.
2. Touch/buttons: corners, edges, multitouch, Home/Back/Recent, volume and power.
3. Multimedia: known H.264 Baseline/Main/High samples at 480p/720p/1080p, VP8, audio sync, seeking and long playback; afterward repeat inside the target app if legitimately available.
4. Audio: speaker, headphone jack, volume, built-in mic recording/playback and Bluetooth audio.
5. Cameras: preview, focus, photo/video and front/rear resolution enumeration.
6. Wi-Fi: stable WPA2 connection, throughput, suspend/resume, 2.4/5 GHz detection and Wi-Fi Direct if needed.
7. Bluetooth: pairing with BLE/HID/A2DP devices and reconnect after sleep.
8. Sensors: rotate device and verify accelerometer/orientation; validate grip sensor behavior.
9. Storage: insert known-good microSD, confirm mount/read/write; test USB OTG separately.
10. Battery: observe charge from low level, current/temperature, discharge rate and sleep drain.
11. Google: open Play Store, verify account/login, update check, Play Protect certification and WebView rendering without changing packages.
12. Target app: obtain current Play Store requirements/version/ABI from an authoritative listing or install only in a later explicitly authorized phase, then test login-free launch, lesson media and audio.

## Evidence index

The original captures are in `raw/`. The reproducible query script is at `scripts/collect-phase1.ps1`. Key files include: `10-getprop-all.txt`, `20-proc-cpuinfo.txt`, `22-proc-version.txt`, `30-proc-meminfo.txt`, `43-proc-partitions.txt`, `45-dev-block-platform.txt`, `50-surfaceflinger.txt`, `65-media-camera.txt`, `66-sensorservice.txt`, `70-wifi.txt`, `80-battery.txt`, `90-pm-list-packages-f.txt`, `94-logcat-d.txt`, `95-dmesg.txt` and `96-media-codecs-xml.txt`.
