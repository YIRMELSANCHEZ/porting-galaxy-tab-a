#!/usr/bin/env python3
# V43 (phase 6 - post-boot tweak): with V42 the device boots fully (boot_completed=1,
# SetupWizard visible, media OK), but the SCREEN COMES OUT ROTATED 180 degrees (panel mounted
# inverted). The device has ro.sf.hwrotation=180, but in Android 10 SurfaceFlinger ALREADY
# does NOT read that property (confirmed: there is no reference to hwrotation in
# frameworks/native/services/surfaceflinger). In Q the primary display orientation is
# controlled with the sysprop ro.surface_flinger.primary_display_orientation
# (SurfaceFlinger.cpp: primary_display_orientation() -> ORIENTATION_180 ->
# eOrientation180), which was empty -> ORIENTATION_0 -> inverted image.
#
# Fix: ro.surface_flinger.primary_display_orientation=ORIENTATION_180. SurfaceFlinger
# composes the output rotated 180; the internal screen's touch follows the orientation of the
# display, so image and touch stay aligned. Wired in PRODUCT_PROPERTY_OVERRIDES
# (wins). Only system.img changes (build.prop); boot = V35. Cumulative. Idempotent.
import sys

DEVMK = "/home/lineage/android/lineage-17.1/device/samsung/gtexswifi/device.mk"

OLD = (
    "    dalvik.vm.usejit=false \\\n"
    "    dalvik.vm.usejitprofiles=false\n"
)
NEW = (
    OLD
    + "\n"
    "# V43: panel montado invertido -> imagen rotada 180. Android 10 ignora ro.sf.hwrotation;\n"
    "# la orientacion del display primario se fija con este sysprop (SurfaceFlinger la aplica\n"
    "# a la composicion y el tactil interno la sigue).\n"
    "PRODUCT_PROPERTY_OVERRIDES += \\\n"
    "    ro.surface_flinger.primary_display_orientation=ORIENTATION_180\n"
)

s = open(DEVMK, encoding="utf-8", errors="surrogateescape").read()

if "primary_display_orientation" in s:
    print("V43_ALREADY"); sys.exit(0)

if OLD not in s:
    print("V43_ERROR: cannot find the expected usejit (V37) block")
    sys.exit(1)

s = s.replace(OLD, NEW, 1)
open(DEVMK, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V43_APPLIED -> ro.surface_flinger.primary_display_orientation=ORIENTATION_180")
