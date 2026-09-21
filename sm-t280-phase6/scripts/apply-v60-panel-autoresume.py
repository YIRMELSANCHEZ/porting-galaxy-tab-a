#!/usr/bin/env python3
# V60 (THE REAL FIX for "button does not turn the screen on"). KERNEL CHANGE -> boot.img.
#
# ROOT CAUSE (verified on HW 2026-09-20): it was NOT the button, the WAKE, or suspension.
# It is the sprdfb panel driver. The panel is controlled by dev->enable; if 0, sprdfb_pan_display
# refuses to paint ("Invalid Device status 0") -> BLACK screen. The panel turns off via
# earlysuspend (which fires with the "mem" writes of the suspension HAL when the screen sleeps),
# but its late_resume NEVER fires on Android 10 because nothing writes "on" to /sys/power/state.
# Result: on waking, the system is Awake (framework Display ON) but the panel stays
# apagado y SurfaceFlinger pinta en negro. (Confirmado: 'echo 0 > /sys/class/graphics/fb0/blank'
# re-lights the panel perfectly -> the driver's resume works; it just needs triggering.)
#
# FIX: in sprdfb_pan_display, if the panel is off (enable==0) but SurfaceFlinger requests
# painting (pan), re-light the panel (sprdfb_power(dev,1)) instead of just erroring. If SF paints,
# the screen must be on. SF composes via GPU + fb_post (pan each frame), so on
# the first frame after waking the panel auto-reactivates. Power-off stays the same (earlysuspend
# on sleep; SF stops painting, no pan -> no reactivation). It is a minimal and low-
# risk change; the worst case would be a flicker, versus the current failure (permanent black).
# sprdfb_power is defined after pan_display -> we add a forward-declaration. Idempotent.
import sys

SRC = "/home/lineage/android/lineage-17.1/kernel/samsung/gtexswifi/drivers/video/sprdfb/sprdfb_main.c"
s = open(SRC, encoding="utf-8", errors="surrogateescape").read()

if "V60: auto-resume" in s:
    print("V60_ALREADY"); sys.exit(0)

# 1) forward-declaration de sprdfb_power antes de pan_display
DECL_ANCHOR = "static int sprdfb_pan_display(struct fb_var_screeninfo *var, struct fb_info *fb)\n{"
DECL_NEW = ("static int sprdfb_power(struct sprdfb_device *dev, int on); /* V60 fwd-decl */\n\n"
            + DECL_ANCHOR)
if DECL_ANCHOR not in s:
    print("V60_ERROR: cannot find the sprdfb_pan_display definition"); sys.exit(1)
s = s.replace(DECL_ANCHOR, DECL_NEW, 1)

# 2) replace the error with auto-resume in pan_display
OLD = ("\tif(0 == dev->enable){\n"
       "\t\tprintk(KERN_ERR \"sprdfb: [%s]: Invalid Device status %d\", __FUNCTION__, dev->enable);\n"
       "\t\treturn -1;\n"
       "\t}\n")
NEW = ("\tif(0 == dev->enable){\n"
       "\t\t/* V60: auto-resume. A10 no dispara el late_resume del earlysuspend (nada escribe\n"
       "\t\t * \"on\" a /sys/power/state), asi que el panel se queda apagado tras encender la\n"
       "\t\t * pantalla y SF pinta en negro. Si SF pide pintar, la pantalla debe estar ON. */\n"
       "\t\tprintk(KERN_WARNING \"sprdfb: [%s]: panel off, auto-resume\\n\", __FUNCTION__);\n"
       "\t\tsprdfb_power(dev, 1);\n"
       "\t\tif(0 == dev->enable){\n"
       "\t\t\tprintk(KERN_ERR \"sprdfb: [%s]: Invalid Device status %d\", __FUNCTION__, dev->enable);\n"
       "\t\t\treturn -1;\n"
       "\t\t}\n"
       "\t}\n")
if OLD not in s:
    print("V60_ERROR: cannot find the original 'Invalid Device status' block in pan_display"); sys.exit(1)
s = s.replace(OLD, NEW, 1)

open(SRC, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V60_APPLIED -> sprdfb_pan_display panel auto-resume")
