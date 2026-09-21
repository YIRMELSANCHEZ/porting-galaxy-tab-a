#!/usr/bin/env python3
# V31 (graphics ROOT CAUSE, in the KERNEL). With V30 it was proven that the gralloc allocates
# the buffer via ION successfully (result=0) but the binder REPLY to SurfaceFlinger fails:
#   kernel: binder: 216:287 got transaction with invalid object type/size, 66646185
#           binder: send failed reply for transaction 254 to 229:229
# 0x66646185 = B_PACK_CHARS('f','d','a') = BINDER_TYPE_FDA (array de fds). HIDL usa
# FDA to pass the buffer's native_handle (with its fd) between processes. The binder backport
# (V13/V14/V15) added multi-device + scatter-gather (BINDER_TYPE_PTR) but
# NOT FDA -> binder_object_size(FDA)=0 -> "invalid object type" -> reply fails ->
# GraphicBufferAllocator returns NO_RESOURCES(5). It is NOT graphics: it is the kernel.
#
# V31 backports BINDER_TYPE_FDA: type + struct (uapi), binder_object_size, translation
# in binder_transaction (finds the PTR parent buffer and translates each fd as BINDER_TYPE_FD),
# and a release case. Recompiles the kernel -> boot.img CHANGES (first boot change since
# V20). Idempotente.
import sys

UAPI = "/home/lineage/android/lineage-17.1/kernel/samsung/gtexswifi/drivers/staging/android/uapi/binder.h"
BC   = "/home/lineage/android/lineage-17.1/kernel/samsung/gtexswifi/drivers/staging/android/binder.c"

# ---------- uapi/binder.h ----------
u = open(UAPI, encoding="utf-8", errors="surrogateescape").read()
if "BINDER_TYPE_FDA" not in u:
    u = u.replace(
        "\tBINDER_TYPE_PTR\t\t= B_PACK_CHARS('p', 't', '*', B_TYPE_LARGE),\n};",
        "\tBINDER_TYPE_PTR\t\t= B_PACK_CHARS('p', 't', '*', B_TYPE_LARGE),\n"
        "\tBINDER_TYPE_FDA\t\t= B_PACK_CHARS('f', 'd', 'a', B_TYPE_LARGE),\n};", 1)
    u = u.replace(
        "struct binder_buffer_object {\n"
        "\tstruct binder_object_header\thdr;\n"
        "\t__u32\t\t\t\tflags;\n"
        "\tbinder_uintptr_t\t\tbuffer;\n"
        "\tbinder_size_t\t\t\tlength;\n"
        "\tbinder_size_t\t\t\tparent;\n"
        "\tbinder_size_t\t\t\tparent_offset;\n"
        "};\n",
        "struct binder_buffer_object {\n"
        "\tstruct binder_object_header\thdr;\n"
        "\t__u32\t\t\t\tflags;\n"
        "\tbinder_uintptr_t\t\tbuffer;\n"
        "\tbinder_size_t\t\t\tlength;\n"
        "\tbinder_size_t\t\t\tparent;\n"
        "\tbinder_size_t\t\t\tparent_offset;\n"
        "};\n\n"
        "/* V31: fd array object (BINDER_TYPE_FDA) */\n"
        "struct binder_fd_array_object {\n"
        "\tstruct binder_object_header\thdr;\n"
        "\t__u32\t\t\t\tpad;\n"
        "\tbinder_size_t\t\t\tnum_fds;\n"
        "\tbinder_size_t\t\t\tparent;\n"
        "\tbinder_size_t\t\t\tparent_offset;\n"
        "};\n", 1)
    open(UAPI, "w", encoding="utf-8", errors="surrogateescape").write(u)
    print("V31_UAPI_APPLIED")
else:
    print("V31_UAPI_ALREADY")

# ---------- binder.c ----------
c = open(BC, encoding="utf-8", errors="surrogateescape").read()
if "V31" in c:
    print("V31_BINDERC_ALREADY"); sys.exit(0)

# (a) binder_object_size
osz_old = ("\tcase BINDER_TYPE_PTR:\n"
           "\t\treturn sizeof(struct binder_buffer_object);\n"
           "\tdefault:\n"
           "\t\treturn 0;\n")
