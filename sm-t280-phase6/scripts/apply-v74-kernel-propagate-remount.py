#!/usr/bin/env python3
# V74 (STOR1: apps cannot read /sdcard). On top of V73. Changes the KERNEL (fs/pnode.c) -> boot.img.
#
# CAUSE (verified on HW, factory configuration, see results/fase-6/STOR1-FINDINGS.md):
#   vold/sdcard creates the storage views as bind-mounts of the default view and then
#   applies per-mount options to them with remount: read=(gid 9997,mask 0027) write/full=(gid 9997,mask 0007).
#   The remount only updates the remounted vfsmount; the COPIES propagated to other namespaces are
#   updated by propagate_remount() (fs/pnode.c). On this kernel 3.10.108 the loop is:
#       for (m = first_slave(mnt); m->mnt_slave.next != &mnt->mnt_slave_list; m = next_slave(m))
#   The condition checks whether the NEXT is the head, so it never processes the LAST slave of the
#   list (with a single slave it processes none). Slaves are inserted at the head, so the
#   last is the oldest: the zygote namespace (created before vold mounts /storage).
#   Measured: in /proc/<zygote>/mountinfo the read/write/full views stay gid=1015,mask=6 (restricted
#   view) while init/vold/system_server/SystemUI have them correct. Each app forks from zygote
#   and inherits (clone_mnt_data) the broken view -> MediaProvider: "Failed to visit /storage/emulated/0:
#   AccessDeniedException" -> MediaStore _size=NULL (the gallery shows 0 B / a blank image), and
#   no app reads /sdcard even with the permissions. Confirmed by remounting inside zygote's ns with
#   nsenter: the new processes are born with gid=9997,mask=7, the scanner stops failing and _size is filled.
#
# FIX: port a 3.10 de "ANDROID: mnt: Propagate remount correctly" (kernel/common, Daniel Rosenberg):
#   walk the propagation tree of the mount's PARENT and, in each namespace, locate the mount
#   that hangs off the same point (__lookup_mnt) and copy its data. Covers all namespaces
#   regardless of the order/nesting of the slave list. Differences from upstream 4.4:
#   __lookup_mnt has 3 args in 3.10 (dir=1) and the int prototype in pnode.h is kept.
#   The caller (do_remount) already holds namespace_lock + vfsmount_lock, a requirement of __lookup_mnt.
# Idempotente.
import sys
from pathlib import Path

SRC = Path("/home/lineage/android/lineage-17.1/kernel/samsung/gtexswifi/fs/pnode.c")

OLD = """int propagate_remount(struct mount *mnt) {
\tstruct mount *m;
\tstruct super_block *sb = mnt->mnt.mnt_sb;
\tint ret = 0;

\tif (sb->s_op->copy_mnt_data) {
\t\tfor (m = first_slave(mnt); m->mnt_slave.next != &mnt->mnt_slave_list; m = next_slave(m)) {
\t\t\tsb->s_op->copy_mnt_data(m->mnt.data, mnt->mnt.data);
\t\t}
\t}

\treturn ret;
}
"""

NEW = """/*
 * V74 (gtexswifi): port de "ANDROID: mnt: Propagate remount correctly".
 * El bucle original sobre mnt_slave_list omitia el ultimo esclavo (el namespace de
 * zygote), dejando las vistas de /storage de todas las apps con la mascara restringida.
 * Recorremos el arbol de propagacion del padre y actualizamos el montaje equivalente
 * en cada namespace. Caller: do_remount() con namespace_lock + vfsmount_lock.
 */
int propagate_remount(struct mount *mnt) {
\tstruct mount *parent = mnt->mnt_parent;
\tstruct mount *p, *m;
\tstruct super_block *sb = mnt->mnt.mnt_sb;

\tif (!sb->s_op->copy_mnt_data)
\t\treturn 0;

\tfor (p = propagation_next(parent, parent); p;
\t     p = propagation_next(p, parent)) {
\t\tm = __lookup_mnt(&p->mnt, mnt->mnt_mountpoint, 1);
\t\tif (m && m->mnt.data)
\t\t\tsb->s_op->copy_mnt_data(m->mnt.data, mnt->mnt.data);
\t}

\treturn 0;
}
"""

s = SRC.read_text(encoding="utf-8", errors="surrogateescape")
if "V74 (gtexswifi): port de" in s:
    print("V74_ALREADY"); sys.exit(0)
if OLD not in s:
    print("V74_ERROR: propagate_remount does not match the expected text"); sys.exit(1)
if "static struct mount *propagation_next" not in s:
    print("V74_ERROR: falta propagation_next en pnode.c"); sys.exit(1)
SRC.write_text(s.replace(OLD, NEW, 1), encoding="utf-8", errors="surrogateescape")
print("V74_APPLIED -> propagate_remount walks the parent's propagation tree")
