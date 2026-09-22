# SM-T280 (gtexswifi) -- Power button / wake: full findings (handoff)

Neutral document for analysis by another agent. Gathers EVERYTHING investigated about the "the power
button does not turn the screen on" problem in the LineageOS 17.1 / Android 10 port. **It does not
recommend a specific solution**: it lays out evidence, what was tried and the open routes for the agent to
decide.

Date: 2026-09-20. Author: previous debugging session (Claude).

---

## 1. Goal and symptom

- **User goal**: leave the tablet 100% usable by a NON-technical user (a child), for "an app that requires
  GLES 3.0" (audio/video/3D). The power button is an **essential priority**: user's words: *"it doesn't
  matter how smooth the video is if I can't turn the tablet on once it's off."*
- **Reported symptom**: when the screen turns off, pressing POWER does not turn it on. Also reported that
  "when pressing to turn off it does not turn off" (see nuances below; partly masked by a display hang
  introduced during debugging).

## 2. Hardware / software

- Samsung Galaxy Tab A 7.0 2016, SM-T280, codename **gtexswifi**, Spreadtrum **SC8830** SoC, Mali-400 GPU.
  4000 mAh battery. 1 GB RAM, 8 GB (data ~4.7 GB). Kernel **3.10.108** (gcc 4.8).
- LineageOS 17.1 (Android 10). SELinux in **Permissive**. adbd runs as **root** (userdebug); `mount -o
  rw,remount /` works.
- **system-as-root**: `/` is mounted from the SYSTEM partition (ext4). The rootdir init.*.rc and the
  keylayouts live in **system.img**, not in the boot ramdisk.
- Panel: **`sprdfb`** driver (drivers/video/sprdfb/, main = sprdfb_main.c). HWC: **hwcomposer.sc8830** blob
  (was Android 5.1). SurfaceFlinger composes on the GPU (CLIENT) + fb_post (pans every frame). 60 Hz.

## 3. MAIN CONCLUSION (verified on HW): they are TWO distinct problems

### Problem A -- The panel does NOT reactivate on resume (cause of "does not turn on")
- The framework DOES wake (mWakefulness=Awake, Display ON, SurfaceFlinger powerMode=2) but the **physical
  panel stays BLACK**.
- `sprdfb` uses `dev->enable`. If 0, `sprdfb_pan_display` prints `Invalid Device status 0` and does not
  paint -> black.
- When the screen turns off, the panel turns off (enable=0) via **earlysuspend** (CONFIG_HAS_EARLYSUSPEND;
  sprdfb registers early_suspend at level EARLY_SUSPEND_LEVEL_DISABLE_FB). Log: `early_suspend: calling
  sprdfb_early_suspend` -> `sprdfb_panel_suspend`.
- The **earlysuspend late_resume NEVER fires** on Android 10: nothing writes "on" to /sys/power/state.
  dmesg shows a `request_suspend_state: sleep (3->3)` storm but no "wake". Asymmetry: it turns off but does
  not turn back on. SurfaceFlinger thinks powerMode=ON and does not re-emit the power-on.
- **VERIFIED MANUAL FIX**: `adb shell "echo 0 > /sys/class/graphics/fb0/blank"` triggers `sprdfb_dsi_init
  resume` -> `sprdfb_panel_resume` -> `gen_panel_backlight resumed` -> `dev->enable= 1` -> **screen turns
  on with an image** (visually confirmed by the user). `echo 4 > .../blank` turns it off. The driver's
  resume WORKS; it only needs to be triggered.
- The HWC blob (SprdHWComposer::blank, opens /dev/graphics/fb%u) has Blank/UnBlank, but in the tests the
  unblank was NOT observed reaching sprdfb on wake (no resume or sprdfb_blank logs until forced by hand).

