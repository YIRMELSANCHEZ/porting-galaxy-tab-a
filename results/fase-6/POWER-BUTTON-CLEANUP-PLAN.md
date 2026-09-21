# SM-T280 -- Cleanup plan for the power-button patches

Goal: keep ONLY what helps, reverting the unnecessary/harmful. **Not executed**: plan ready to apply when
decided. Coordinate with **V62** (keylayout, from the other agent). Each revert operation is a
`str.replace(NEW -> OLD)` on the indicated file.

Date: 2026-09-20. Source of truth for the diagnosis: POWER-BUTTON-FINDINGS.md.

---

## 0. Execution principle (important)

- **Do it in ONE build/flash cycle**, reconciled with V62, so as not to multiply flashes.
- Kernel reverts -> rebuild **boot.img**. init.board.rc/keylayout reverts -> rebuild **system.img**
  (system-as-root). If both are touched, flash boot+system together (Odin AP).
- After any kernel rebuild: **verify WiFi** (sprdwl.ko). In principle the vermagic does not change (same
  version/config), but confirm that `wlan0` comes up after flashing.
- User restriction intact: only boot.img+system.img via Odin AP; the user flashes.

## 1. Classification

| Item | Partition | Action |
|------|-----------|--------|
| V55 `sci-keypad.kl` WAKE | system | **REVERT** (invalid WAKE; coordinate with V62) |
| V56 `sc_keypad.c` enable_irq_wake | boot | **REVERT** (unnecessary) |
| V57 `gpio-eic.c` irq_set_wake | boot | **REVERT** (unnecessary) |
| V58 `cpuidle-scx35.c` light_sleep_en=0 | boot | **DECISION** (smoothness <-> standby; not the button) |
| V59 `init.board.rc` wakelock | system | **REVERT** (confirmed useless) |
| V60 sprdfb inline | boot | **N/A** (already replaced by V61 in the file) |
| V61 sprdfb deferred resume | boot | **KEEP** unless V62/agent chooses another panel approach |
| Runtime Generic.kl WAKE | /system device | **REVERT** via a clean system reflash (V62) |
| Runtime `stay_on_while_plugged_in=7` | /data | **REVERT** once the button works |

## 2. Exact reverts

### 2.1 V56 -- `kernel/samsung/gtexswifi/drivers/input/keyboard/sc_keypad.c`
Remove the suspend line:
- Replace:
  ```
  static int sci_keypad_suspend(struct platform_device *dev, pm_message_t state)
  {
  	/* V56: arm the power IRQ (EIC) as a wake source to resume from suspend */
  	enable_irq_wake(gpio_to_irq(PB_INT));
  	return 0;
  }
  ```
  with:
  ```
  static int sci_keypad_suspend(struct platform_device *dev, pm_message_t state)
  {
  	return 0;
  }
  ```
Remove the resume line: delete the `\tdisable_irq_wake(gpio_to_irq(PB_INT));\n` line that V56 inserted
after the `pdata`/`value` declaration in `sci_keypad_resume`.

### 2.2 V57 -- `kernel/samsung/gtexswifi/drivers/gpio/gpio-eic.c`
For `irq-a-eic` and `irq-d-eic`, remove the added line: `\t.irq_set_wake = sci_gpio_irq_set_wake,\n` (the
struct is left as it was, closing at `.irq_set_type = sci_eic_irq_set_type,\n};`).

### 2.3 V59 -- `device/samsung/gtexswifi/rootdir/init.board.rc`
Remove the block inserted after `on boot` + `chown ... sprd_simdet/state`:
```
# V59: permanent partial wakelock -> the system does NOT enter mem-suspend, so the power
# button can wake the off screen (KEY_POWER event lost in the suspend resume). Trade-off:
# worse standby. See KNOWN-ISSUES P1.
    write /sys/power/wake_lock "gtex_power_wake"
```
(leave only the line `chown system system /sys/class/switch/sprd_simdet/state`).

### 2.4 V55 (button part) -- `device/samsung/gtexswifi/keylayout/sci-keypad.kl`
`key 116   POWER          WAKE` -> `key 116   POWER`. **Coordinate with V62**: if V62 already leaves the
keylayout valid (no WAKE) and decides whether to use sci-keypad.kl or Generic.kl, align this with V62
instead of reverting separately. Do NOT touch the V55 parts of media_codecs or low_ram (not the button;
kept).

### 2.5 Runtime on the device (not in the tree)
- `Generic.kl` with WAKE in /system: reverted by **flashing a clean system.img** (V62). Nothing to edit in
  the tree (it was a live edit).
- `stay_on_while_plugged_in`: `adb shell settings put global stay_on_while_plugged_in 0` once the button
  works (and adjust `screen_off_timeout` to the desired value).

## 3. V58 -- decision (not the button)
`static int light_sleep_en = 0;` (V58) gives more smoothness but worse standby. To revert to stock: `0` ->
`1` in `drivers/platform/sprd/cpuidle-scx35.c`. Recommendation: decide according to the user's battery
priority; not needed for the button. If standby is prioritized, revert.

## 4. Suggested sequence (a single build/flash, after V62)
1. Wait for V62 (valid keylayout + its panel approach if changed).
2. Apply reverts 2.1 (V56), 2.2 (V57), 2.3 (V59) and decide 2.4 (V55 kl) and V58.
3. Reconcile the panel: keep V61 unless V62 brings another panel fix (Problem A).
4. `mka bootimage` + `mka systemimage` (systemimage because of init.board.rc/keylayout).
5. Convert system to legacy sparse and package boot+system (package-system-for-odin.sh).
6. User flashes via Odin AP (Auto Reboot OFF, Re-Partition off).

## 5. Post-flash verification
- `dumpsys input | grep -A15 sci-keypad` -> **KeyLayoutFile NOT empty** and maps POWER.
- Physical button: turns the screen off and **on** (Problem B resolved by V62).
- Panel: after off/on, image visible without freeze (Problem A; V61/V62).
- WiFi: `wlan0` comes up and connects (sprdwl.ko OK after kernel rebuild).
- `dmesg | grep BIT_DISPC0_EB` -> no new hangs.
- No `gtex_power_wake` wakelock in `/sys/power/wake_lock` (V59 reverted).

## 6. Do NOT touch (outside the button)
Previous functional fixes: boot to launcher, WiFi/internet, Mali-400 GPU, audio, 180 rotation, software
media (V55 media_codecs), low_ram. The V55 media/low_ram part is kept.

## 7. Revert scripts (to generate when execution is decided)
They can be created as `revert-vNN-*.py` (idempotent, `NEW -> OLD`) mirroring the apply-vNN. Not yet
created so as not to clash with what V62 touches; generate after reconciling.
