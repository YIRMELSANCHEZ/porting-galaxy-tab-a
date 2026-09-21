# Phase 6 -- Android, Google and target-app validation

## Description

Stability, performance and compatibility testing of the target application on the candidate ROM.

## Goal

Determine whether the port offers a safe and sufficiently stable experience for an app that requires
GLES 3.0.

## Checks and steps

1. Measure boot, memory, LMK, temperature, battery life and sustained stability.
2. Run CTS/VTS or applicable subsets and document exceptions due to legacy hardware.
3. Validate WebView, TLS, certificates, date/time, DNS and browsing.
4. Choose, with authorization, a minimal and compatible ARM32 GApps distribution.
5. Verify Play Services, Play Store, login, sync and certification.
6. Obtain the target app from a legitimate source and record version, ABI and requirements.
7. Test install, launch, authentication without inspecting credentials, authorized download and lesson
   playback.
8. Test video, audio, seeking, fullscreen, suspend/resume and headphones.
9. Capture failures with logcat and metrics without collecting personal data.
10. Repeat tests after reboots and idle periods.

## Exit criterion

`PASS / PARTIAL / FAIL` report for the target app and the overall experience, with reproducible defects
and enough metrics to decide.
