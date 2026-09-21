#!/usr/bin/env python3
# V16 (diagnostic): neutralize the blocking checkpoint/FBE of post-fs-data in
# init.rc, which depends on vold/keystore (broken) and blocks the creation of the
# /data structure. Without it, post-fs-data does not create /data/misc, /data/* and everything
# falls into a loop. /data goes unencrypted (V15), so checkpoint/installkey are not
# needed for the diagnostic boot. Idempotent.
import sys

RC = "/home/lineage/android/lineage-17.1/system/core/rootdir/init.rc"
s = open(RC, encoding="utf-8", errors="surrogateescape").read()

if "# V16 diag:" in s:
    print("V16_PATCH_ALREADY_PRESENT"); sys.exit(0)

changes = [
    ("    exec - system system -- /system/bin/vdc checkpoint prepareCheckpoint\n",
     "    # V16 diag: checkpoint desactivado (bloqueaba post-fs-data vía vold)\n"),
    ("    installkey /data\n",
     "    # V16 diag: installkey /data desactivado (/data sin cifrado)\n"),
]
applied = 0
for old, new in changes:
    if old in s:
        s = s.replace(old, new, 1); applied += 1
    else:
        print("WARN: not found (may vary): " + old.strip(), file=sys.stderr)

if applied == 0:
    print("ERROR: no change was applied", file=sys.stderr); sys.exit(2)

open(RC, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("V16_PATCH_APPLIED changes=%d" % applied)
