# V64 — Android 10 userspace suspend counter

Status: **OFFLINE VERIFIED; HARDWARE TEST PENDING**

## Root cause established by V63

The Android 10 service `android.system.suspend@1.0-service` was constructed with
`mUseSuspendCounter=false`. In that mode it exports Android wake locks through the kernel
wakelock interface but its autosuspend thread still writes `mem` to `/sys/power/state` every
100 ms. A modern kernel treats a failed suspend attempt independently from display state. The
SM-T280 3.10 kernel additionally maps every write to its legacy early-suspend state machine.

Consequently a wake lock prevented real system suspend, but did not prevent
`early_suspend` from switching off sprdfb, mip4 touch and the touch keys. V63's
`late_resume` was immediately undone by another `mem` write.

## Change

V64 enables the existing userspace wake-lock counter in SystemSuspend:

`true /* mUseSuspendCounter*/`

The autosuspend thread now waits until Android's counter reaches zero before writing `mem`.
While `PowerManagerService.Display` is held, no suspend request should reach the old kernel.
On screen-off Android releases the blocker and the normal legacy `early_suspend` can run. On
wake, V63 runs one complete `late_resume`; reacquiring the display blocker prevents the
100 ms thread from undoing it.

## Artifact

- Package: `sm-t280-phase6/packages/SM-T280-android10-suspend-counter-PHASE6-v64-DO-NOT-FLASH.tar.md5`
- Type: Odin AP, boot + system
- Boot: V63, unchanged
- Boot SHA-256: `e4641a1672e610aab448bb666678b43981116f271b2c373b9042ab14534fbf38`
- V64 suspend service SHA-256: `75f7d8f769168340ccf1e1db43aece0f4b07566911e405e15824b08d7fce7eb5`
- Legacy system SHA-256: `4d7ca49c63142f02e2f5d09a6b50609d1f99b7a86120321b0f7da705f28bdb8b`
- Package SHA-256: `297209ae12cd9061ee100518ab1aaba587e34071de5859016f941a19244b13f6`

The AP archive contains exactly `boot.img` and `system.img`. It contains no recovery, PIT, BL,
CP, CSC or modem image.

## Offline validation

- `V64_SYSTEM_SUSPEND_BUILD_PASS`
- V64 marker found in the installed service and generated `system.img`
- canonical Android 10 `sci-keypad.kl` from V62 present; obsolete `WAKE` flag absent
- `SYSTEM_BOOT_OFFLINE_VERIFY_PASS`
- `ODIN_SYSTEM_PACKAGE_PASS`
- `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`
- `V64_PACKAGE_PASS`

## Hardware test

Confirm each physical state with the user:

1. Flash V64 through Odin AP with Auto Reboot OFF and Re-Partition OFF.
2. Boot Android manually; confirm full boot, visible stable display and responsive touch.
3. Verify the V64 service marker and that the awake kernel log no longer receives a 100 ms
   storm of `request_suspend_state: sleep`.
4. Capture one short POWER press; confirm Android becomes Asleep and the display turns off.
5. Capture a second short POWER press; confirm display, changing frames and touch all recover.
6. Verify one `late_resume` sequence, `mip4_ts - Enabled`, no immediate `early_suspend`, and no
   continued blinking for at least 30 seconds.
