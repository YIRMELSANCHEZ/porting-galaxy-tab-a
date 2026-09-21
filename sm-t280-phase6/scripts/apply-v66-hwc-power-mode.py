#!/usr/bin/env python3
"""V66: make the Spreadtrum HWC power-mode ioctl control the panel.

SurfaceFlinger/HWC already sends SPRD_FB_SET_POWER_MODE synchronously for
logical display OFF/ON transitions.  The stock kernel only logged the ioctl,
leaving physical panel blanking coupled to delayed legacy early_suspend.

V66 makes OFF/SUSPEND power the framebuffer down immediately.  NORMAL/DOZE
first cancel a pending legacy suspend, then power the framebuffer up.  There
is deliberately no deferred OFF worker, so a rapid OFF->ON cannot leave a
stale blank operation queued after the wake request.
"""

import sys


FB = (
    "/home/lineage/android/lineage-17.1/kernel/samsung/gtexswifi/"
    "drivers/video/sprdfb/sprdfb_main.c"
)

source = open(FB, encoding="utf-8", errors="surrogateescape").read()

if "V66 HWC power-mode request" in source:
    print("V66_ALREADY")
    sys.exit(0)

old = """\tcase SPRD_FB_SET_POWER_MODE:
\t\tresult = copy_from_user(&power_mode, argp, sizeof(power_mode));
\t\tprintk("sprdfb: [%s] : SPRD_FB_SET_POWER_MODE (%d)\\n", __FUNCTION__, power_mode);
\t\tbreak;
"""

new = """\tcase SPRD_FB_SET_POWER_MODE:
\t\tif (copy_from_user(&power_mode, argp, sizeof(power_mode))) {
\t\t\tpr_err("V66 HWC power-mode copy_from_user failed\\n");
\t\t\tresult = -EFAULT;
\t\t\tbreak;
\t\t}

\t\tpr_info("V66 HWC power-mode request %d\\n", power_mode);
\t\tswitch (power_mode) {
\t\tcase SPRD_FB_POWER_OFF:
\t\tcase SPRD_FB_POWER_SUSPEND:
\t\t\t/* Synchronous OFF: never leave a stale delayed blank that can
\t\t\t * race with a subsequent POWER press.  Legacy early_suspend may
\t\t\t * still run later, but sprdfb_power() is idempotent. */
\t\t\tresult = sprdfb_power(dev, 0);
\t\t\tpr_info("V66 display power OFF complete (%d)\\n", result);
\t\t\tbreak;

\t\tcase SPRD_FB_POWER_NORMAL:
\t\tcase SPRD_FB_POWER_DOZE:
\t\t\t/* Authoritative wake transition.  Clearing the legacy suspend
\t\t\t * request makes a queued early_suspend abort.  If its handlers
\t\t\t * are already running, request_suspend_state() queues the full
\t\t\t * late_resume sequence, restoring touch after the race. */
\t\t\tif (get_suspend_state() != PM_SUSPEND_ON) {
\t\t\t\tpr_info("V66 cancelling pending legacy suspend\\n");
\t\t\t\trequest_suspend_state(PM_SUSPEND_ON);
\t\t\t}

\t\t\tresult = sprdfb_power(dev, 1);
\t\t\tif (!result && dev->enable)
\t\t\t\tresult = dev->ctrl->refresh(dev);
\t\t\tpr_info("V66 display power ON complete (%d)\\n", result);
\t\t\tbreak;

\t\tdefault:
\t\t\tpr_err("V66 invalid HWC power mode %d\\n", power_mode);
\t\t\tresult = -EINVAL;
\t\t\tbreak;
\t\t}
\t\tbreak;
"""

if old not in source:
    print("V66_ERROR: exact no-op SPRD_FB_SET_POWER_MODE block not found")
    sys.exit(1)

if "static int sprdfb_power(struct sprdfb_device *dev, int on);" not in source:
    print("V66_ERROR: sprdfb_power forward declaration missing")
    sys.exit(1)

if "V63: request the complete legacy late_resume" not in source:
    print("V66_ERROR: required V63 full late-resume bridge missing")
    sys.exit(1)

source = source.replace(old, new, 1)
open(FB, "w", encoding="utf-8", errors="surrogateescape").write(source)
print("V66_APPLIED -> synchronous HWC OFF/ON with suspend-race cancellation")
