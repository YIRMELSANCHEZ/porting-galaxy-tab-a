# V63 — Complete legacy late-resume

Status: **HARDWARE TESTED; REJECTED DUE TO RESUME/SUSPEND OSCILLATION**

## Evidence from V62

V62 fixed the physical POWER mapping. Android slept and woke for the first time through the
physical key, but wake restored only the framebuffer:

- `early_suspend` powered off `mip4_ts`, touchkey and sprdfb.
- Android logged `WAKE_REASON_POWER_BUTTON` and SurfaceFlinger changed power mode to ON.
- The legacy kernel did not log or execute `late_resume`.
- V61's deferred worker directly powered sprdfb on.
- Touch remained disabled and `/dev/input/event3` produced no events.
- The visible frame was frozen and DISPC later logged `BIT_DISPC0_EB still set`.

## Change

The deferred V61 worker now requests `PM_SUSPEND_ON` through the kernel's legacy
`request_suspend_state()` API. That queues the normal `late_resume` work and resumes every
registered handler in reverse order, including display, touchscreen and touch keys.

The fallback direct framebuffer resume remains only for the exceptional case where the legacy
suspend state is already ON while the framebuffer is disabled.

## Artifact

- Package: `sm-t280-phase6/packages/SM-T280-android10-full-late-resume-PHASE6-v63-DO-NOT-FLASH.tar.md5`
- Type: Odin AP, boot-only
- Boot SHA-256: `e4641a1672e610aab448bb666678b43981116f271b2c373b9042ab14534fbf38`
- Package SHA-256: `98daf85f0e27514a2e71c2301edc5ebecc2f27bb4ee4b10dc1f0818ba6b87094`

The archive contains exactly `boot.img`. It contains no system, recovery, PIT, BL, CP, CSC or
modem image.

## Offline validation

- Kernel rebuilt with GCC 4.8 and the existing gtexswifi configuration.
- Samsung boot image regenerated with the project mkbootimg, DT combiner, header insertion and
  signing rules.
- V63 diagnostic strings are present in the compiled kernel.
- V63 boot differs from V61.
- `V63_BOOT_BUILD_PASS`
- `ODIN_BOOT_ONLY_PACKAGE_PASS`
- `V63_BOOT_ONLY_PACKAGE_VERIFY_PASS`

## Hardware test

Confirm every physical state with the user instead of inferring it:

1. Flash the boot-only AP with Auto Reboot OFF and Re-Partition OFF.
2. Manually boot Android and confirm full boot, display ON and responsive touch.
3. Verify V63 kernel string and loaded V62 keylayout by read-only ADB.
4. Capture one short POWER press; confirm display OFF and Android Asleep.
5. Capture a second short POWER press; confirm display ON, changing frame and working touch.
6. Verify `late_resume: call handlers`, `mip4_ts - Enabled`, and absence of a new
   `BIT_DISPC0_EB still set` after the cycle.

## Hardware result (2026-09-20)

V63 boots Android completely and the first POWER press works correctly:

- input: one clean `KEY_POWER DOWN/UP` pair;
- framework: `Going to sleep due to power_button`;
- power state: `Asleep`, display `OFF`.

The second press also reaches Android and starts the intended full resume:

- `WAKE_REASON_POWER_BUTTON`;
- `V63 requesting full late_resume`;
- `late_resume: call handlers`;
- `mip4_ts - Enabled` and touchkey resume.

However, `android.system.suspend@1.0-service` continues writing `mem` to
`/sys/power/state` every approximately 100 ms while Android is interactive. On this legacy
kernel every write also drives `request_suspend_state()`. The first new write arrived while
the V63 resume handlers were still running (`sleep (0->3)`), queued `early_suspend`, disabled
the touchscreen again and powered the panel off. Subsequent framebuffer updates repeated the
cycle, producing visible blinking.

The framework itself remained healthy (`mWakefulness=Awake`, display state `ON`). Therefore
V63's complete handler sequence is valid, but it cannot coexist with the Android 10 suspend
service in its default kernel-wakelock mode. V64 addresses that compatibility boundary.
