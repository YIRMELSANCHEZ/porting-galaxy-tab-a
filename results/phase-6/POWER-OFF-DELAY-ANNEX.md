# Annex -- ~1s delay when turning the screen OFF (post V62/V63/V64) + V65 attempt (reverted)

For the agent that implemented V62-V64. Documents the diagnosis of the power-off delay, the V65 attempt
(kernel-level Option A) and why it did NOT work, with measured evidence. V65 is **reverted** in the tree
(clean source, V63/V64 state). Goal: for you to integrate the fix into your design.

Date: 2026-09-20.

## 1. Symptom
With V62(keylayout)+V63(late_resume)+V64(suspend counter): turning on/off with the button WORKS. Only
nuisance: when **turning it off again** there is a ~1s delay (the screen stays on and then turns off). Key
user lead: **it only happens if the tablet is UNLOCKED**; from the lock screen the power-off is instant.

## 2. Diagnosis (measured on HW)
- The **framework decides to turn off quickly**: `powerPress` -> `Going to sleep` (~125 ms after the key),
  `Blocking screen off` -> `Unblocked screen off after 0 ms`, SurfaceFlinger `Setting power mode 0` ->
  `Finished` in ~40 ms. That is, the framework side does NOT have the delay.
- The button event is clean in the kernel: getevent DOWN->UP ~171 ms; IRQ 422 rises. It is not the ISR.
- **The delay is that the BACKLIGHT and the PANEL stay on** until `sprdfb_early_suspend` ->
  `sprdfb_panel_suspend` runs. Measured: after the off command, the `early_suspend` runs at **+1.19s
  (injected) / +3.4s (physical with more wakelocks)**. Correlation (injected): OFFCMD uptime 185.19 ->
  `early_suspend: calling sprdfb_early_suspend` at 186.385.
- **`/sys/class/backlight/panel/actual_brightness` stays at 143** for that whole time after pressing off
  (sampled ~0.7s, constant 143). That is: the framework does NOT write brightness 0 to the backlight; the
  backlight only turns off when the panel enters early_suspend.
- **Color fade RULED OUT**: `mColorFadeEnabled=false` in dumpsys display. It is not the animation.
- **Root cause**: the backlight/panel power-off is **coupled to early_suspend**, which only fires when the
  system manages to suspend = **when all wakelocks are released**. Unlocked there are MORE wakelocks
  (foreground app, etc.) -> early_suspend takes longer -> hence the "only unlocked". (Contributors:
  `wake_lock_timeout(&keypad_wake_lock, HZ*1)` = 1s per press in the ISR; WiFi `setSuspendModeEnabled`
  retries; the V64 wakelock counter.)
- Asymmetry with your fix: V63 **decoupled the TURN-ON** (forces `request_suspend_state(PM_SUSPEND_ON)`
  promptly). The **TURN-OFF** is still built on the late early_suspend.

## 3. V65 attempt (kernel-level Option A) -- DID NOT WORK, reverted
- File: `drivers/video/backlight/gen_panel/gen-panel-bl.c` (built-in, CONFIG_GEN_PANEL_BACKLIGHT=y). Chosen
  to NOT collide with your changes in sprdfb_main.c.
- Idea (mirror of V63): in `gen_panel_backlight_update_status`, if `brightness==0` and
  `get_suspend_state()==PM_SUSPEND_ON`, trigger via a worker `request_suspend_state(PM_SUSPEND_MEM)` ->
  prompt early_suspend -> panel/backlight off immediately.
- **Why it failed**: the `brightness==0` condition **is never met in time**, because the framework does NOT
  write brightness 0 to the backlight on off (actual_brightness stays at 143 until panel_suspend). So the
  hook does not fire. Verified: V65 boot correctly flashed (KERNEL partition hash =
  f64aaf16c0030a995085bf9096bfa3140c0ad395122a3d7ae981845a8a3293fd) but early_suspend was still at +1.19s.
- V65 **reverted** in the tree (scripts: apply-v65-prompt-panel-off.py / revert-v65-prompt-panel-off.py).
  The V65 boot flashed on the device is inert (the hook does not fire); you can go back to boot V63
  (e4641a16) by reflashing, no urgency.

## 4. Where the real problem is for the fix (recommendation, you decide)
The prompt power-off needs to **turn off the backlight/panel when the screen-off order is received,
decoupled from suspend**. Routes:
- **(A-framework, recommended)**: have the framework turn off the backlight immediately on entering
  screen-off (write brightness 0 to `/sys/class/backlight/panel/brightness` promptly, or blank promptly),
  instead of leaving it to panel_suspend. It is a system.img change and fits your area (V64 already touches
  the framework/SystemSuspend). Note: writing 0 to `/sys/class/backlight/panel/brightness` live DOES turn
  off the backlight (tested), so the sysfs path works; the problem is that the framework does not do it
  early on screen-off.
- **(A-kernel)**: there is no reliable "display off" signal that reaches the kernel early on this device
  (the HWC blob's blank does NOT reach `sprdfb_blank`; the framework does not write brightness 0 early).
  That is why the kernel hook (V65) had no signal. A kernel route would be to hook the signal that does
  exist (e.g. when the HWC does its ioctl), but it was not confirmed that it arrives.
- **(partial)**: reducing `wake_lock_timeout(&keypad_wake_lock, HZ*1)` to a few ms trims ~1s, but does NOT
  fix the unlocked case (other wakelocks dominate) -- insufficient alone.

## 5. Useful diagnostic commands
- Framework timing: `logcat -v threadtime PowerManagerService:V PhoneWindowManager:V '*:S'`
- Kernel panel-off timing: `dmesg | grep -iE 'early_suspend: calling sprdfb|panel_suspend'` (correlate
  uptime with wall via `cat /proc/uptime` + `date`).
- Physical backlight: sample `cat /sys/class/backlight/panel/actual_brightness` during the off.
- Color fade: `dumpsys display | grep -i ColorFade`.
- Verify the flashed boot: `dd if=/dev/block/platform/sdio_emmc/by-name/KERNEL bs=<boot.img size> count=1 |
  sha256sum` (KERNEL = boot partition; SYSTEM = system).
- Force backlight on/off live (test): `echo 0|4 > /sys/class/graphics/fb0/blank`.

## 6. Mandatory race: logical OFF followed by POWER before the physical OFF

The interval must also be covered in which Android has already processed `Going to sleep` and considers the
display `OFF`, but the backlight and the panel are still physically on because `early_suspend` has not run.

If the user presses POWER again within that window:

- the second press must be interpreted as a wake;
- any pending physical power-off must be canceled or invalidated;
- an old power-off worker must not run after the wake and blank the panel again;
- the final state must be Android `Awake`, logical display `ON`, panel stable, image refreshing and touch
  working;
- no late `early_suspend` cycle must appear after that press's `late_resume`.

The next fix must use authoritative state and a cancelable generation/sequence for the deferred operations,
or run the blank synchronously in the logical transition to OFF. Firing a power-off worker without
re-checking that the desired state is still OFF is not enough.

Minimum physical tests, always confirming the visible state with the user:

1. Normal OFF, wait for the full physical power-off and then POWER to wake.
2. OFF followed by POWER about 100 ms later, before the physical power-off.
3. Repeat with intervals of about 300 ms and 700 ms.
4. Repeat from lock and from an unlocked session.
5. After each case, wait at least five seconds to detect a residual deferred power-off and check touch
   response.
