# V62 — Physical POWER key mapping

Status: **POWER MAPPING HARDWARE PASS; RESUME PIPELINE PARTIAL**

## Observed failure on V61

Evidence is stored in `results/fase-6/v61-power-button-live/`.

- Device: ADB `device`, `sys.boot_completed=1`.
- Initial state: Android `Awake`, display `ON`.
- Physical POWER press: Linux `KEY_POWER DOWN/UP`; IRQ counter 18 -> 20.
- Result: Android remained `Awake`, display remained `ON`; user saw no visual change.
- InputReader: `sci-keypad` enabled but no `KeyLayoutFile` loaded.

## Root cause

The inherited `WAKE` token in `sci-keypad.kl` is not a valid Android 10 key-layout flag in
this branch. The parser rejects the entire file, so scan code 116 never becomes Android
`KEYCODE_POWER`, even though Linux receives the physical event correctly.

## V62 change

Remove the invalid `WAKE` tokens from POWER and HOME. No kernel change is included. The V61
boot image remains byte-identical; only `system.img` changes.

To avoid a 59,586-target rebuild caused by regenerated kernel headers, the fix was applied to
a copy of the already validated standard sparse system image. The replacement preserves the
exact file length and all filesystem metadata. The patched image was then converted to the
Samsung legacy sparse header format and packaged for Odin.

## Artifacts

- AP package: `sm-t280-phase6/packages/SM-T280-android10-power-button-PHASE6-v62-DO-NOT-FLASH.tar.md5`
- Package SHA-256: `5df2008396a8fe4d0a4e2e8f778eb6d968573c040d41b7da8443a359b189959b`
- Boot SHA-256: `4f8649fe853b5fbef7d4eb75aa766e2169775677ba91bb4504f089eae055973f`
- Legacy system SHA-256: `e59c6d3f82d53cbdffa2f86cc1d3e8589b3b78d727591e8d19172e50fe826ef0`

The AP archive contains exactly `boot.img` followed by `system.img`; it contains no recovery,
PIT, BL, CP, CSC or modem image.

## Offline validation

- `V62_SPARSE_KEYLAYOUT_PATCH_PASS`
- `V62_SPARSE_KEYLAYOUT_VERIFY_PASS` (standard and Samsung legacy sparse images)
- `ODIN_SYSTEM_PACKAGE_PASS`
- `ODIN_BOOT_SYSTEM_PACKAGE_VERIFY_PASS`

## Hardware validation protocol

Do not infer the physical state. Confirm each state with the user before the next action:

1. User flashes the AP package with Auto Reboot OFF and Re-Partition OFF.
2. User boots Android manually and confirms that boot completed, the display is on, and the UI
   is responsive.
3. Read-only ADB verifies loaded keylayout and absence of parser errors.
4. Capture a single short POWER press. User confirms whether the display turns off.
5. If and only if display-off is confirmed, capture a second short POWER press. User confirms
   whether the display wakes and whether the frame is live rather than frozen.

## Hardware result

- V62 booted fully and InputReader loaded
  `/system/usr/keylayout/sci-keypad.kl`.
- No `Expected key flag label` error appeared.
- First physical POWER press produced clean `KEY_POWER DOWN/UP`; Android logged
  `Going to sleep due to power_button`, changed to `Asleep`, and display changed to `OFF`.
- Second physical POWER press produced clean `KEY_POWER DOWN/UP`; Android logged
  `WAKE_REASON_POWER_BUTTON`, changed to `Awake`, and display changed to `ON`.
- Therefore the V62 key mapping is confirmed fixed.
- The woken screen was visible but frozen and did not react to touch. Direct capture from
  `/dev/input/event3` returned no event for a physical tap.
- Kernel logs explain this second failure: `early_suspend` disabled `mip4_ts`, but wake never
  invoked `late_resume`. V61 resumed only `sprdfb`; `mip4_ts` remained disabled and the display
  later logged `BIT_DISPC0_EB still set`.

The remaining failure is addressed separately by the V63 boot-only candidate.
