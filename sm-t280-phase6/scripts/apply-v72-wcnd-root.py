#!/usr/bin/env python3
# V72 (Bluetooth: wcnd must start as root). On top of V71. Changes system/etc/init/wcnd.rc
# (PRODUCT_COPY_FILES -> /system/etc/init/wcnd.rc, goes in system.img; host_init_verifier does not validate it).
#
# CAUSE (verified on HW with V71):
#   The combo WiFi+BT chip (Marlin sc2331, "CP2") is governed by the 'wcnd' daemon. libbt-vendor requests
#   "wcn BT-OPEN" from wcnd over a socket; wcnd has to start/confirm CP2 and answer. If CP2 is
#   in ASSERT and wcnd cannot reset it, it never answers -> libbt "start_cp2: get -1 bytes" ->
#   bt_hci "startup_timer_expired" (3s) -> SIGABRT de com.android.bluetooth -> BT nunca sube.
#   logcat WCND: "Error downing interface: Operation not permitted"
#                "Error Wifi driver cannot unloaded in 20 seconds" / "reboot CP2 Fail !"
#   /proc/<wcnd>/status: Uid 1000, CapEff 0000000000000000.
#   The wcnd binary does setuid()+capset() ITSELF (strings: setuid, capset): it is designed to
#   start as root and drop to 'system' keeping CAP_NET_ADMIN/CAP_NET_RAW (ifdown wlan0 in the
#   reset of CP2). The rc's own comment says so ("we will start as root and wcnd will switch
#   to user system") and in Samsung's stock 5.1 init.sc8830.rc 'user system' is COMMENTED OUT.
#   The cm14-inherited rc uncommented it -> wcnd without caps -> CP2 unrecoverable after the first assert.
#   TESTED ON HW: relaunching /system/bin/wcnd as root -> Uid 1000, CapEff 0x3020
#   (NET_ADMIN|NET_RAW|KILL) and CP2 starts/resets correctly (loopcheck OK, CP2_STARTED).
#
# FIX: remove 'user system' from the wcnd service (init launches it as root; wcnd drops to system on its own).
#      Also 'net_bt_stack' -> 3008 (AID nonexistent in A10; init aborts parsing 'group' at
#      that point, the following groups would be lost). Idempotent.
import sys
from pathlib import Path

RC = Path("/home/lineage/android/lineage-17.1/device/samsung/gtexswifi/system/etc/init/wcnd.rc")

OLD = """service wcnd /system/bin/wcnd
    class core
    #   we will start as root and wcnd will switch to user system
    user system
    group system shell wifi inet bluetooth net_bt_stack
    oneshot
"""

NEW = """service wcnd /system/bin/wcnd
    class core
    #   we will start as root and wcnd will switch to user system
    #   V72: sin 'user system' -> arranca root, wcnd hace setuid(system)+capset conservando
    #   CAP_NET_ADMIN; con 'user system' queda CapEff=0 y no puede resetear CP2 (BT nunca sube)
    group system shell wifi inet bluetooth 3008
    oneshot
"""

s = RC.read_text(encoding="utf-8", errors="surrogateescape")
if "V72: sin 'user system'" in s:
    print("V72_ALREADY"); sys.exit(0)
if OLD not in s:
    print("V72_ERROR: unexpected 'service wcnd' block"); sys.exit(1)
s = s.replace(OLD, NEW, 1).replace("net_bt_stack", "3008")
RC.write_text(s, encoding="utf-8", errors="surrogateescape")
print("V72_APPLIED -> wcnd starts as root; net_bt_stack -> 3008")