osz_new = ("\tcase BINDER_TYPE_PTR:\n"
           "\t\treturn sizeof(struct binder_buffer_object);\n"
           "\tcase BINDER_TYPE_FDA: /* V31 */\n"
           "\t\treturn sizeof(struct binder_fd_array_object);\n"
           "\tdefault:\n"
           "\t\treturn 0;\n")
if c.count(osz_old) != 1:
    print("V31_OSZ_ANCHOR_ERROR count=%d" % c.count(osz_old)); sys.exit(1)
c = c.replace(osz_old, osz_new, 1)

# (b) binder_transaction: FDA translation, insert before the 'default:' after the PTR case
tr_anchor = (
    "\t\t\tsg_bufp += ALIGN(bp->length, sizeof(u64));\n"
    "\t\t} break;\n\n"
    "\t\tdefault:\n"
    "\t\t\tbinder_user_error(\"%d:%d got transaction with invalid object type, %x\\n\",\n"
)
tr_fda = (
    "\t\t\tsg_bufp += ALIGN(bp->length, sizeof(u64));\n"
    "\t\t} break;\n\n"
    "\t\tcase BINDER_TYPE_FDA: { /* V31: fd array */\n"
    "\t\t\tstruct binder_fd_array_object *fda =\n"
    "\t\t\t\t(struct binder_fd_array_object *)fp;\n"
    "\t\t\tbinder_size_t parent_index, fd_buf_size;\n"
    "\t\t\tstruct binder_buffer_object *parent;\n"
    "\t\t\tu8 *parent_buffer;\n"
    "\t\t\tu32 *fd_array;\n"
    "\t\t\tsize_t fd_index;\n\n"
    "\t\t\tparent_index = (binder_size_t)(offp - off_start);\n"
    "\t\t\tif (fda->parent >= parent_index) {\n"
    "\t\t\t\tbinder_user_error(\"%d:%d BINDER_TYPE_FDA bad parent index\\n\",\n"
    "\t\t\t\t\tproc->pid, thread->pid);\n"
    "\t\t\t\treturn_error = BR_FAILED_REPLY;\n"
    "\t\t\t\tgoto err_bad_offset;\n"
    "\t\t\t}\n"
    "\t\t\tparent = (struct binder_buffer_object *)\n"
    "\t\t\t\t(t->buffer->data + off_start[fda->parent]);\n"
    "\t\t\tif (parent->hdr.type != BINDER_TYPE_PTR) {\n"
    "\t\t\t\tbinder_user_error(\"%d:%d BINDER_TYPE_FDA parent not PTR\\n\",\n"
    "\t\t\t\t\tproc->pid, thread->pid);\n"
    "\t\t\t\treturn_error = BR_FAILED_REPLY;\n"
    "\t\t\t\tgoto err_bad_offset;\n"
    "\t\t\t}\n"
    "\t\t\tif (fda->num_fds >= (SIZE_MAX / sizeof(u32))) {\n"
    "\t\t\t\treturn_error = BR_FAILED_REPLY;\n"
    "\t\t\t\tgoto err_bad_offset;\n"
    "\t\t\t}\n"
    "\t\t\tfd_buf_size = sizeof(u32) * fda->num_fds;\n"
    "\t\t\tif (fda->parent_offset > parent->length ||\n"
    "\t\t\t    parent->length - fda->parent_offset < fd_buf_size) {\n"
    "\t\t\t\tbinder_user_error(\"%d:%d BINDER_TYPE_FDA bad parent_offset\\n\",\n"
    "\t\t\t\t\tproc->pid, thread->pid);\n"
    "\t\t\t\treturn_error = BR_FAILED_REPLY;\n"
    "\t\t\t\tgoto err_bad_offset;\n"
    "\t\t\t}\n"
    "\t\t\tparent_buffer = (u8 *)((uintptr_t)parent->buffer -\n"
    "\t\t\t\ttarget_proc->user_buffer_offset);\n"
    "\t\t\tfd_array = (u32 *)(parent_buffer + fda->parent_offset);\n"
    "\t\t\tif (!IS_ALIGNED((uintptr_t)fd_array, sizeof(u32))) {\n"
    "\t\t\t\treturn_error = BR_FAILED_REPLY;\n"
    "\t\t\t\tgoto err_bad_offset;\n"
    "\t\t\t}\n"
    "\t\t\tfor (fd_index = 0; fd_index < fda->num_fds; fd_index++) {\n"
    "\t\t\t\tu32 fd = fd_array[fd_index];\n"
    "\t\t\t\tstruct file *file;\n"
    "\t\t\t\tint target_fd;\n\n"
    "\t\t\t\tif (reply) {\n"
    "\t\t\t\t\tif (!(in_reply_to->flags & TF_ACCEPT_FDS)) {\n"
    "\t\t\t\t\t\treturn_error = BR_FAILED_REPLY;\n"
    "\t\t\t\t\t\tgoto err_fd_not_allowed;\n"
    "\t\t\t\t\t}\n"
    "\t\t\t\t} else if (!target_node->accept_fds) {\n"
    "\t\t\t\t\treturn_error = BR_FAILED_REPLY;\n"
    "\t\t\t\t\tgoto err_fd_not_allowed;\n"
    "\t\t\t\t}\n"
    "\t\t\t\tfile = fget(fd);\n"
    "\t\t\t\tif (file == NULL) {\n"
    "\t\t\t\t\tbinder_user_error(\"%d:%d BINDER_TYPE_FDA invalid fd %d\\n\",\n"
    "\t\t\t\t\t\tproc->pid, thread->pid, fd);\n"
    "\t\t\t\t\treturn_error = BR_FAILED_REPLY;\n"
    "\t\t\t\t\tgoto err_fget_failed;\n"
    "\t\t\t\t}\n"
    "\t\t\t\tif (security_binder_transfer_file(proc->tsk,\n"
    "\t\t\t\t\t\ttarget_proc->tsk, file) < 0) {\n"
    "\t\t\t\t\tfput(file);\n"
    "\t\t\t\t\treturn_error = BR_FAILED_REPLY;\n"
    "\t\t\t\t\tgoto err_get_unused_fd_failed;\n"
    "\t\t\t\t}\n"
    "\t\t\t\ttarget_fd = task_get_unused_fd_flags(target_proc, O_CLOEXEC);\n"
    "\t\t\t\tif (target_fd < 0) {\n"
    "\t\t\t\t\tfput(file);\n"
    "\t\t\t\t\treturn_error = BR_FAILED_REPLY;\n"
    "\t\t\t\t\tgoto err_get_unused_fd_failed;\n"
    "\t\t\t\t}\n"
    "\t\t\t\ttask_fd_install(target_proc, target_fd, file);\n"
    "\t\t\t\tfd_array[fd_index] = target_fd;\n"
    "\t\t\t}\n"
    "\t\t} break;\n\n"
    "\t\tdefault:\n"
    "\t\t\tbinder_user_error(\"%d:%d got transaction with invalid object type, %x\\n\",\n"
)
if c.count(tr_anchor) != 1:
    print("V31_TR_ANCHOR_ERROR count=%d" % c.count(tr_anchor)); sys.exit(1)
c = c.replace(tr_anchor, tr_fda, 1)

# (c) binder_transaction_buffer_release: FDA case (clean, without closing fds - bring-up)
rel_old = ("\t\tcase BINDER_TYPE_PTR:\n"
           "\t\t\t/* buffer SG: nada que liberar */\n"
           "\t\t\tbreak;\n")
rel_new = ("\t\tcase BINDER_TYPE_PTR:\n"
           "\t\t\t/* buffer SG: nada que liberar */\n"
           "\t\t\tbreak;\n"
           "\t\tcase BINDER_TYPE_FDA: /* V31: fd array, fds los cierra el receptor */\n"
           "\t\t\tbreak;\n")
if c.count(rel_old) != 1:
    print("V31_REL_ANCHOR_ERROR count=%d" % c.count(rel_old)); sys.exit(1)
c = c.replace(rel_old, rel_new, 1)

open(BC, "w", encoding="utf-8", errors="surrogateescape").write(c)
print("V31_BINDERC_APPLIED")
