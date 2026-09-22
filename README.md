# LineageOS 17.1 (Android 10) port for the Samsung Galaxy Tab A 7.0 2016 (SM-T280)

![License](https://img.shields.io/badge/license-MIT-yellow)
![Android](https://img.shields.io/badge/Android-10-3DDC84?logo=android&logoColor=white)
![LineageOS](https://img.shields.io/badge/LineageOS-17.1-167C80)
![Device](https://img.shields.io/badge/device-SM--T280%20gtexswifi-1f6feb)
![SoC](https://img.shields.io/badge/SoC-Spreadtrum%20SC8830-lightgrey)
![GPU](https://img.shields.io/badge/GPU-Mali--400%20GLES2-e05d44)
![Status](https://img.shields.io/badge/status-discontinued%20%C2%B7%20documented-orange)
![Last commit](https://img.shields.io/github/last-commit/YIRMELSANCHEZ/porting-galaxy-tab-a)
![Top language](https://img.shields.io/github/languages/top/YIRMELSANCHEZ/porting-galaxy-tab-a)
![Repo size](https://img.shields.io/github/repo-size/YIRMELSANCHEZ/porting-galaxy-tab-a)

> *Documented, reproducible port of Android 10 to a 2016 Spreadtrum tablet Samsung left on Android 5.1.1 — boots to the launcher with almost all hardware working.*

Full record of the Android 10 port for the **Samsung Galaxy Tab A 7.0 2016 (SM-T280, `gtexswifi`)**,
a Spreadtrum SC8830 device (4x Cortex-A7 1.3 GHz, Mali-400 GLES 2.0 GPU, 1.5 GB RAM, kernel 3.10) that
Samsung left on Android 5.1.1. Initial goal: run an educational app that requires GLES 3.0. Final goal
after the evidence: leave a usable general-purpose tablet.

**Status: migration stopped on 2026-09-21 by user decision.** Summary of why and of what was achieved
below; the detail and the pending items in [results/ESTADO-FINAL.md](results/ESTADO-FINAL.md).

## What was achieved

Android 10 boots stably on a 2016 device with almost all the hardware working:

| Subsystem | Status |
|---|---|
| Boot, display (180 rotation), touch | works |
| Wi-Fi + Bluetooth (coexistence on the Marlin chip) | works |
| Power button / suspend / power off | works (sprdfb panel bug fixed) |
| Storage, camera HAL (2 cameras), microphone | works |
| Hardware H.264 video (Spreadtrum OMX) | works |
| GLES 3.0 in software (SwiftAngle / SwiftShader) | works for apps that require it |
| App store (Aurora) + Google apps via **microG** | works (microG initial setup required) |
| The target app | launches and is usable, but GPU-limited (measured) |

## What was not achieved (real limits)

- **Camera preview**: the HAL works, but the graphics layer (Spreadtrum gralloc on Android 10) rejects
  the preview buffers. It affects every camera app. It is a gralloc porting bug, not a HAL bug. See
  [results/fase-6/CAMERA-V98.md](results/fase-6/CAMERA-V98.md).
- **Heavy 3D performance**: the Mali-400 is GLES 2.0 in silicon; apps that require GLES 3.0 run on the
  CPU (SwiftShader), at a few fps. It is a physical limit, not a software one.

## How it is organized

- **`docs/`** -- procedures and the phase plan (reusable, not specific to this tablet).
- **`results/`** -- measurements, reports and findings per phase (`fase-1` ... `fase-6`) plus the closeout.
  - `results/ESTADO-FINAL.md` -- final state, decision and pending items.
  - `results/fase-6/` -- the long phase: graphics/video bring-up, SwiftAngle, camera, microG, the app.
- **`sm-t280-phase6/scripts/`** -- all the patches (`apply-vNN-*.py`) and the build/packaging scripts.
- **`sm-t280-phase4/stock/`** -- original Samsung firmware (T280XXU0AQJ1) for the factory restore.

Heavy binaries (`*.tar.md5`, `*.img`, APKs, blobs, source trees) are **not** versioned in git; see
`.gitignore`. The repository keeps the reproducible knowledge: documentation and scripts.

## Reproducing the port

Environment: WSL Ubuntu 22.04, LineageOS 17.1 tree at `/home/lineage/android/lineage-17.1`, device tree
`device/samsung/gtexswifi`. The final package is produced by `sm-t280-phase6/scripts/build-v96-final.sh`
(it applies the chain `apply-v87` ... `apply-v99` on the tree and packages for Odin). Flashing: Odin AP,
**Auto Reboot OFF, Re-Partition unchecked**, `boot` + `system` only. Detail and sha256 in
[results/fase-6/BUILD-V96-FINAL.md](results/fase-6/BUILD-V96-FINAL.md).

## Restoring the tablet to factory (original Android 5.1.1)

The original firmware is in `sm-t280-phase4/stock/` (`AP/BL/CSC_...AQJ1...`). Full restore via Odin with
BL + AP + CSC, which returns the original software and wipes the data. Procedure in
[results/ESTADO-FINAL.md](results/ESTADO-FINAL.md#restore-to-factory).
