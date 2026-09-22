#!/usr/bin/env python3
# V35 (phase 6.1): framework auto-boot. The framework (zygote/system_server) is
# functional (validated: `ctl.start zygote` by hand brings system_server up to 32 services) but
# does not start on its own: the init.rc triggers depend on `ro.crypto.state`, which at runtime
# is EMPTY:
#   on zygote-start && property:ro.crypto.state=unencrypted  -> start zygote  (init.rc:638)
#   on nonencrypted                                          -> class_start main (init.rc:770)
# /data is `formattable` (fstab without encryptable/fileencryption); mount_all does not emit the
# crypto event that would set ro.crypto.state=unencrypted + trigger nonencrypted.
#
# Fix: at the END of `on post-fs-data` of the ramdisk (the device's init.sc8830.rc, where /data
# is already mounted and structured and `setprop vold.post_fs_data_done 1` is done), force:
#   setprop ro.crypto.state unencrypted   -> habilita `on zygote-start && ...unencrypted`
#   trigger nonencrypted                  -> dispara class_start main + late_start
# Ramdisk change -> boot.img CHANGES (on top of V31's FDA kernel). Idempotent.
import sys

F = "/home/lineage/android/lineage-17.1/device/samsung/gtexswifi/rootdir/init.sc8830.rc"
s = open(F, encoding="utf-8", errors="surrogateescape").read()

if "V35" in s:
    print("V35_ALREADY_PRESENT"); sys.exit(0)

anchor = (
    "        restorecon_recursive /data/security\n"
    "    # ]\n"
    "\n"
    "on early-boot\n"
)
new = (
    "        restorecon_recursive /data/security\n"
    "    # ]\n"
    "\n"
    "    # V35 (phase 6.1): /data unencrypted (formattable) no dispara el evento crypto\n"
    "    # de mount_all -> ro.crypto.state queda vacio y el framework no auto-arranca.\n"
    "    # Forzarlo aqui, con /data ya listo (tras vold.post_fs_data_done).\n"
    "    setprop ro.crypto.state unencrypted\n"
    "    trigger nonencrypted\n"
    "\n"
    "on early-boot\n"
)

if s.count(anchor) != 1:
    print("V35_ANCHOR_ERROR count=%d" % s.count(anchor)); sys.exit(1)

s = s.replace(anchor, new, 1)
open(F, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V35_APPLIED")
