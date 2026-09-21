#!/usr/bin/env python3
# V23 (logd root fix): on kernel 3.10 ambient capabilities do NOT work.
# logd.rc launches logd as `user logd` (uid 1036) + `capabilities SYSLOG
# AUDIT_CONTROL SETGID` via ambient; not being applied, logd runs without effective
# CAP_SETGID -> cap_set_proc fails (the V22 shim masked it) and then setgroups()/
# setgid() to AID_LOGD also fail -> "failed to set AID_READPROC groups" ->
# exit status 1 in a loop -> no logcat.
#
# Fix: launch logd as ROOT (user root) and remove the `capabilities` line; its
# own drop_privs() (main.cpp) CAN cap_set_proc to the subset (root),
# setgroups, and setgid/setuid to AID_LOGD. The V22 shim stays as a safety net.
# Change in /system/etc/init/logd.rc (system.img). Idempotent.
import sys

F = "/home/lineage/android/lineage-17.1/system/core/logd/logd.rc"
s = open(F, encoding="utf-8", errors="surrogateescape").read()

if "# V23: logd como root" in s:
    print("V23_PATCH_ALREADY_PRESENT"); sys.exit(0)

# Only the main service block `logd` (not logd-reinit or logd-auditctl).
old = (
    "service logd /system/bin/logd\n"
    "    socket logd stream 0666 logd logd\n"
    "    socket logdr seqpacket 0666 logd logd\n"
    "    socket logdw dgram+passcred 0222 logd logd\n"
    "    file /proc/kmsg r\n"
    "    file /dev/kmsg w\n"
    "    user logd\n"
    "    group logd system package_info readproc\n"
    "    capabilities SYSLOG AUDIT_CONTROL SETGID\n"
    "    writepid /dev/cpuset/system-background/tasks\n"
)
new = (
    "service logd /system/bin/logd\n"
    "    # V23: logd como root; kernel 3.10 sin ambient caps. drop_privs()\n"
    "    # baja a AID_LOGD por si mismo (cap_set_proc/setgroups/setgid ok como root).\n"
    "    socket logd stream 0666 logd logd\n"
    "    socket logdr seqpacket 0666 logd logd\n"
    "    socket logdw dgram+passcred 0222 logd logd\n"
    "    file /proc/kmsg r\n"
    "    file /dev/kmsg w\n"
    "    user root\n"
    "    group logd system package_info readproc\n"
    "    writepid /dev/cpuset/system-background/tasks\n"
)

if s.count(old) != 1:
    print("V23_PATCH_ANCHOR_ERROR count=%d" % s.count(old)); sys.exit(1)

s = s.replace(old, new)
open(F, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V23_PATCH_APPLIED")
