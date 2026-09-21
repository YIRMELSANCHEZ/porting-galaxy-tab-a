#!/usr/bin/env python3
"""V63: request the complete legacy late-resume sequence on Android wake.

V62 proves the physical POWER event reaches PhoneWindowManager.  On wake,
Android 10 turns SurfaceFlinger back on but never writes "on" to the legacy
/sys/power/state interface.  The kernel therefore runs early_suspend but not
late_resume: V61 powers only the framebuffer, leaving touch and other handlers
suspended.  V63 turns the deferred framebuffer recovery into a request for the
normal late_resume work, which resumes every handler in reverse order.
"""

import sys


ROOT = "/home/lineage/android/lineage-17.1/kernel/samsung/gtexswifi"
FB = ROOT + "/drivers/video/sprdfb/sprdfb_main.c"
HEADER = ROOT + "/include/linux/earlysuspend.h"

fb = open(FB, encoding="utf-8", errors="surrogateescape").read()
header = open(HEADER, encoding="utf-8", errors="surrogateescape").read()

if "V63: request the complete legacy late_resume" in fb:
    print("V63_ALREADY")
    sys.exit(0)

old_header = (
    "void register_early_suspend(struct early_suspend *handler);\n"
    "void unregister_early_suspend(struct early_suspend *handler);\n"
)
new_header = (
    "void register_early_suspend(struct early_suspend *handler);\n"
    "void unregister_early_suspend(struct early_suspend *handler);\n"
    "/* Public legacy display-state bridge used by built-in display drivers. */\n"
    "void request_suspend_state(suspend_state_t state);\n"
    "suspend_state_t get_suspend_state(void);\n"
)
if old_header not in header:
    print("V63_ERROR: earlysuspend declarations not found")
    sys.exit(1)
header = header.replace(old_header, new_header, 1)

old_include = "#include <linux/list.h>\n"
new_include = "#include <linux/list.h>\n#include <linux/suspend.h>\n"
if old_include not in header:
    print("V63_ERROR: earlysuspend include anchor not found")
    sys.exit(1)
header = header.replace(old_include, new_include, 1)

old_worker = (
    "static struct sprdfb_device *sprdfb_resume_dev; /* V61 */\n"
    "static void sprdfb_resume_work_func(struct work_struct *w) /* V61 */\n"
    "{\n"
    "\tstruct sprdfb_device *dev = sprdfb_resume_dev;\n"
    "\tif (dev && 0 == dev->enable)\n"
    "\t\tsprdfb_power(dev, 1);\n"
    "}\n"
    "static DECLARE_WORK(sprdfb_resume_work, sprdfb_resume_work_func); /* V61 */\n"
)
new_worker = (
    "static struct sprdfb_device *sprdfb_resume_dev; /* V61 */\n"
    "static void sprdfb_resume_work_func(struct work_struct *w) /* V63 */\n"
    "{\n"
    "\tstruct sprdfb_device *dev = sprdfb_resume_dev;\n"
    "\n"
    "\t/* V63: request the complete legacy late_resume. Android 10 wakes its\n"
    "\t * framework without writing PM_SUSPEND_ON, so V61 resumed only the LCD\n"
    "\t * and left mip4 touch and the other early-suspend clients disabled. */\n"
    "\tif (get_suspend_state() != PM_SUSPEND_ON) {\n"
    "\t\tpr_info(\"V63 requesting full late_resume\\n\");\n"
    "\t\trequest_suspend_state(PM_SUSPEND_ON);\n"
    "\t} else if (dev && 0 == dev->enable) {\n"
    "\t\t/* Defensive fallback for a framebuffer-off state unrelated to the\n"
    "\t\t * legacy early-suspend state machine. */\n"
    "\t\tpr_warn(\"V63 framebuffer off while suspend state is ON; direct resume\\n\");\n"
    "\t\tsprdfb_power(dev, 1);\n"
    "\t}\n"
    "}\n"
    "static DECLARE_WORK(sprdfb_resume_work, sprdfb_resume_work_func); /* V63 */\n"
)
if old_worker not in fb:
    print("V63_ERROR: exact V61 deferred worker not found")
    sys.exit(1)
fb = fb.replace(old_worker, new_worker, 1)

open(HEADER, "w", encoding="utf-8", errors="surrogateescape").write(header)
open(FB, "w", encoding="utf-8", errors="surrogateescape").write(fb)
print("V63_APPLIED -> pan_display requests complete late_resume")
