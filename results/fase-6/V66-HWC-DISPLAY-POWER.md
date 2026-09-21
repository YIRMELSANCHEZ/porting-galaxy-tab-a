# V66 -- physical off/on from the HWC power mode

Status: **DISCARDED ON HARDWARE; HWC1 PATH NOT USED. REPLACED BY V67**

The test showed the V66 kernel was loaded, but no V66 marker appeared. The real Composer uses
`libhwc2onfbadapter.so`, not `hwcomposer.sc8830.so`; the framebuffer adapter ignored `setPowerMode`. The
fix was moved to the real path in V67.

## Problem it solves

V64 left the POWER -> off -> POWER -> on sequence stable and recovered touch, but the physical panel
power-off was still tied to `early_suspend`. Android marked the display as `OFF` in tens of milliseconds,
while the backlight could stay on for roughly 1 to 3.4 seconds until other wakelocks disappeared.

There was also a mandatory race: if POWER was pressed again during that window, a deferred power-off must
not run after the wake and blank the panel again.

## Authoritative signal found

The Spreadtrum HWC already translates the SurfaceFlinger transitions and synchronously sends the
`SPRD_FB_SET_POWER_MODE` ioctl to the framebuffer:

- `SPRD_FB_POWER_OFF` for screen off;
- `SPRD_FB_POWER_NORMAL` for screen on;
- `DOZE` and `SUSPEND` for the other HAL-defined modes.

The stock driver received the ioctl, printed the value and performed no action. That is why the framework
finished quickly but the panel waited for `early_suspend`.

## V66 change

File modified in the Android tree:

`kernel/samsung/gtexswifi/drivers/video/sprdfb/sprdfb_main.c`

New behavior:

1. `OFF` and `SUSPEND` synchronously call `sprdfb_power(dev, 0)`. When the ioctl returns, the panel is
   already off. No power-off timer or worker is created.
2. `NORMAL` and `DOZE` check the legacy state. If a suspend was requested, they call
   `request_suspend_state(PM_SUSPEND_ON)` before turning on.
3. They then call `sprdfb_power(dev, 1)` and refresh the framebuffer.
4. Unknown values return `-EINVAL` and a copy-from-userspace failure returns `-EFAULT`.
5. `sprdfb_power()` keeps its mutex and idempotent check, serializing concurrent transitions with
   `early_suspend`/`late_resume`.

## OFF -> ON race coverage

The power-off leaves no deferred work, so there is no stale OFF operation able to run after ON. On wake:

- if `early_suspend` was still queued, the switch to `PM_SUSPEND_ON` makes it abort;
- if its handlers were already running, the full `late_resume` is queued;
- even if the framebuffer handler races with the ioctl, the mutex serializes both and the later
  `late_resume` leaves panel and touch active as the final state.

V63 is kept as a fallback to recover the full set of handlers and V64 so SystemSuspend does not request
`mem` again while Android holds the display wakelock.

## Artifact

- Odin AP package: `sm-t280-phase6/packages/SM-T280-android10-display-power-mode-PHASE6-v66-DO-NOT-FLASH.tar.md5`
- Exact content: only `boot.img` (KERNEL partition)
- Boot SHA-256: `5907fe4871e3da25e15bdf18050c55cdc83dd39b583179473963e52a026c7b69`
- Package SHA-256: `725b8275c7a10d9eeb4cf3f94ca1392d8d8419f31ca2ecd577ce3cdfd049c187`
- Embedded Odin MD5: `42e320908de63ac08163b8071bd96684`
- Boot size: `12954804` bytes; verified partition margin: `3822412` bytes
- Kernel: `Linux 3.10.108-g95996f39350-dirty`, GCC 4.8

## Offline validation passed

- `V66_BOOT_BUILD_PASS`
- V66 markers present in the generated kernel
- `ODIN_BOOT_ONLY_PACKAGE_PASS`
- `V66_BOOT_ONLY_PACKAGE_VERIFY_PASS`
- AP contains exactly `boot.img`, no system, recovery, PIT, BL, CP, CSC or modem
- boot extracted from the AP byte-for-byte identical to the compiled one
- Samsung/SEAndroid tag present
- `SYSTEM_BOOT_OFFLINE_VERIFY_PASS` for the current set

The generic verifier showed two `WARN`s when literally searching for the version strings inside `boot.img`;
the direct check on the embedded kernel did find: `Linux version 3.10.108-g95996f39350-dirty ... gcc
version 4.8`.

## Physical test pending

Do not assume any state. Before flashing, ask for explicit confirmation of:

- the tablet's current mode;
- whether the screen is on/off and stable;
- whether touch responds;
- whether the POWER button responds;
- whether Odin detects the port.

After the boot-only flash, validate separately:

1. full boot, stable screen and working touch;
2. normal OFF and immediate physical power-off;
3. normal ON, changing frames and working touch for at least 30 seconds;
4. fast OFF -> ON at about 100, 300 and 700 ms;
5. repeat from lock and from an unlocked session;
6. wait at least 5 seconds after each race to rule out a late OFF;
7. check in `dmesg` the V66 markers, the suspend cancellation when applicable and the absence of
   `early_suspend`/`late_resume` loops.

Until these tests are complete, V66 is an offline candidate and is not declared a definitive physical fix.
