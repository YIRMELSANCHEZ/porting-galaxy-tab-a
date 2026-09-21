#!/usr/bin/env python3
# V15: (1) caso BINDER_TYPE_PTR en binder_transaction_buffer_release;
#      (2) /data mountable without encryption (formattable) for the diagnostic boot.
# Idempotente.
import sys

KROOT = "/home/lineage/android/lineage-17.1/kernel/samsung/gtexswifi/drivers/staging/android"
C = KROOT + "/binder.c"
FSTAB = "/home/lineage/android/lineage-17.1/device/samsung/gtexswifi/rootdir/fstab.sc8830"

def load(p): return open(p, encoding="utf-8", errors="surrogateescape").read()
def save(p, s): open(p, "w", encoding="utf-8", errors="surrogateescape").write(s)

# (1) binder_transaction_buffer_release: caso PTR.
c = load(C)
mark1 = "case BINDER_TYPE_PTR:\n\t\t\t/* buffer SG: nada que liberar */"
if mark1 in c:
    print("V15_BINDER_ALREADY_PRESENT")
else:
    old = ("\t\tcase BINDER_TYPE_FD:\n"
           "\t\t\tbinder_debug(BINDER_DEBUG_TRANSACTION,\n"
           "\t\t\t\t     \"        fd %d\\n\", fp->handle);\n"
           "\t\t\tif (failed_at)\n"
           "\t\t\t\ttask_close_fd(proc, fp->handle);\n"
           "\t\t\tbreak;\n"
           "\n"
           "\t\tdefault:\n"
           "\t\t\tpr_err(\"transaction release %d bad object type %x\\n\",\n")
    new = ("\t\tcase BINDER_TYPE_FD:\n"
           "\t\t\tbinder_debug(BINDER_DEBUG_TRANSACTION,\n"
           "\t\t\t\t     \"        fd %d\\n\", fp->handle);\n"
           "\t\t\tif (failed_at)\n"
           "\t\t\t\ttask_close_fd(proc, fp->handle);\n"
           "\t\t\tbreak;\n"
           "\t\tcase BINDER_TYPE_PTR:\n"
           "\t\t\t/* buffer SG: nada que liberar */\n"
           "\t\t\tbreak;\n"
           "\n"
           "\t\tdefault:\n"
           "\t\t\tpr_err(\"transaction release %d bad object type %x\\n\",\n")
    if old not in c:
        print("ERROR: could not find the default of buffer_release", file=sys.stderr); sys.exit(2)
    c = c.replace(old, new, 1)
    save(C, c)
    print("V15_BINDER_PTR_RELEASE_OK")

# (2) fstab: /data formattable without encryption.
f = load(FSTAB)
old_line = "/dev/block/platform/sdio_emmc/by-name/userdata  /data        ext4 nosuid,nodev,noatime,noauto_da_alloc,discard,journal_async_commit,errors=panic    wait,check,encryptable=footer"
new_line = "/dev/block/platform/sdio_emmc/by-name/userdata  /data        ext4 nosuid,nodev,noatime,noauto_da_alloc,discard,journal_async_commit,errors=panic    wait,check,formattable"
if "wait,check,formattable" in f:
    print("V15_FSTAB_ALREADY_PRESENT")
elif old_line in f:
    f = f.replace(old_line, new_line, 1)
    save(FSTAB, f)
    print("V15_FSTAB_DATA_OK")
else:
    print("ERROR: could not find the /data line in fstab.sc8830", file=sys.stderr); sys.exit(2)
