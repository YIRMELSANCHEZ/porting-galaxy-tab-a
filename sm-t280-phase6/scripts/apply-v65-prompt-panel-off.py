#!/usr/bin/env python3
# V65 (Option A: screen off WITHOUT delay). KERNEL CHANGE -> boot.img.
# File: drivers/video/backlight/gen_panel/gen-panel-bl.c (built-in, CONFIG_GEN_PANEL_BACKLIGHT=y).
# Does NOT touch sprdfb_main.c -> does not collide with the other agent's patches (V60-V63 are in sprdfb).
#
# CAUSE (measured on HW): after wake, V63 leaves the earlysuspend state at PM_SUSPEND_ON. On turning off,
# the panel only turns off when early_suspend runs, and that only fires when the suspension
# HAL manages to suspend (after releasing all wakelocks: keypad 1s, WiFi, V64 counter)
# -> ~1-3s delay between the framework's off command and the panel actually black. The framework
# does NOT give a "display off" signal that reaches the kernel promptly (the HWC blank is a no-op for the panel).
#
# RELIABLE SIGNAL: the framework sets BRIGHTNESS to 0 exactly on screen off (normal min=10, 0=off),
# and that reaches gen_panel_backlight_update_status. FIX (mirror of V63): when brightness==0 and the
# state is PM_SUSPEND_ON, fire request_suspend_state(PM_SUSPEND_MEM) via a worker -> early_suspend
# PROMPT -> panel off immediately. The full mem suspend is still gated by the HAL (unchanged);
# we only bring forward the early_suspend (panel off). Idempotent.
import sys

SRC = "/home/lineage/android/lineage-17.1/kernel/samsung/gtexswifi/drivers/video/backlight/gen_panel/gen-panel-bl.c"
s = open(SRC, encoding="utf-8", errors="surrogateescape").read()

if "V65" in s:
    print("V65_ALREADY"); sys.exit(0)

# 1) includes
INC_ANCHOR = "#include <linux/module.h>\n"
INC_NEW = ("#include <linux/module.h>\n"
           "#include <linux/earlysuspend.h> /* V65 */\n"
           "#include <linux/workqueue.h> /* V65 */\n")
if INC_ANCHOR not in s:
    print("V65_ERROR: no encuentro #include <linux/module.h>"); sys.exit(1)
s = s.replace(INC_ANCHOR, INC_NEW, 1)

# 2) worker + DECLARE_WORK justo antes de update_status
FUNC_ANCHOR = "static int gen_panel_backlight_update_status(struct backlight_device *bd)\n{"
WORKER = ("/* V65 (Opcion A): apagar el panel de inmediato en pantalla-off. Espejo del resume de\n"
          " * V63. El brillo=0 es la senal fiable de pantalla-off; forzamos el early_suspend\n"
          " * (panel off) prompt en vez de esperar a que el HAL suspenda tras liberar wakelocks. */\n"
          "static void gen_panel_off_work_func(struct work_struct *w)\n"
          "{\n"
          "\tif (get_suspend_state() == PM_SUSPEND_ON)\n"
          "\t\trequest_suspend_state(PM_SUSPEND_MEM);\n"
          "}\n"
          "static DECLARE_WORK(gen_panel_off_work, gen_panel_off_work_func); /* V65 */\n\n"
          + FUNC_ANCHOR)
if FUNC_ANCHOR not in s:
    print("V65_ERROR: no encuentro gen_panel_backlight_update_status"); sys.exit(1)
s = s.replace(FUNC_ANCHOR, WORKER, 1)

# 3) trigger tras set_brightness
CALL_ANCHOR = "\tgen_panel_backlight_set_brightness(bd, brightness);\n\n\treturn 0;\n}"
CALL_NEW = ("\tgen_panel_backlight_set_brightness(bd, brightness);\n\n"
            "\tif (brightness == 0 && get_suspend_state() == PM_SUSPEND_ON) /* V65 */\n"
            "\t\tschedule_work(&gen_panel_off_work);\n\n"
            "\treturn 0;\n}")
if CALL_ANCHOR not in s:
    print("V65_ERROR: cannot find the expected end of update_status"); sys.exit(1)
s = s.replace(CALL_ANCHOR, CALL_NEW, 1)

open(SRC, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V65_APPLIED -> panel-off prompt en brillo=0 (gen-panel-bl.c)")
