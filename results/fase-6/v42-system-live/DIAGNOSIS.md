# Phase 6 -- V42: FULL BOOT (boot_completed=1, UI). Pending adjustment: 180 rotation

Date: 2026-09-19. Source: V42 flashed. User: "boot achieved but the screen is rotated 180 degrees, I see
Next / Emergency call" (= Android's SetupWizard visible).

## MILESTONE -- the tablet boots Android 10 to the UI

- `sys.boot_completed=1`.
- `init.svc.media=running`: mediaserver (pid 355) and media.codec (pid 879) STABLE. V42 (ion_is_legacy in
  libion_sprd) resolved the linker crash-loop: before -> `CANNOT LINK EXECUTABLE
  "/system/bin/mediaserver": cannot locate symbol "ion_is_legacy" referenced by
  "/system/lib/libcodec2_vndk.so"`. Now 0 occurrences.
- SetupWizard on screen (Next / Emergency call) -> framework + SystemUI + boot apps OK. The phase 6 blocker
  chain is COMPLETE (V36..V42).

## Adjustment 1 (V43): screen rotated 180 degrees

The panel is mounted inverted. The device carries `ro.sf.hwrotation=180`, but Android 10 NO LONGER reads
that property (no references to hwrotation in frameworks/native/services/surfaceflinger). On Q the primary
display orientation is set with the sysprop `ro.surface_flinger.primary_display_orientation`
(SurfaceFlinger.cpp:326 primary_display_orientation() -> ORIENTATION_180 -> eOrientation180), which was
empty -> ORIENTATION_0 -> inverted image.

V43 (`apply-v43-display-rotation.py`): PRODUCT_PROPERTY_OVERRIDES +=
ro.surface_flinger.primary_display_orientation=ORIENTATION_180. SurfaceFlinger composes the output rotated
180 and the internal screen's touch follows the display orientation, so image and touch stay aligned.
system.img only; boot = V35.

Expected success: UI in the correct orientation and aligned touch. Verify with the user.

## Pending to review after V43 (not boot blockers)
- Confirm working and aligned touch after the rotation.
- Wifi/network (for setup and to install the app for the kids).
- Real audio (playback), video acceleration (Codec2 already links; still to test).
- Complete SetupWizard or skip it; then install "an app that requires GLES 3.0".
