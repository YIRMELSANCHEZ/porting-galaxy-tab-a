# V41 runtime diagnosis

Date: 2026-09-19

## Result

`V41_FULL_BOOT_PASS`

V41 reaches a complete Android 10 userspace boot on the physical SM-T280. This is the first build in this bring-up sequence with direct evidence of all of the following at the same time:

- `sys.boot_completed=1`
- `system_server` running
- `surfaceflinger` running
- `com.android.systemui` running
- `keystore` running
- `android.hardware.keymaster@4.0::IKeymasterDevice/default` registered as `TRUSTED_ENVIRONMENT`
- `BOOT_COMPLETED` delivered and processing completed for user 0

The software keymaster added in V41 therefore resolves the V40 boot blocker. It is a bring-up implementation, not hardware-backed security.

## Screen-black observation

The tablet did not power off or reboot during the captured incident. At capture time:

- ADB remained available in normal Android.
- `mWakefulness=Awake`.
- `Display Power: state=ON`.
- WindowManager reported the screen on and interactive.
- The foreground activity was `org.lineageos.setupwizard/.WelcomeActivity`.
- The configured screen-off timeout was 60 seconds, but no sleep transition had occurred (`mLastSleepTime=0`).

The logs contain input and activity timeouts for Lineage SetupWizard: the focused application had not produced a focused window. Consequently the observed black screen is most consistent with a stalled SetupWizard/window presentation path, not a shutdown. A framebuffer/backlight mismatch remains possible if the panel is visually black while Android reports it ON.

## Confirmed blocker: media service

`mediaserver` cannot start and is restarted repeatedly by init:

```text
CANNOT LINK EXECUTABLE "/system/bin/mediaserver": cannot locate symbol
"ion_is_legacy" referenced by "/system/lib/libcodec2_vndk.so"
```

This is the highest-priority defect for the next build because it prevents `media.player` from being published and causes dependent components, including SetupWizard media scanning/UI work, to wait repeatedly.

Probable correction: provide an ABI-compatible `ion_is_legacy` implementation/export to `libcodec2_vndk.so`, or rebuild/replace the mismatched Codec2 library against the ION compatibility layer actually present in this tree. Do not hide the failure by merely disabling mediaserver: hardware multimedia is a primary project requirement.

## Bluetooth failure

The legacy Bluetooth HAL loads, but controller initialization fails and `com.android.bluetooth` aborts. Observed sequence:

- HAL library loads.
- Controller is not ready and the adapter address cannot be returned.
- Bluetooth process dies with `SIGABRT`.
- Framework receives a dead binder and times out waiting for a valid state.

This is a separate subsystem issue and is not a boot blocker.

## Memory-management warnings

`lowmemorykiller` repeatedly receives `EACCES` while opening process `oom_score_adj` files. With approximately 1.5 GB RAM, this requires correction before stability/load testing. It did not prevent this boot from completing.

## Tombstones

Tombstones showing repeated keystore aborts are from the earlier V40 run (timestamps around 23:46-23:50 and the pre-V41 build fingerprint). They must not be attributed to V41. In the V41 runtime capture, keystore PID 325 remains alive and its Keymaster 4.0 device is registered.

## Classification

| Area | Status | Evidence |
|---|---|---|
| Full Android boot | PASS | `sys.boot_completed=1`, completed `BOOT_COMPLETED` |
| Keymaster/keystore bring-up | PASS | service registered; keystore remains alive |
| Framework/SystemUI | PARTIAL | running, but SetupWizard has focus/window timeouts |
| Display stack | PARTIAL | Android reports ON; visual black event still needs correlation |
| Multimedia framework | FAIL | unresolved `ion_is_legacy`; mediaserver restart loop |
| Bluetooth | FAIL | native Bluetooth process aborts during initialization |
| Memory management | PARTIAL | boot completes, but LMKD access warnings are continuous |

## Next build recommendation

Create V42 as a single-variable iteration focused on the missing `ion_is_legacy` symbol. Retain V41 boot, keymaster, graphics, and framework changes unchanged. After V42 boots, validate `media.player`, SetupWizard responsiveness, audio playback, video decode, and whether the visual black-screen event recurs. Bluetooth and LMKD should be handled in later isolated iterations unless either becomes a direct stability blocker.
