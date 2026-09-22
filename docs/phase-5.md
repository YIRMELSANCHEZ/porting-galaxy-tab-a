# Phase 5 -- Hardware bring-up

## Description

Progressive integration of drivers, HALs, firmware and blobs until the device's essential functions are
recovered.

## Goal

Achieve a stable ROM with the subsystems needed for everyday use and multimedia playback.

## Checks and steps

1. Boot, ADB, storage, applicable encryption and partition mounting.
2. Display, brightness, composition, rotation, touch and buttons.
3. GPU, EGL, gralloc, HWC and SurfaceFlinger stability.
4. Audio via speaker/jack/Bluetooth and microphone capture.
5. OMX/MediaCodec: H.264, VP8, audio, seeking, sync and long playback.
6. Wi-Fi, suspend, DHCP, WPA2, tethering only if in scope, and Wi-Fi Direct.
7. Classic/BLE Bluetooth, HID, A2DP and reconnection.
8. Rear/front cameras, preview, photo, video and autofocus.
9. Accelerometer, orientation and the other available sensors.
10. Battery, charging, temperature, deep sleep and idle consumption.
11. USB MTP/ADB/OTG and microSD.
12. SELinux enforcing and removal of denials via minimal rules.

## Exit criterion

Functional matrix with each component marked tested, partial or failed; no critical data, temperature or
stability failures.
