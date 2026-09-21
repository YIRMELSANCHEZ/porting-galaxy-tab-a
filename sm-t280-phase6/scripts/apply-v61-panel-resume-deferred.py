#!/usr/bin/env python3
# V61 (fixes the V60 hang). KERNEL CHANGE -> boot.img. Requires V60 applied first.
#
# V60 reactivated the panel INLINE inside sprdfb_pan_display (composition/refresh path),
# which left the DISPC hung ("###---- BIT_DISPC0_EB still set ----###") -> frozen
# screen after an off/on cycle. The resume mechanism is correct (echo 0 >
# /sys/class/graphics/fb0/blank works cleanly), but it CANNOT be called from the refresh.
#
# V61: make the resume DEFERRED in a worker (schedule_work), outside the composition path.
# While enable==0, pan_display queues the resume and skips the frame (return 0); when the worker
# reactivates the panel (enable=1), the following frames paint normally. No re-entrancy with the DISPC.
# Idempotent. Replaces the V60 inline block.
import sys

SRC = "/home/lineage/android/lineage-17.1/kernel/samsung/gtexswifi/drivers/video/sprdfb/sprdfb_main.c"
s = open(SRC, encoding="utf-8", errors="surrogateescape").read()

if "V61: resume DIFERIDO" in s:
    print("V61_ALREADY"); sys.exit(0)

# 1) Insert the worker infrastructure right after the V60 fwd-decl.
FWD = "static int sprdfb_power(struct sprdfb_device *dev, int on); /* V60 fwd-decl */\n"
INFRA = (FWD +
         "static struct sprdfb_device *sprdfb_resume_dev; /* V61 */\n"
         "static void sprdfb_resume_work_func(struct work_struct *w) /* V61 */\n"
         "{\n"
         "\tstruct sprdfb_device *dev = sprdfb_resume_dev;\n"
         "\tif (dev && 0 == dev->enable)\n"
         "\t\tsprdfb_power(dev, 1);\n"
         "}\n"
         "static DECLARE_WORK(sprdfb_resume_work, sprdfb_resume_work_func); /* V61 */\n")
if FWD not in s:
    print("V61_ERROR: cannot find the V60 fwd-decl (apply V60 first)"); sys.exit(1)
s = s.replace(FWD, INFRA, 1)

# 2) Replace the V60 inline block with the deferred one.
V60_BLOCK = ("\tif(0 == dev->enable){\n"
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
V61_BLOCK = ("\tif(0 == dev->enable){\n"
             "\t\t/* V61: resume DIFERIDO. Reactivar el panel inline aqui (ruta de refresh) colgaba\n"
             "\t\t * el DISPC (BIT_DISPC0_EB). Lo hacemos en un worker fuera de la ruta de\n"
             "\t\t * composicion; mientras enable==0 saltamos el frame. */\n"
             "\t\tsprdfb_resume_dev = dev;\n"
             "\t\tschedule_work(&sprdfb_resume_work);\n"
             "\t\treturn 0;\n"
             "\t}\n")
if V60_BLOCK not in s:
    print("V61_ERROR: cannot find the V60 inline block in pan_display"); sys.exit(1)
s = s.replace(V60_BLOCK, V61_BLOCK, 1)

open(SRC, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V61_APPLIED -> deferred resume via workqueue in pan_display")
