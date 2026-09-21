#!/usr/bin/env python3
"""V64: gate /sys/power/state writes with Android's userspace wakelock counter.

Android 10's system-suspend service normally delegates wake locks to kernels
that do not tie /sys/power/state writes to legacy early-suspend.  The SM-T280
3.10 kernel does tie them together, so the service's 100 ms suspend retries
re-run early_suspend even while PowerManager says the display is awake.

Using SystemSuspend's existing userspace counter keeps the suspend thread
blocked while the display (or another Android wake lock) is active.  V63 can
then perform one complete late_resume without an immediate sleep request.
"""

from pathlib import Path
import sys


SOURCE = Path(
    "/home/lineage/android/lineage-17.1/"
    "system/hardware/interfaces/suspend/1.0/default/main.cpp"
)

text = SOURCE.read_text(encoding="utf-8", errors="surrogateescape")

if "V64: userspace suspend counter enabled" in text:
    print("V64_ALREADY")
    sys.exit(0)

old = """    sp<SystemSuspend> suspend =
        new SystemSuspend(std::move(wakeupCountFd), std::move(stateFd), 100 /* maxStatsEntries */,
                          100ms /* baseSleepTime */, suspendControl, false /* mUseSuspendCounter*/);
"""
new = """    // V64: this 3.10 kernel maps every /sys/power/state write to the
    // legacy early-suspend state machine.  Gate writes in userspace so the
    // 100 ms autosuspend retry loop cannot blank an interactive display.
    LOG(INFO) << \"V64: userspace suspend counter enabled\";
    sp<SystemSuspend> suspend =
        new SystemSuspend(std::move(wakeupCountFd), std::move(stateFd), 100 /* maxStatsEntries */,
                          100ms /* baseSleepTime */, suspendControl, true /* mUseSuspendCounter*/);
"""

if old not in text:
    print("V64_ERROR: exact SystemSuspend constructor block not found")
    sys.exit(1)

SOURCE.write_text(text.replace(old, new, 1), encoding="utf-8", errors="surrogateescape")
print("V64_APPLIED -> SystemSuspend uses userspace wake-lock counter")
