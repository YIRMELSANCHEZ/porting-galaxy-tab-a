#!/usr/bin/env python3
# Revert of V65: undoes the gen-panel-bl.c hook (it did not fix the power-off delay because
# the framework does not write brightness 0 early). Leaves the file as it was (V63/V64 state of the other
# agente). Idempotente.
import sys

SRC = "/home/lineage/android/lineage-17.1/kernel/samsung/gtexswifi/drivers/video/backlight/gen_panel/gen-panel-bl.c"
s = open(SRC, encoding="utf-8", errors="surrogateescape").read()

if "V65" not in s:
    print("V65_NOT_PRESENT (already reverted)"); sys.exit(0)

# 1) quitar includes
s = s.replace("#include <linux/earlysuspend.h> /* V65 */\n", "", 1)
s = s.replace("#include <linux/workqueue.h> /* V65 */\n", "", 1)

# 2) remove worker + DECLARE_WORK (whole block, leaves the function anchor)
WORKER = ("/* V65 (Opcion A): apagar el panel de inmediato en pantalla-off. Espejo del resume de\n"
          " * V63. El brillo=0 es la senal fiable de pantalla-off; forzamos el early_suspend\n"
          " * (panel off) prompt en vez de esperar a que el HAL suspenda tras liberar wakelocks. */\n"
          "static void gen_panel_off_work_func(struct work_struct *w)\n"
          "{\n"
          "\tif (get_suspend_state() == PM_SUSPEND_ON)\n"
          "\t\trequest_suspend_state(PM_SUSPEND_MEM);\n"
          "}\n"
          "static DECLARE_WORK(gen_panel_off_work, gen_panel_off_work_func); /* V65 */\n\n")
s = s.replace(WORKER, "", 1)

# 3) remove the trigger after set_brightness
TRIG = ("\n\tif (brightness == 0 && get_suspend_state() == PM_SUSPEND_ON) /* V65 */\n"
        "\t\tschedule_work(&gen_panel_off_work);\n")
s = s.replace(TRIG, "", 1)

if "V65" in s:
    print("V65_REVERT_WARN: quedan restos de V65, revisar manualmente"); sys.exit(1)

open(SRC, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V65_REVERTED -> gen-panel-bl.c restaurado (estado V63/V64)")
