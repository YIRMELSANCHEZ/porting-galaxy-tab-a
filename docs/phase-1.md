# Phase 1 -- Non-destructive technical analysis

## Description

Read-only audit of the device and the original firmware via ADB. Establishes a verifiable baseline before
considering any modification.

## Goal

Confirm the exact variant, characterize hardware/software and issue a preliminary feasibility assessment
for Android 10 / LineageOS 17.1 and the target app.

## Checks and steps

1. Prepare the official Android Platform Tools and verify the authorized ADB connection.
2. Confirm model, codename, product, board, SoC and Wi-Fi/LTE variant.
3. Collect Android version, build, firmware, bootloader and security patch.
4. Identify CPU, architecture, ABI, cores and ARM extensions.
5. Audit the kernel, modules, accessible config and exposed device tree.
6. Measure RAM, swap/ZRAM and memory pressure.
7. Inventory storage, filesystems and partition map without copying blocks.
8. Determine Treble, A/B, Virtual A/B and dynamic partitions.
9. Enumerate display, touch, GPU, EGL, OpenGL ES and compositor.
10. Inventory codecs, OMX, multimedia acceleration and declared limits.
11. Enumerate audio, microphones, cameras and sensors.
12. Audit Wi-Fi, Bluetooth, battery, thermals, power management and USB.
13. Review SELinux, security properties and Android features.
14. Inventory Play Store, Google Play Services, GSF, WebView and the target app.
15. Capture finite logcat/dmesg snapshots and summarize relevant errors.
16. Produce a risk matrix, missing information and pending manual tests.

## Exit criterion

Enough evidence is available to decide whether the port is worth investigating. Nothing is flashed,
installed, rooted, unlocked or rebooted into special modes.
