# SM-T280 Android 10 -- Known issues (backlog, non-urgent)

Record of failures observed by the user / diagnosis, to be fixed without rush. State at V56. Priority and
indicative notes (probable cause) for when they are tackled.

## Open

| # | Issue | Symptom | Probable cause (unconfirmed) | Priority |
|---|-----------|---------|--------------------------------|-----------|
| G1 | Graphics performance | Display capped at ~8fps globally (UI and video stutter) | The SPRD HWC composes on the GPU and dumps via CPU (memcpy in fb_post), with no DISPC/GSP overlays or page-flip. See graphics-8fps-DIAGNOSIS.md | HIGH (user priority) |
| R1 | Screen rotation | Auto-rotate does not work even when the option is enabled | Missing/incomplete sensors HAL (android.hardware.sensors): the accelerometer does not reach the framework -> WindowManager does not rotate. The "accelerometer_sensor" input exists but probably without the sensors HIDL HAL wired | MEDIUM |
| S1 | Screenshots | Taking a screenshot does not save | Probable failure writing to /data/media (MediaProvider/storage) or a permission/SELinux issue in the screenshot service; check logcat of com.android.systemui / MediaProvider when capturing | LOW |
| V1 | HW video | Hardware video codecs (OMX.sprd.*) disabled (5.1 blobs, ABI-incompatible) | No Android 10 blobs for the chip; software decode only (V55). HW unfeasible unless the blobs are ported | LOW (accepted) |
| A1 | audioserver at boot | Transient keystore/audio crash at boot (historical) | Boot restarts already stabilized; watch if it reappears | INFO |
| W1 | WiFi 5GHz | 5GHz networks do not appear | The sc2331 chip is 2.4GHz only (hardware) | CLOSED (not applicable) |

## P1 -- Power button / wake (RESOLVED in V59 - permanent wakelock, VERIFIED ON HW)
V59 (flashed candidate): init.board.rc 'on boot' holds a permanent partial wakelock
(/sys/power/wake_lock "gtex_power_wake") -> the system does NOT enter mem-suspend -> the power key WAKES
the off screen. Decisive test on hardware (V58 + runtime wakelock "mywake"): baseline IRQ 422=56, Display
OFF/Asleep -> after 5 presses IRQ=66 (+10), Display ON/Awake. DEFINITIVE root cause (corrects the previous
"event delivery" diagnosis): it was NOT the ISR or evdev; it was Android's MEM-SUSPEND (autosleep)
swallowing KEY_POWER in the suspend<->resume transition. The IRQ did arrive (V58 ungates it from the SPRD
light-sleep), but the event did not survive the resume. Preventing mem-suspend (wakelock) fixes it
reliably. The screen still turns off (the backlight is saved); only the CPU stops suspending. SELinux
Permissive -> init writes the node without blocking. V55(WAKE kl)/V56/V57/V58 are kept. TRADE-OFF: worse
standby (accepted by the user: "it doesn't matter how smooth the video is if I can't turn the tablet on
once it's off"). Fine backlog: the "good" fix = keep mem-suspend and arm the EIC wake in the PMIC (SPRD
ADI), hardware-deep and uncertain; with V59 it is no longer needed.

## P1-HISTORICAL-2 -- V58 investigation (PARTIAL; superseded by V59)
Progress but NOT fully resolved. Two layers:
 (1) IRQ GATING [FIXED by V58]: the SPRD LIGHT-SLEEP (cpuidle-scx35, light_sleep_en=1) pauses the AP
     subsystem (incl. ADI/PMIC) when the screen goes off -> previously the power IRQ (422 irq-a-eic) did
     NOT arrive (the counter did not rise). V58 sets light_sleep_en=0 -> NOW the IRQ does fire with the
     tablet asleep (the counter rises). Good side effect: a smoother system. Trade-off: worse standby.
 (2) EVENT DELIVERY [PENDING, DEEP]: with V58, pressing POWER while asleep the IRQ 422 rises
     (+2/press) and BatteryStats logs "resumed from suspend", BUT the KEY_POWER event does NOT reach
     userspace (getevent /dev/input/event1 = 0 lines) or the framework (no InputDispatcher/
     PhoneWindowManager/PowerManager logs) -> the display does NOT turn on. The device does deep-suspend
     (and USB resumes it in a loop). KEY_POWER is lost in the suspend<->resume transition: the ISR
     sci_powerkey_isr does input_report_key + wake_lock_timeout(1s), but evdev/InputReader do not pick it
     up after the resume.
Next (backlog): investigate why evstate/evdev does not deliver KEY_POWER on resume (input core
 suspend/resume, or the fragile ISR logic with irq_set_irq_type LEVEL toggling and the inverted value).
 Possible routes: report the key with a proper wakeup_source/pm_wakeup_event; review evdev suspend; or
 avoid deep-suspend (autosleep off) at the cost of battery. The changes
 V55(WAKE kl)/V56(enable_irq_wake)/V57(irqchip set_wake)/V58(light_sleep off) are kept. Current
 workaround: screen_off_timeout=30min + stay_on(USB)=7.

## P1-HISTORICAL -- investigation (V55->V57, for reference)
Symptom: neither POWER nor HOME wakes the tablet when the screen is off (unplugged it stays unusable until
reboot). Current workaround: screen_off_timeout=30min + stay_on_while_plugged_in=7 (with USB it does not
turn off).
Diagnosis (V55->V57, definitive):
- V55 added WAKE to the keylayout (POWER), V56 enable_irq_wake(PB_INT) in sci_keypad_suspend, V57
  .irq_set_wake in a_eic_irq_chip/d_eic_irq_chip (gpio-eic.c). NONE fixes it.
- The device does NOT enter PM suspend (dmesg without "PM: suspend"); it only turns the screen off
  (mWakefulness=Asleep) and enters a light SPRD sleep (cpuidle deep sleep).
- With the screen off, hammering POWER does NOT increment the IRQ 422 counter (irq-a-eic powerkey) -> the
  analog EIC interrupt does NOT reach the kernel: it is MASKED/gated in that state. (Awake it does work:
  it turns the screen off.)
- Root cause: in the SPRD deep-sleep, the PMIC's analog/EIC domain (ADI) is gated. For the power key to
  wake, the EIC WAKE must be configured IN THE PMIC (ADI/ANA_EIC registers), not only the Linux
  enable_irq_wake. sci_gpio_irq_set_wake is a stub (return 0) that writes no PMIC register -> Linux thinks
  the wake is armed but the PMIC is not. The real wake arm in the PMIC EIC is missing (or the a-eic domain
  gating in deep sleep must be avoided). It is SPRD-specific and complex (PMIC register map).
Next step (when resumed): study drivers/mfd/sprd/adi + the deep sleep code (arch/arm/mach-sc / sprd pm)
for the EIC wake arm in the PMIC; or force the a-eic not to be gated. The V56/V57 changes are harmless
(they leave Linux prepared), and are kept.

## Resolved
- Boot to launcher, WiFi 2.4GHz + internet, Mali-400 GPU (3D HW), audio, 180 panel rotation, software
  media, low_ram.

## Pending investigation notes (when tackled)
- R1 (rotation): check `dumpsys sensorservice` (does it list the accelerometer?), lshal of
  android.hardware.sensors@*. If there is no sensors HAL, wire it (hardware/sprd sensors or the generic
  HAL). Also verify `settings get system accelerometer_rotation`.
- S1 (screenshot): `logcat` filtering GlobalScreenshot/SystemUI/MediaProvider when pressing capture; check
  permissions of /data/media/0/Pictures/Screenshots and the storage manager.
