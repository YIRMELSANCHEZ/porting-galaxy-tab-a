#!/usr/bin/env python3
# V24 (fix definitivo de logd en kernel 3.10). Historia:
#  - V22: cap_set_proc no-fatal -> avanzaba pero moria en setgroups.
#  - V23: user root -> cap_set_proc/setgroups OK, pero moria en setuid(AID_LOGD):
#    drop_privs clears CAP_SETUID from the effective set (cap_set_proc leaves only SETGID/
#    SYSLOG/AUDIT_CONTROL); then setuid(1036) FROM uid 0 needs CAP_SETUID ->
#    EPERM. In the normal flow init already starts logd as uid 1036, so
#    setuid(1036) is a no-op. Launched as root, setuid changes uid and fails.
#
# Fix: (1) .rc vuelve a `user logd` (init pone uid 1036 + grupos). (2) main.cpp:
# non-fatal setgroups/setgid/setuid. With init's uid 1036: setgroups fails ->
# skipped (init's groups are kept, including readproc); setgid(1036) and
# setuid(1036) are no-ops (same id) -> OK. logd runs as AID_LOGD with its
# sockets -> logcat. Combines with the V22 shim (cap_set_proc). Idempotent.
import sys

RC = "/home/lineage/android/lineage-17.1/system/core/logd/logd.rc"
MAIN = "/home/lineage/android/lineage-17.1/system/core/logd/main.cpp"

# --- (1) .rc: user root -> user logd (revierte V23) ---
rc = open(RC, encoding="utf-8", errors="surrogateescape").read()
if "# V24" not in rc:
    old_rc = (
        "    # V23: logd como root; kernel 3.10 sin ambient caps. drop_privs()\n"
        "    # baja a AID_LOGD por si mismo (cap_set_proc/setgroups/setgid ok como root).\n"
    )
    new_rc = (
        "    # V24: logd como uid logd (init); kernel 3.10 sin ambient caps.\n"
        "    # setgroups/setgid/setuid en drop_privs() son no-fatales (main.cpp).\n"
    )
    if rc.count(old_rc) != 1 or rc.count("    user root\n") != 1:
        print("V24_RC_ANCHOR_ERROR c1=%d c2=%d" % (rc.count(old_rc), rc.count("    user root\n"))); sys.exit(1)
    rc = rc.replace(old_rc, new_rc).replace("    user root\n", "    user logd\n", 1)
    open(RC, "w", encoding="utf-8", errors="surrogateescape").write(rc)
    print("V24_RC_APPLIED")
else:
    print("V24_RC_ALREADY_PRESENT")

# --- (2) main.cpp: setgroups/setgid/setuid no-fatales ---
s = open(MAIN, encoding="utf-8", errors="surrogateescape").read()
if "V24 non-fatal" in s:
    print("V24_MAIN_ALREADY_PRESENT"); sys.exit(0)

repls = [
    (
        '    if (setgroups(arraysize(groups), groups) == -1) {\n'
        '        android::prdebug("failed to set AID_READPROC groups");\n'
        '        return -1;\n'
        '    }\n',
        '    if (setgroups(arraysize(groups), groups) == -1) {\n'
        '        android::prdebug("V24 non-fatal: setgroups AID_READPROC failed;"\n'
        '                         " keeping init-provided groups");\n'
        '    }\n',
    ),
    (
        '    if (setgid(AID_LOGD) != 0) {\n'
        '        android::prdebug("failed to set AID_LOGD gid");\n'
        '        return -1;\n'
        '    }\n',
        '    if (setgid(AID_LOGD) != 0) {\n'
        '        android::prdebug("V24 non-fatal: setgid AID_LOGD failed;"\n'
        '                         " continuing");\n'
        '    }\n',
    ),
    (
        '    if (setuid(AID_LOGD) != 0) {\n'
        '        android::prdebug("failed to set AID_LOGD uid");\n'
        '        return -1;\n'
        '    }\n',
        '    if (setuid(AID_LOGD) != 0) {\n'
        '        android::prdebug("V24 non-fatal: setuid AID_LOGD failed;"\n'
        '                         " continuing");\n'
        '    }\n',
    ),
]
for old, _ in repls:
    if s.count(old) != 1:
        print("V24_MAIN_ANCHOR_ERROR count=%d for: %s" % (s.count(old), old.splitlines()[0])); sys.exit(1)
for old, new in repls:
    s = s.replace(old, new)
open(MAIN, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V24_MAIN_APPLIED")
