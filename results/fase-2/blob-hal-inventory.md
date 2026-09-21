# Phase 2 -- Blob and HAL inventory

The historical vendor contains 113 files, of which 95 are ARM little-endian ELF32. The reproducible detail
is in `sm-t280-phase2/analysis/vendor-elf-inventory.csv`.

| Subsystem | Evidence | Android 10 status | Risk |
|---|---|---|---|
| Camera | `camera.sc8830.so`, calibration and Samsung/SPRD libraries | Depends on binder, camera_client, gui/ui and old utilities | CRITICAL |
| Sensors | `sensors.sc8830.so` | Legacy HAL with old dependencies | HIGH |
| GPS | `gps.default.so`, `libwrappergps.so` | Legacy ICU/RIL/SQLite/framework dependencies | HIGH |
| Audio | Samsung/SPRD blobs and config; part of the HAL is in the source tree | Requires adapting policies and ABI | HIGH |
| Video | Hardware and software OMX H.264/MPEG4/VP8 | Requires an OMX/Stagefright port; execution not tested | CRITICAL |
| Wi-Fi/BT | SC2331 firmware, `libbt-vendor` and Marlin code | A base exists, but the APIs are 7.1-era | HIGH |
| Graphics | HWC/gralloc can be built from `hardware/sprd` | `libGLES_mali.so` is missing in this vendor | CRITICAL |

The `proprietary-files.txt` explicitly comments out `lib/egl/libGLES_mali.so` and
`lib/hw/gralloc.sc8830.so`; the vendor repository does not contain the Mali blob. Integrity, permitted
redistribution or Android 10 compatibility must not be assumed until the exact set from the AQJ1 firmware is
inventoried via an authorized, traceable procedure.
