# SM-T280 port -- final state -- closeout 2026-09-21

Closeout document: decision, progress record, pending items and the factory-restore procedure.
For the technical detail of each point, follow the links to `fase-6/`.

## Decision

**Migration stopped on 2026-09-21 by user decision.** Reason: the device has reached its useful ceiling.
Android 10 boots with almost all the hardware working, but the two remaining goals hit hardware or gralloc
porting limits, not more tweaks:

1. The target app works but is GPU-limited (GLES 3.0 emulated on the CPU), measured and with no margin.
2. The camera preview is blocked by a Spreadtrum gralloc bug on Android 10, which is separate research
   work with reflashes and an uncertain outcome.

The decision is to record everything, version it in git and **restore the tablet to its original Samsung
firmware**.

## Progress record (what was achieved)

A chain of ~99 iterations (V1...V99). Milestones per subsystem:

| Area | Result | Reference |
|---|---|---|
| Android 10 recovery on hardware | validated (V21) | fase-4 |
| Android 10 boot (system-as-root, fstab, binder, HIDL graphics) | stable | fase-5 |
| Power button / suspend / power off | sprdfb panel bug (no resume on A10) fixed | [gtexa-power-button-real-cause] - fase-6/POWER-BUTTON-FINDINGS.md |
| Wi-Fi + Bluetooth coexisting (Marlin/wcnd chip) | works (V70-V72, V89-V90) | fase-6/BLUETOOTH-FINDINGS.md, V89-WIFI-START-RECOVERY.md |
| Display performance (OSD/DISPC cap) | removed (V76) | fase-6/G1-FINDINGS.md |
| GLES 3.0 in software (SwiftAngle = SwiftShader as ANGLE driver) | works (V77-V88) | fase-6/V87-CLEAN-WIFI-ANGLE.md, V88-SWIFTANGLE-SCALED-EGL.md |
| Hardware H.264 video (OMX.sprd.h264.decoder) | works (V94b); NV12 in SwiftShader (V94) | fase-6/BUILD-V96-FINAL.md |
| Camera: HAL working, 2 cameras | works (V92 + V98) | fase-6/CAMERA-V98.md |
| Google Play Services via microG | integrated (V99), native LineageOS signature spoofing | fase-6/BUILD-V96-FINAL.md |
| Final general-purpose package | `...PHASE6-v96` | fase-6/BUILD-V96-FINAL.md |

## Pending items (recorded, will not be tackled)

### Blocking for a "100% functional tablet"
- **CAM2 -- camera preview**: HAL OK, but the Spreadtrum gralloc rejects the preview buffers (API1:
  `allocator@2.0` returns EINVAL for NV21 usage `0x24000930`; camera2-legacy: ION NO_RESOURCES for RGBA
  usage `0x702`). It affects every app. Leads to resume it in
  [fase-6/CAMERA-V98.md](fase-6/CAMERA-V98.md) (preview section). High difficulty, requires rebuilding and
  reflashing the gralloc/allocator.

### One-time configuration (no reflash needed)
- **microG**: open "microG Settings", check the self-check (signature spoofing green), enable device
  registration and Cloud Messaging, grant permissions. Detail in fase-6/BUILD-V96-FINAL.md section 3.
- **Cleaning up the ANGLE setting**: the tablet keeps the ANGLE opt-in in `/data`
  (`settings delete global angle_gl_driver_selection_pkgs` and `..._values`). Irrelevant if it is restored
  to factory.

### Minor (low priority, see fase-6/TODO-ANALYSIS.md)
- **MED1**: `_size`/dimensions of new captures are not filled in until a MediaStore scan.
- **GAL1**: gallery sorts by name, not by date.
- **SEC1**: PIN/pattern falls into keystore (`KeyPermanentlyInvalidatedException`), not gatekeeper; not
  touched. **Warning**: never remove a PIN by editing `locksettings.db` (leaves an orphan SP -> bootloop).
- **Battery saver**: verify with the USB cable disconnected.
- **Thermal HAL** absent (the kernel throttles on its own). Optional.

### Closed / out of scope
- **Vibrator**: the SM-T280 has no motor (DTS/defconfig). Closed.
- **GNSS/GPS, Widevine, generic OMX SW video**: deferred unless the app needs them.

## Restore to factory

The original Samsung firmware (Android 5.1.1, build **T280XXU0AQJ1**, the same one it shipped with) is in
`sm-t280-phase4/stock/extracted/`:

| Odin slot | File |
|---|---|
| BL | `BL_T280XXU0AQJ1_..._user_low_ship.tar.md5` |
| AP | `AP_T280XXU0AQJ1_..._user_low_ship.tar.md5` (2.0 GB) |
| CSC | `CSC_UVS_T280UVS0AQJ1_..._user_low_ship.tar.md5` |

There is no CP (the SM-T280 is Wi-Fi only, no modem). Procedure (performed by the user):

1. Power off the tablet and enter **Download Mode** (Vol-Down + Home + Power, then Vol-Up).
2. In Odin load each file into its slot: **BL**, **AP**, **CSC** (use CSC, not HOME_CSC: the plain CSC
   does the wipe and returns the tablet to full factory state).
3. Odin options: **Auto Reboot ON**, **Re-Partition OFF**, F. Reset Time default.
4. Press Start. The AP takes several minutes. When it finishes, the tablet reboots into the original
   Android 5.1.1 and performs the data wipe from the CSC.

This returns the original software and configuration and erases everything from the port. It is reversible
by reflashing LineageOS (the V96 package) if desired.

## Traceability notes

- Project memory (workflow, gotchas, state): `[gtexa-build-flash-workflow]` and related.
- Each `Vnn` has its `scripts/apply-vNN-*.py` and, in most cases, a note in `results/fase-6/`.
- The OAuth secret the app dumped into logcat stayed only in the session scratchpad; it was **not**
  propagated into this documentation.
