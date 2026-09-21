#!/usr/bin/env python3
"""V67: implement HWC2OnFbAdapter display power and bridge fb_blank to wake.

The device runs HWC2OnFbAdapter, not the installed Spreadtrum HWC1 module.
Its stock setPowerMode hook explicitly pretends success without touching fb0.
V67 sends FBIOBLANK for ON/OFF and makes kernel unblank cancel/complete the
legacy early-suspend state machine so panel and touch end in the awake state.
"""

import sys


ROOT = "/home/lineage/android/lineage-17.1"
ADAPTER = (
    ROOT
    + "/hardware/interfaces/graphics/composer/2.1/utils/"
      "hwc2onfbadapter/HWC2OnFbAdapter.cpp"
)
KERNEL = (
    ROOT
    + "/kernel/samsung/gtexswifi/drivers/video/sprdfb/sprdfb_main.c"
)

adapter = open(ADAPTER, encoding="utf-8", errors="surrogateescape").read()
kernel = open(KERNEL, encoding="utf-8", errors="surrogateescape").read()

adapter_done = "V67 HWC2 fb power mode" in adapter
kernel_done = "V67 fb_blank cancelling pending legacy suspend" in kernel
if adapter_done and kernel_done:
    print("V67_ALREADY")
    sys.exit(0)
if adapter_done != kernel_done:
    print("V67_ERROR: partially applied tree")
    sys.exit(1)

old_include = """#include <inttypes.h>
#include <time.h>
"""
new_include = """#include <inttypes.h>
#include <errno.h>
#include <time.h>
"""
if old_include not in adapter:
    print("V67_ERROR: adapter include anchor not found")
    sys.exit(1)

old_hook = """int32_t setPowerModeHook(hwc2_device_t* device, hwc2_display_t display, int32_t /*mode*/) {
    auto& adapter = HWC2OnFbAdapter::cast(device);
    if (adapter.getDisplayId() != display) {
        return HWC2_ERROR_BAD_DISPLAY;
    }

    // pretend that it works
    return HWC2_ERROR_NONE;
}
"""
new_hook = """int32_t setPowerModeHook(hwc2_device_t* device, hwc2_display_t display, int32_t mode) {
    auto& adapter = HWC2OnFbAdapter::cast(device);
    if (adapter.getDisplayId() != display) {
        return HWC2_ERROR_BAD_DISPLAY;
    }

    int blank;
    switch (mode) {
        case HWC2_POWER_MODE_OFF:
            blank = FB_BLANK_POWERDOWN;
            break;
        case HWC2_POWER_MODE_ON:
            blank = FB_BLANK_UNBLANK;
            break;
        case HWC2_POWER_MODE_DOZE:
        case HWC2_POWER_MODE_DOZE_SUSPEND:
            // getDozeSupportHook reports false for this framebuffer adapter.
            return HWC2_ERROR_UNSUPPORTED;
        default:
            return HWC2_ERROR_BAD_PARAMETER;
    }

    int fbfd = ::open("/dev/graphics/fb0", O_RDWR | O_CLOEXEC);
    if (fbfd < 0) {
        fbfd = ::open("/dev/fb0", O_RDWR | O_CLOEXEC);
    }
    if (fbfd < 0) {
        ALOGE("V67 HWC2 fb power mode %d: open failed errno=%d", mode, errno);
        return HWC2_ERROR_NO_RESOURCES;
    }

    const int error = ioctl(fbfd, FBIOBLANK, blank);
    const int savedErrno = errno;
    ::close(fbfd);
    if (error < 0) {
        ALOGE("V67 HWC2 fb power mode %d: FBIOBLANK failed errno=%d", mode, savedErrno);
        return HWC2_ERROR_NO_RESOURCES;
    }

    ALOGI("V67 HWC2 fb power mode %d complete (blank=%d)", mode, blank);
    return HWC2_ERROR_NONE;
}
"""
if old_hook not in adapter:
    print("V67_ERROR: exact no-op setPowerModeHook not found")
    sys.exit(1)

old_blank = """static int sprdfb_blank(int blank, struct fb_info *info)
{
\tstruct sprdfb_device *dev = info->par;

\tpr_info("%s, %s\\n", __func__,
\t\t\tblank == FB_BLANK_UNBLANK ? "unblank" : "blank");

\tsprdfb_power(dev, blank == FB_BLANK_UNBLANK ? 1 : 0);

\tif (blank == FB_BLANK_UNBLANK)
\t\tdev->ctrl->refresh(dev);

\treturn 0;
}
"""
new_blank = """static int sprdfb_blank(int blank, struct fb_info *info)
{
\tstruct sprdfb_device *dev = info->par;
\tconst bool unblank = blank == FB_BLANK_UNBLANK;

\tpr_info("V67 %s, %s\\n", __func__, unblank ? "unblank" : "blank");

\t/* FBIOBLANK is the actual Android 10 HWC2OnFbAdapter power path on
\t * gtexswifi.  On wake, cancel a queued early_suspend or arrange the
\t * complete late_resume if handlers have already started. */
\tif (unblank && get_suspend_state() != PM_SUSPEND_ON) {
\t\tpr_info("V67 fb_blank cancelling pending legacy suspend\\n");
\t\trequest_suspend_state(PM_SUSPEND_ON);
\t}

\tsprdfb_power(dev, unblank ? 1 : 0);

\tif (unblank)
\t\tdev->ctrl->refresh(dev);

\tpr_info("V67 fb_blank %s complete\\n", unblank ? "ON" : "OFF");
\treturn 0;
}
"""
if old_blank not in kernel:
    print("V67_ERROR: exact sprdfb_blank block not found")
    sys.exit(1)
if "V66 HWC power-mode request" not in kernel:
    print("V67_ERROR: required cumulative V66 kernel change missing")
    sys.exit(1)

adapter = adapter.replace(old_include, new_include, 1)
adapter = adapter.replace(old_hook, new_hook, 1)
kernel = kernel.replace(old_blank, new_blank, 1)

open(ADAPTER, "w", encoding="utf-8", errors="surrogateescape").write(adapter)
open(KERNEL, "w", encoding="utf-8", errors="surrogateescape").write(kernel)
print("V67_APPLIED -> HWC2 FBIOBLANK + race-safe kernel unblank")
