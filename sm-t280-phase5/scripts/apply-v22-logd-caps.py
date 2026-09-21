#!/usr/bin/env python3
# V22 (diagnostic/unblock): logd falls into a status-1 loop on kernel 3.10.
# Exact cause (dmesg): "logd: failed to set CAP_SETGID, CAP_SYSLOG or
# CAP_AUDIT_CONTROL (1)" -> drop_privs() devuelve -1 -> main() sale EXIT_FAILURE.
# On kernel 3.10 raising those capabilities (ambient/prctl) fails with
# EPERM. Without logd there is no logcat, and SurfaceFlinger hangs initializing the
# display leaving no visible trace. Same pattern as the pthread shim (V19):
# make the two cap_set_proc of drop_privs NON-FATAL (warn + continue). logd
# still does setgid/setuid to AID_LOGD (which work as root) and serves the
# main/system/crash buffers over its sockets -> logcat returns. Idempotent.
import sys

F = "/home/lineage/android/lineage-17.1/system/core/logd/main.cpp"
s = open(F, encoding="utf-8", errors="surrogateescape").read()

MARK = "V22 non-fatal"
if MARK in s:
    print("V22_PATCH_ALREADY_PRESENT"); sys.exit(0)

# Bloque 1: fijar SETGID/SYSLOG/AUDIT_CONTROL en PERMITTED/EFFECTIVE.
old1 = (
    "    if (cap_set_proc(caps.get()) < 0) {\n"
    "        android::prdebug(\n"
    "            \"failed to set CAP_SETGID, CAP_SYSLOG or CAP_AUDIT_CONTROL (%d)\",\n"
    "            errno);\n"
    "        return -1;\n"
    "    }\n"
)
new1 = (
    "    if (cap_set_proc(caps.get()) < 0) {\n"
    "        android::prdebug(\n"
    "            \"V22 non-fatal: cap_set_proc SETGID/SYSLOG/AUDIT_CONTROL failed\"\n"
    "            \" (%d) on legacy kernel; continuing without them\", errno);\n"
    "    }\n"
)

# Block 2: clear CAP_SETGID after the setuid to AID_LOGD.
old2 = (
    "    if (cap_set_proc(caps.get()) < 0) {\n"
    "        android::prdebug(\"failed to clear CAP_SETGID (%d)\", errno);\n"
    "        return -1;\n"
    "    }\n"
)
new2 = (
    "    if (cap_set_proc(caps.get()) < 0) {\n"
    "        android::prdebug(\"V22 non-fatal: clear CAP_SETGID failed (%d);\"\n"
    "                         \" continuing\", errno);\n"
    "    }\n"
)

for old in (old1, old2):
    if s.count(old) != 1:
        print("V22_PATCH_ANCHOR_ERROR count=%d for block starting: %s"
              % (s.count(old), old.splitlines()[0])); sys.exit(1)

s = s.replace(old1, new1).replace(old2, new2)
open(F, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V22_PATCH_APPLIED")