### Problem B -- The physical POWER button does not trigger the framework's power action
- On pressing physical POWER: the **IRQ 422 (irq-a-eic powerkey) DOES increment** (it reaches the kernel).
- **getevent** on /dev/input/event1 (sci-keypad) shows KEY_POWER DOWN/UP **clean** -> it reaches evdev.
- InputReader receives it (dumpsys input: sci-keypad's DownTime updates after the press).
- BUT the framework **does not act**: mWakefulness does not change, no PhoneWindowManager /
  PowerManagerService logs (neither "Going to sleep" nor "Waking up"). The screen neither turns off nor on
  with the physical button.
- **Software-injected DOES work**: `input keyevent 26` (POWER) turns off cleanly; `input keyevent 224`
  (WAKEUP) turns on (and with V60/V61 triggers the panel resume).
- Physical vs injected difference: the physical event carries keylayout policy flags; the injected one goes
  straight to InputDispatcher. Unresolved why the physical one does not reach PhoneWindowManager's power
  logic (interceptKeyBeforeQueueing). NOTE: some of the "does not turn off/on with the button"
  observations were made with the display already FROZEN by a test-version bug (V60), which may have masked
  the real behavior -> it is worth re-verifying B cleanly (V61 does not freeze).

## 4. Suspend (context that complicates B)

- Old kernel with **legacy wakelocks** (not modern wakeup_sources: /sys/kernel/debug/wakeup_sources empty
  except the header).
- The **`android.system.suspend@1.0-service` HAL** governs mem-suspend and **IGNORES /sys/power/wake_lock**
  of the kernel. Test: with `gtex_power_wake` in /sys/power/wake_lock, the device STILL suspends (a
  `BatteryStatsService: resumed from suspend` storm at ~10 Hz with USB).
- Stopping the HAL (`setprop ctl.stop system_suspend`) DOES stop the suspend (0 resumes) but **crashes
  system_server** (DeadSystemException) -> not viable.
- `chmod` on /sys/power/state does not stop the suspend (the HAL already has the fd open).
- With USB connected there is a suspend/resume loop (USB resume). Unplugged, the device enters mem-suspend
  and **the POWER press does not wake the framework** (event lost in the suspend/resume; enable_irq_wake
  V56 / irqchip set_wake V57 were not enough -> the EIC wake arm in the PMIC/ADI is not implemented). The
  "wake-from-mem-suspend" via the power key has NOT been achieved.
- Implication: even if A (panel) is fixed, if the device mem-suspends with the screen off, B may prevent
  the framework from waking -> the panel does not reactivate because SF does not paint.

## 5. History of tested versions (kernel = boot.img unless noted)

| Ver | Change | Result |
|-----|--------|--------|
| V55 | keylayout sci-keypad.kl `key 116 POWER WAKE`; sw media; low_ram | The framework uses Generic.kl, NOT sci-keypad.kl -> WAKE not effective. |
| V56 | enable_irq_wake(PB_INT) in sci_keypad_suspend (sc_keypad.c) | Insufficient (the device does not use standard PM suspend in that mode). |
| V57 | .irq_set_wake in a_eic_irq_chip/d_eic_irq_chip (gpio-eic.c) | Insufficient alone. |
| V58 | light_sleep_en=0 (cpuidle-scx35.c) | IRQ 422 now fires with the screen off; smoother system; did NOT solve the wake. |
| V59 | permanent wakelock in init.board.rc (`/sys/power/wake_lock "gtex_power_wake"`) + system rebuild | NOT reliable: the suspend HAL ignores that wakelock -> keeps suspending. (Revealed system-as-root: init.board.rc goes in system.img.) |
| runtime | `Generic.kl`: `key 116 POWER WAKE` (remount + edit; persists in /system) | Correct (Generic.kl is the effective one) but on its own it fixes nothing (the real failure is the panel, Problem A). |
| V60 | sprdfb_pan_display: INLINE auto-resume of the panel (sprdfb_power(dev,1)) | Triggers the resume BUT doing it inside the refresh path hangs the DISPC (`###---- BIT_DISPC0_EB still set ----###`) -> **frozen screen**. Discarded. |
| **V61** (current) | sprdfb_pan_display: **DEFERRED** resume via workqueue (schedule_work); while enable==0 skip the frame | In a software sleep/wake cycle: CLEAN panel resume (`dev->enable= 1`, no DISPC hang). Pending to validate with the physical button and unplugged. |

V56/V57/V58 changes are kept in the current boot. V59 (wakelock init + system) is flashed on the device's
current partition. The keylayout WAKE is in /system (runtime edit, persists until system is reflashed).

## 6. Current device state (V61 boot flashed, 2026-09-20)

- Kernel 3.10.108 with V56/V57/V58/V61. /system with V59 + Generic.kl POWER WAKE.
- SOFTWARE off/on cycle: works cleanly (V61 reactivates the panel, no freeze).
- PHYSICAL POWER button: IRQ rises, but does not turn off or on (Problem B unsolved / to re-verify
  cleanly).
- `dumpsys power`: mWakefulness=Awake, Display ON. `settings global stay_on_while_plugged_in=7` set
  (workaround: with USB it does not turn off by timeout).

## 7. Useful diagnostic commands (they work)

- adb: `C:\Dev\Experiments\porting-galaxy-tab-a\sm-t280-phase1\tools\platform-tools\adb.exe` (root).
- Power state: `dumpsys power | grep -E 'mWakefulness=|Display Power: state'`
- Button IRQ: `cat /proc/interrupts | grep -i powerkey` (line 422 irq-a-eic powerkey)
- Button evdev events: `getevent -lt /dev/input/event1` (sci-keypad = KEY_POWER/VOL/HOME)
- Force panel ON/OFF: `echo 0 > /sys/class/graphics/fb0/blank` / `echo 4 > ...`
- Inject power: `input keyevent 26` (sleep) / `input keyevent 224` (wakeup)
- See suspend: `dmesg | grep -c 'resumed from suspend'`; `dmesg | grep BIT_DISPC0_EB`
- Raise loglevel to see sprdfb pr_info: `echo 8 > /proc/sys/kernel/printk`
- Verify inside system.img: `simg2img system.img raw.img` (host bin in out/host/linux-x86/bin, cd to the
  dir) + `debugfs -R 'dump /path /tmp/x' raw.img`.

## 8. Possible solution routes (WITHOUT recommending any; for the agent to decide)

For Problem A (panel resume):
- A1. Keep the sprdfb auto-resume approach but deferred (V61) -- validate robustness (races with
  earlysuspend, DISPC hang in edge cases, first-frame latency).
- A2. Decouple sprdfb from earlysuspend (do not register early_suspend) and depend on the HWC's FBIOBLANK
  -- REQUIRES confirming that the HWC calls FBIOBLANK on setPowerMode (evidence says the OFF goes via
  earlysuspend, not FBIOBLANK -> risk that the screen does not turn off).
- A3. A userspace daemon that writes /sys/class/graphics/fb0/blank according to the display state (a
  mechanism proven 100% safe), with an init service -- requires a system.img rebuild and a reliable trigger
  (uevent, poll, etc.).
- A4. Fix the earlysuspend late_resume so it fires on A10 (have something write "on" to /sys/power/state,
  or reintroduce the earlysuspend wake path).

For Problem B (physical button -> framework) and suspend:
- B1. Investigate why the physical KEY_POWER does not reach PhoneWindowManager's interceptKeyBeforeQueueing
  even though InputReader receives it (policy flags, WAKE flag, effective keylayout, custom
  hwc2on1/PhoneWindowManager). Re-verify cleanly with V61 (no prior freeze).
- B2. Reliably prevent mem-suspend (at the kernel level, since the userspace levers fail or crash) so the
  event is not lost and the framework wakes.
- B3. Implement the real power-key wake arm in the PMIC (SC8830 ADI/ANA_EIC) to wake from mem-suspend
  (hardware-deep; see drivers/mfd/sprd/adi, arch/arm/mach-sc pm).

## 9. Restrictions (user authorization, STRICT)

- The user only flashes it HIMSELF, via Odin AP: boot.img (KERNEL) + system.img (SYSTEM). Auto Reboot OFF,
  Re-Partition unchecked. NO PIT/BL/CP/CSC/modem/recovery/wipe/bootloader without new authorization. The
  agent does NOT flash or physically reboot (a soft adb reboot has been used).
- Do NOT init git yet. Packages >30 MB cannot be sent to mobile/web (the user takes them from
  sm-t280-phase6\packages\).
- Battery: the user prioritizes the tablet TURNING ON over standby (accepts worse battery).

## 10. Locations

- kernel/device tree in WSL Ubuntu-22.04 user `lineage`: /home/lineage/android/lineage-17.1
- sprdfb: kernel/samsung/gtexswifi/drivers/video/sprdfb/sprdfb_main.c (pan_display ~L333, sprdfb_power
  ~L544, sprdfb_blank ~L577, early_suspend/late_resume ~L593/608, register ~L903).
- Patcher scripts: sm-t280-phase6/scripts/apply-vNN-*.py (V55..V61). Packaging:
  package-system-for-odin.sh / package-boot-only-for-odin.sh; legacy_sparse.py.
- Packages: sm-t280-phase6/packages/ (V61 = SM-T280-android10-panel-resume-PHASE6-v61-DO-NOT-FLASH.tar.md5,
  boot sha256 4f8649fe853b5fbef7d4eb75aa766e2169775677ba91bb4504f089eae055973f).

## 11. Diagnosis correction and V62 candidate (2026-09-20)

The clean V61 test definitively separated the physical button from the panel:

- Android was fully booted, ADB working and the screen on/frozen at the unlock.
- A physical press produced `KEY_POWER DOWN` and `KEY_POWER UP` on `/dev/input/event1`.
- The `powerkey` IRQ counter went from 18 to 20.
- `mWakefulness` stayed `Awake` and `Display Power: state=ON`.
- The user confirmed the screen stayed on and visually the same.
- `dumpsys input` showed `sci-keypad` enabled, but `KeyLayoutFile` empty.

The root cause is the Android 10 parser, not the button or the IRQ. On this branch, `InputEventLabels.h`
only accepts `VIRTUAL`, `FUNCTION` and `GESTURE` as keylayout flags. The legacy `WAKE` flag causes
`Expected key flag label, got 'WAKE'`; `KeyLayoutMap.cpp` then rejects the whole file. Therefore, the
historical claim that `Generic.kl POWER WAKE` was a correct mapping is replaced by this finding: `WAKE` is
invalid on this Android 10 and leaves the device with no keylayout loaded.

V62 removes `WAKE` from POWER and HOME in `sci-keypad.kl`. It does not need that flag: once translated to
`KEYCODE_POWER`, `PhoneWindowManager` implements on/off itself. The patch was applied directly on a copy of
`system.img`, replacing only eight bytes with spaces and keeping the file's size, inode, permissions and
xattrs. `boot.img` is V61 unchanged.

Offline validations passed:

- `V62_SPARSE_KEYLAYOUT_PATCH_PASS`
- `V62_SPARSE_KEYLAYOUT_VERIFY_PASS` on standard sparse and Samsung legacy
- `ODIN_SYSTEM_PACKAGE_PASS`
- `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`
- AP content: only `boot.img` and `system.img`
- boot SHA-256 V61: `4f8649fe853b5fbef7d4eb75aa766e2169775677ba91bb4504f089eae055973f`
- package SHA-256: `5df2008396a8fe4d0a4e2e8f778eb6d968573c040d41b7da8443a359b189959b`

Package pending physical validation:

`sm-t280-phase6/packages/SM-T280-android10-power-button-PHASE6-v62-DO-NOT-FLASH.tar.md5`

Physical test after flashing, without assuming states:

1. Explicitly confirm that Android finished booting and that the screen is visible and responsive.
2. Check via ADB that `sci-keypad` has a `KeyLayoutFile` and that the `WAKE` flag error does not appear.
3. With the screen confirmed on, ask for a single brief POWER press and confirm visually if it turned off.
4. Only after confirming the screen off, ask for another brief press and confirm if it woke.
5. Correlate both actions with IRQ, `getevent`, `dumpsys power`, logcat and dmesg. If the panel freezes
   again, treat it as a V61/V63 issue separate from the V62 mapping.

## 12. V62 physical result and V63 candidate (2026-09-20)

V62 definitively fixes the physical-button -> framework leg:

- Off: `KEY_POWER DOWN/UP` -> `Going to sleep due to power_button` -> `Asleep`, display OFF.
- On: `KEY_POWER DOWN/UP` -> `WAKE_REASON_POWER_BUTTON` -> `Awake`, display ON.

The wake revealed the remaining failure. During the off, `early_suspend` ran all handlers and left
`mip4_ts` in `Disabled`. During the on, `late_resume: call handlers` did not appear. V61 turned `sprdfb` on
directly, but touch stayed off; a physical press generated no event on `/dev/input/event3`. Also, the DISPC
again logged `BIT_DISPC0_EB still set`. The user saw the screen on, but frozen and unresponsive to touch.

V63 replaces V61's isolated LCD turn-on with `request_suspend_state(PM_SUSPEND_ON)` from the same deferred
worker. This queues the kernel's normal `late_resume` and resumes in reverse order all the clients that had
suspended, including sprdfb, mip4 and touchkey. It is a **boot-only** package; it keeps the V62 system with
the validated keylayout unchanged.

- Boot SHA-256: `e4641a1672e610aab448bb666678b43981116f271b2c373b9042ab14534fbf38`
- Package SHA-256: `98daf85f0e27514a2e71c2301edc5ebecc2f27bb4ee4b10dc1f0818ba6b87094`
- Offline validation: `V63_BOOT_BUILD_PASS`, `ODIN_BOOT_ONLY_PACKAGE_PASS` and
  `V63_BOOT_ONLY_PACKAGE_VERIFY_PASS`.
- Package: `sm-t280-phase6/packages/SM-T280-android10-full-late-resume-PHASE6-v63-DO-NOT-FLASH.tar.md5`.

## 13. V63 physical result and V64 candidate (2026-09-20)

V63 confirmed that the full resume mechanism works, but also revealed an incompatibility between Android 10
and the legacy early-suspend:

- the first press produced a single `KEY_POWER DOWN/UP`, Android went to `Asleep` and the screen turned
  off;
- the second press produced `WAKE_REASON_POWER_BUTTON` and Android returned to `Awake`;
- V63 ran `late_resume: call handlers`, reactivated sprdfb, left `mip4_ts - Enabled` and resumed touchkey;
- during those handlers `request_suspend_state: sleep (0->3)` arrived and, when the resume finished, another
  `early_suspend` ran immediately, disabling touch and panel again;
- the user saw it on for about half a second and then periodic flicker. `dumpsys power` still reported
  `Awake` and display `ON`.

The source is `android.system.suspend@1.0-service`: with `mUseSuspendCounter=false`, its thread writes
`mem` every 100 ms even though a kernel wakelock prevents the real suspend. This 3.10 kernel uses the same
write to drive early-suspend, so the mere attempt turns off the interactive peripherals.

V64 configures the service with `mUseSuspendCounter=true`. Android will keep the autosuspend thread blocked
while a `PowerManagerService.Display` exists; it can only write `mem` when the wakelock counter reaches
zero. Boot V63 and the V62 keylayout are kept.

- Boot SHA-256: `e4641a1672e610aab448bb666678b43981116f271b2c373b9042ab14534fbf38`
- Service SHA-256: `75f7d8f769168340ccf1e1db43aece0f4b07566911e405e15824b08d7fce7eb5`
- System legacy SHA-256: `4d7ca49c63142f02e2f5d09a6b50609d1f99b7a86120321b0f7da705f28bdb8b`
- Package SHA-256: `297209ae12cd9061ee100518ab1aaba587e34071de5859016f941a19244b13f6`
- Validations: `V64_SYSTEM_SUSPEND_BUILD_PASS`, `SYSTEM_BOOT_OFFLINE_VERIFY_PASS`,
  `ODIN_SYSTEM_PACKAGE_PASS`, `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`, `V64_PACKAGE_PASS`.
- Package: `sm-t280-phase6/packages/SM-T280-android10-suspend-counter-PHASE6-v64-DO-NOT-FLASH.tar.md5`.

## 14. Requirement for the next fix: cancel a pending OFF on wake

There is a race window during the power-off delay: the framework is already `Asleep` and the logical
display reads `OFF`, but panel and backlight are still physically on until `early_suspend` arrives. A second
POWER press during that window is a valid wake.

The future immediate-off solution must guarantee that this press invalidates any pending OFF operation. A
late worker must not turn the panel off after Android has returned to `Awake`. The verifiable final state
must include a stable physical display, refreshing frames, `mip4_ts` enabled and working touch, with no
`early_suspend` after the resume.

Therefore, any asynchronous implementation needs a cancelable generation or a final check of the desired
state under a lock. The physical validation will include fast OFF->ON before the real power-off, with
several intervals, both locked and unlocked, and a later wait to detect deferred power-offs.

## 15. V66 implementation: HWC ioctl as authoritative state

It was confirmed that the reliable signal does exist: SurfaceFlinger calls the Spreadtrum HWC and it sends
`SPRD_FB_SET_POWER_MODE` to the framebuffer immediately on every logical transition. The stock driver just
recorded the value, which explains why the physical power-off waited for `early_suspend`.

V66 connects that ioctl to `sprdfb_power()`:

- OFF/SUSPEND turn the panel off synchronously;
- NORMAL/DOZE first cancel a pending legacy suspend, turn on and refresh;
- there is no OFF worker, so a fast OFF->ON cannot suffer a later stale power-off;
- the `sprdfb_power()` mutex and the V63 `late_resume` resolve the race if the suspend handlers had already
  started.

Offline build and packaging passed. The V66 AP contains only `boot.img`:

- boot SHA-256: `5907fe4871e3da25e15bdf18050c55cdc83dd39b583179473963e52a026c7b69`
- package SHA-256: `725b8275c7a10d9eeb4cf3f94ca1392d8d8419f31ca2ecd577ce3cdfd049c187`
- validations: `V66_BOOT_BUILD_PASS`, `ODIN_BOOT_ONLY_PACKAGE_PASS`, `V66_BOOT_ONLY_PACKAGE_VERIFY_PASS`,
  `SYSTEM_BOOT_OFFLINE_VERIFY_PASS`

Physical validation is still pending and must cover normal OFF/ON and fast OFF->ON at about 100/300/700 ms,
locked and unlocked, checking screen, frames and touch.

## 16. V66 had no effect and the V67 fix on the real path

The V66 test confirmed the new boot (`kernel #28`) but produced no `V66 HWC power-mode` marker.
`/proc/<composer>/maps` showed that the service loads `libhwc2onfbadapter.so` and not `hwcomposer.sc8830.so`.
The adapter power hook used ignored the mode with `// pretend that it works`; this is the direct cause of
V66 having no effect.

V67 replaces that no-op with a synchronous `FBIOBLANK` on fb0. The kernel `sprdfb_blank` is extended to
cancel the pending legacy suspend before unblank and to keep panel and touch active as the final state even
on a fast OFF->ON. The boot+system package is verified offline:

- boot: `2d621cf4d4862c31edb182d2c6348a4f611812755389b4a6b6ad50c9d9e317c1`
- system legacy: `167e9c120af385dc3f1259e99060d6a781ccd16e67f652fa5108bfe9dee25e2c`
- package: `99b01e53213391eecc2592eeab2b76d97cac02c8b4689cff1da33c11a2d4e218`

Status: **physical V67 PASS**. The user confirmed it works and the logs validated normal OFF/ON, fast
OFF->ON, touch recovery and no late power-off.

## 17. Final V67 physical validation and health audit

V67 is the first version that closes the whole button -> framework -> HWC2 -> framebuffer -> panel chain
and coordinates it with early/late resume. The test left Android `Awake`, display `ON`, touch enabled and
real brightness 143. Three fast OFF->ON races were observed; all ended in a stable ON and no later OFF
appeared. SurfaceFlinger reported zero dropped frames.

The audit also found independent issues that must not be confused with a button regression:

- The EFS and prodnv partitions exist, but `/efs` and `/productinfo` do not exist and so are not mounted.
  There is no evidence of loss; the mount points are missing in system-as-root.
- Bluetooth enters an abort loop because `android.hardware.bluetooth@1.0::IBluetoothHci/default` neither
  exists nor is declared.
- The legacy gralloc path causes many `ion_invalidate_for_cpu` with `ERR_PTR(-EBADF)` when trying to
  invalidate an invalid DMA-BUF descriptor. It is kernel noise and a performance risk, not an FBIOBLANK
  failure.
- A single `BIT_DISPC0_EB still set` warning appeared inside a suspend-attempt dump with active wakelocks.
  It did not coincide with a freeze: the final state, touch and SurfaceFlinger stayed healthy.
- The SC2331 driver logs periodic `wlan_scan_timeout()`. Wi-Fi must be evaluated as a separate issue if
  scan or connection failures are observed.

Full evidence: `results/phase-6/V67-LIVE-VALIDATION.md`.
