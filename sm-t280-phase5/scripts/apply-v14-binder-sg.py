#!/usr/bin/env python3
# V14: scatter-gather backport to the 3.10 binder (BC_TRANSACTION_SG/BC_REPLY_SG,
# BINDER_TYPE_PTR, binder_buffer_object, extra_buffers_size). Based on the design
# upstream (Martijn Coenen). Idempotente.
import sys

KROOT = "/home/lineage/android/lineage-17.1/kernel/samsung/gtexswifi/drivers/staging/android"
H = KROOT + "/uapi/binder.h"
C = KROOT + "/binder.c"

def load(p):
    return open(p, encoding="utf-8", errors="surrogateescape").read()
def save(p, s):
    open(p, "w", encoding="utf-8", errors="surrogateescape").write(s)
def rep(s, old, new, tag):
    if old not in s:
        print("ERROR: block not found (%s)" % tag, file=sys.stderr); sys.exit(2)
    return s.replace(old, new, 1)

h = load(H)
c = load(C)
if "BINDER_TYPE_PTR" in h or "binder_transaction_data_sg" in h:
    print("V14_PATCH_ALREADY_PRESENT"); sys.exit(0)

# --- HEADER ---
h = rep(h,
    "\tBINDER_TYPE_FD\t\t= B_PACK_CHARS('f', 'd', '*', B_TYPE_LARGE),\n",
    "\tBINDER_TYPE_FD\t\t= B_PACK_CHARS('f', 'd', '*', B_TYPE_LARGE),\n"
    "\tBINDER_TYPE_PTR\t\t= B_PACK_CHARS('p', 't', '*', B_TYPE_LARGE),\n",
    "H1 BINDER_TYPE_PTR")

STRUCTS = (
"enum {\n"
"\tBINDER_BUFFER_FLAG_HAS_PARENT = 0x01,\n"
"};\n\n"
"struct binder_object_header {\n"
"\t__u32        type;\n"
"};\n\n"
"struct binder_buffer_object {\n"
"\tstruct binder_object_header\thdr;\n"
"\t__u32\t\t\t\tflags;\n"
"\tbinder_uintptr_t\t\tbuffer;\n"
"\tbinder_size_t\t\t\tlength;\n"
"\tbinder_size_t\t\t\tparent;\n"
"\tbinder_size_t\t\t\tparent_offset;\n"
"};\n\n"
"struct binder_transaction_data_sg {\n"
"\tstruct binder_transaction_data transaction_data;\n"
"\tbinder_size_t buffers_size;\n"
"};\n\n"
"enum binder_driver_command_protocol {\n")
h = rep(h, "enum binder_driver_command_protocol {\n", STRUCTS, "H2 structs")

h = rep(h,
    "\tBC_REPLY = _IOW('c', 1, struct binder_transaction_data),\n"
    "\t/*\n"
    "\t * binder_transaction_data: the sent command.\n"
    "\t */\n",
    "\tBC_REPLY = _IOW('c', 1, struct binder_transaction_data),\n"
    "\t/*\n"
    "\t * binder_transaction_data: the sent command.\n"
    "\t */\n\n"
    "\tBC_TRANSACTION_SG = _IOW('c', 17, struct binder_transaction_data_sg),\n"
    "\tBC_REPLY_SG = _IOW('c', 18, struct binder_transaction_data_sg),\n"
    "\t/*\n"
    "\t * binder_transaction_data_sg: the sent command.\n"
    "\t */\n",
    "H3 BC_*_SG")
save(H, h)

# --- binder.c ---
# C0: enlarge the bc[] stats array to include BC_REPLY_SG.
c = rep(c, "\tint bc[_IOC_NR(BC_DEAD_BINDER_DONE) + 1];\n",
           "\tint bc[_IOC_NR(BC_REPLY_SG) + 1];\n", "C0 stats bc size")

# C1: campo extra_buffers_size en binder_buffer.
c = rep(c, "\tsize_t data_size;\n\tsize_t offsets_size;\n\tuint8_t data[0];\n",
           "\tsize_t data_size;\n\tsize_t offsets_size;\n\tsize_t extra_buffers_size;\n\tuint8_t data[0];\n",
           "C1 binder_buffer")

# C2: binder_alloc_buf signature.
c = rep(c,
    "static struct binder_buffer *binder_alloc_buf(struct binder_proc *proc,\n"
    "\t\t\t\t\t      size_t data_size,\n"
    "\t\t\t\t\t      size_t offsets_size, int is_async)\n",
    "static struct binder_buffer *binder_alloc_buf(struct binder_proc *proc,\n"
    "\t\t\t\t\t      size_t data_size,\n"
    "\t\t\t\t\t      size_t offsets_size,\n"
    "\t\t\t\t\t      size_t extra_buffers_size,\n"
    "\t\t\t\t\t      int is_async)\n",
    "C2 alloc sig")

# C3: calculo de tamano en alloc.
c = rep(c,
    "\tsize = ALIGN(data_size, sizeof(void *)) +\n"
    "\t\tALIGN(offsets_size, sizeof(void *));\n",
    "\tsize = ALIGN(data_size, sizeof(void *)) +\n"
    "\t\tALIGN(offsets_size, sizeof(void *)) +\n"
    "\t\tALIGN(extra_buffers_size, sizeof(void *));\n",
    "C3 alloc size")

# C4: guardar extra_buffers_size.
c = rep(c,
    "\tbuffer->data_size = data_size;\n\tbuffer->offsets_size = offsets_size;\n\tbuffer->async_transaction = is_async;\n",
    "\tbuffer->data_size = data_size;\n\tbuffer->offsets_size = offsets_size;\n\tbuffer->extra_buffers_size = extra_buffers_size;\n\tbuffer->async_transaction = is_async;\n",
    "C4 store extra")

# C5: tamano en binder_free_buf.
c = rep(c,
    "\tsize = ALIGN(buffer->data_size, sizeof(void *)) +\n"
    "\t\tALIGN(buffer->offsets_size, sizeof(void *));\n",
    "\tsize = ALIGN(buffer->data_size, sizeof(void *)) +\n"
    "\t\tALIGN(buffer->offsets_size, sizeof(void *)) +\n"
    "\t\tALIGN(buffer->extra_buffers_size, sizeof(void *));\n",
    "C5 free size")

# C6: binder_object_size helper + signature + locals of binder_transaction.
c = rep(c,
    "static void binder_transaction(struct binder_proc *proc,\n"
    "\t\t\t       struct binder_thread *thread,\n"
    "\t\t\t       struct binder_transaction_data *tr, int reply)\n"
    "{\n"
    "\tstruct binder_transaction *t;\n"
    "\tstruct binder_work *tcomplete;\n"
    "\tbinder_size_t *offp, *off_end;\n"
    "\tbinder_size_t off_min;\n",
    "static size_t binder_object_size(__u32 type)\n"
    "{\n"
    "\tswitch (type) {\n"
    "\tcase BINDER_TYPE_BINDER:\n"
    "\tcase BINDER_TYPE_WEAK_BINDER:\n"
    "\tcase BINDER_TYPE_HANDLE:\n"
    "\tcase BINDER_TYPE_WEAK_HANDLE:\n"
    "\tcase BINDER_TYPE_FD:\n"
    "\t\treturn sizeof(struct flat_binder_object);\n"
    "\tcase BINDER_TYPE_PTR:\n"
    "\t\treturn sizeof(struct binder_buffer_object);\n"
    "\tdefault:\n"
    "\t\treturn 0;\n"
    "\t}\n"
    "}\n\n"
    "static void binder_transaction(struct binder_proc *proc,\n"
    "\t\t\t       struct binder_thread *thread,\n"
    "\t\t\t       struct binder_transaction_data *tr, int reply,\n"
    "\t\t\t       binder_size_t extra_buffers_size)\n"
    "{\n"
    "\tstruct binder_transaction *t;\n"
    "\tstruct binder_work *tcomplete;\n"
    "\tbinder_size_t *offp, *off_end, *off_start;\n"
    "\tbinder_size_t off_min;\n"
    "\tu8 *sg_bufp, *sg_buf_end;\n",
    "C6 transaction sig")

# C7: llamada a binder_alloc_buf.
c = rep(c,
    "\tt->buffer = binder_alloc_buf(target_proc, tr->data_size,\n"
    "\t\ttr->offsets_size, !reply && (t->flags & TF_ONE_WAY));\n",
    "\tt->buffer = binder_alloc_buf(target_proc, tr->data_size,\n"
    "\t\ttr->offsets_size, extra_buffers_size,\n"
    "\t\t!reply && (t->flags & TF_ONE_WAY));\n",
    "C7 alloc call")

# C8: offp/off_start.
c = rep(c,
    "\toffp = (binder_size_t *)(t->buffer->data +\n"
    "\t\t\t\t ALIGN(tr->data_size, sizeof(void *)));\n",
    "\toff_start = (binder_size_t *)(t->buffer->data +\n"
    "\t\t\t\t ALIGN(tr->data_size, sizeof(void *)));\n"
    "\toffp = off_start;\n",
    "C8 off_start")

# C9: size-aware validation of the loop + sg_bufp init.
c = rep(c,
    "\toff_end = (void *)offp + tr->offsets_size;\n"
    "\toff_min = 0;\n"
    "\tfor (; offp < off_end; offp++) {\n"
    "\t\tstruct flat_binder_object *fp;\n"
    "\t\tif (*offp > t->buffer->data_size - sizeof(*fp) ||\n"
    "\t\t    *offp < off_min ||\n"
    "\t\t    t->buffer->data_size < sizeof(*fp) ||\n"
    "\t\t    !IS_ALIGNED(*offp, sizeof(u32))) {\n"
    "\t\t\tbinder_user_error(\"%d:%d got transaction with invalid offset, %lld (min %lld, max %lld)\\n\",\n"
    "\t\t\t\t\t  proc->pid, thread->pid, (u64)*offp,\n"
    "\t\t\t\t\t  (u64)off_min,\n"
    "\t\t\t\t\t  (u64)(t->buffer->data_size -\n"
    "\t\t\t\t\t  sizeof(*fp)));\n"
    "\t\t\treturn_error = BR_FAILED_REPLY;\n"
    "\t\t\tgoto err_bad_offset;\n"
    "\t\t}\n"
    "\t\tfp = (struct flat_binder_object *)(t->buffer->data + *offp);\n"
    "\t\toff_min = *offp + sizeof(struct flat_binder_object);\n"
    "\t\tswitch (fp->type) {\n",
    "\toff_end = (void *)off_start + tr->offsets_size;\n"
    "\tsg_bufp = (u8 *)(t->buffer->data +\n"
    "\t\tALIGN(tr->data_size, sizeof(void *)) +\n"
    "\t\tALIGN(tr->offsets_size, sizeof(void *)));\n"
    "\tsg_buf_end = sg_bufp + extra_buffers_size;\n"
    "\toff_min = 0;\n"
    "\tfor (; offp < off_end; offp++) {\n"
    "\t\tstruct flat_binder_object *fp;\n"
    "\t\tsize_t object_size;\n"
    "\t\tif (t->buffer->data_size < sizeof(u32) ||\n"
    "\t\t    *offp > t->buffer->data_size - sizeof(u32) ||\n"
    "\t\t    *offp < off_min ||\n"
    "\t\t    !IS_ALIGNED(*offp, sizeof(u32))) {\n"
    "\t\t\tbinder_user_error(\"%d:%d got transaction with invalid offset, %lld (min %lld, max %lld)\\n\",\n"
    "\t\t\t\t\t  proc->pid, thread->pid, (u64)*offp,\n"
    "\t\t\t\t\t  (u64)off_min,\n"
    "\t\t\t\t\t  (u64)(t->buffer->data_size -\n"
    "\t\t\t\t\t  sizeof(u32)));\n"
    "\t\t\treturn_error = BR_FAILED_REPLY;\n"
    "\t\t\tgoto err_bad_offset;\n"
    "\t\t}\n"
    "\t\tfp = (struct flat_binder_object *)(t->buffer->data + *offp);\n"
    "\t\tobject_size = binder_object_size(fp->type);\n"
    "\t\tif (object_size == 0 ||\n"
    "\t\t    t->buffer->data_size < object_size ||\n"
    "\t\t    *offp > t->buffer->data_size - object_size) {\n"
    "\t\t\tbinder_user_error(\"%d:%d got transaction with invalid object type/size, %x\\n\",\n"
    "\t\t\t\t\t  proc->pid, thread->pid, fp->type);\n"
    "\t\t\treturn_error = BR_FAILED_REPLY;\n"
    "\t\t\tgoto err_bad_object_type;\n"
    "\t\t}\n"
    "\t\toff_min = *offp + object_size;\n"
    "\t\tswitch (fp->type) {\n",
    "C9 loop validation")

# C10: caso BINDER_TYPE_PTR antes de default.
c = rep(c,
    "\t\t\tfp->binder = 0;\n"
    "\t\t\tfp->handle = target_fd;\n"
    "\t\t} break;\n"
    "\n"
    "\t\tdefault:\n"
    "\t\t\tbinder_user_error(\"%d:%d got transaction with invalid object type, %x\\n\",\n",
    "\t\t\tfp->binder = 0;\n"
    "\t\t\tfp->handle = target_fd;\n"
    "\t\t} break;\n"
    "\t\tcase BINDER_TYPE_PTR: {\n"
    "\t\t\tstruct binder_buffer_object *bp =\n"
    "\t\t\t\t(struct binder_buffer_object *)fp;\n"
    "\t\t\tsize_t buf_left = sg_buf_end - sg_bufp;\n\n"
    "\t\t\tif (bp->length > buf_left) {\n"
    "\t\t\t\tbinder_user_error(\"%d:%d got transaction with too large buffer\\n\",\n"
    "\t\t\t\t\t\t  proc->pid, thread->pid);\n"
    "\t\t\t\treturn_error = BR_FAILED_REPLY;\n"
    "\t\t\t\tgoto err_bad_offset;\n"
    "\t\t\t}\n"
    "\t\t\tif (copy_from_user(sg_bufp,\n"
    "\t\t\t\t\t   (const void __user *)(uintptr_t)bp->buffer,\n"
    "\t\t\t\t\t   bp->length)) {\n"
    "\t\t\t\tbinder_user_error(\"%d:%d got transaction with invalid buffer ptr\\n\",\n"
    "\t\t\t\t\t\t  proc->pid, thread->pid);\n"
    "\t\t\t\treturn_error = BR_FAILED_REPLY;\n"
    "\t\t\t\tgoto err_copy_data_failed;\n"
    "\t\t\t}\n"
    "\t\t\tbp->buffer = (binder_uintptr_t)((uintptr_t)sg_bufp +\n"
    "\t\t\t\t\ttarget_proc->user_buffer_offset);\n"
    "\t\t\tif (bp->flags & BINDER_BUFFER_FLAG_HAS_PARENT) {\n"
    "\t\t\t\tstruct binder_buffer_object *parent;\n"
    "\t\t\t\tu8 *parent_buffer;\n"
    "\t\t\t\tbinder_size_t parent_index;\n\n"
    "\t\t\t\tparent_index = (binder_size_t)(offp - off_start);\n"
    "\t\t\t\tif (bp->parent >= parent_index) {\n"
    "\t\t\t\t\tbinder_user_error(\"%d:%d got transaction with invalid parent index\\n\",\n"
    "\t\t\t\t\t\t\t  proc->pid, thread->pid);\n"
    "\t\t\t\t\treturn_error = BR_FAILED_REPLY;\n"
    "\t\t\t\t\tgoto err_bad_offset;\n"
    "\t\t\t\t}\n"
    "\t\t\t\tparent = (struct binder_buffer_object *)\n"
    "\t\t\t\t\t(t->buffer->data + off_start[bp->parent]);\n"
    "\t\t\t\tif (parent->hdr.type != BINDER_TYPE_PTR ||\n"
    "\t\t\t\t    bp->parent_offset > parent->length ||\n"
    "\t\t\t\t    parent->length - bp->parent_offset <\n"
    "\t\t\t\t\tsizeof(binder_uintptr_t)) {\n"
    "\t\t\t\t\tbinder_user_error(\"%d:%d got transaction with invalid parent fixup\\n\",\n"
    "\t\t\t\t\t\t\t  proc->pid, thread->pid);\n"
    "\t\t\t\t\treturn_error = BR_FAILED_REPLY;\n"
    "\t\t\t\t\tgoto err_bad_offset;\n"
    "\t\t\t\t}\n"
    "\t\t\t\tparent_buffer = (u8 *)((uintptr_t)parent->buffer -\n"
    "\t\t\t\t\ttarget_proc->user_buffer_offset);\n"
    "\t\t\t\t*(binder_uintptr_t *)(parent_buffer +\n"
    "\t\t\t\t\tbp->parent_offset) = bp->buffer;\n"
    "\t\t\t}\n"
    "\t\t\tsg_bufp += ALIGN(bp->length, sizeof(u64));\n"
    "\t\t} break;\n"
    "\n"
    "\t\tdefault:\n"
    "\t\t\tbinder_user_error(\"%d:%d got transaction with invalid object type, %x\\n\",\n",
    "C10 PTR case")

# C11: BC_TRANSACTION_SG/BC_REPLY_SG dispatch + pass extra=0 to the normal path.
c = rep(c,
    "\t\tcase BC_TRANSACTION:\n"
    "\t\tcase BC_REPLY: {\n"
    "\t\t\tstruct binder_transaction_data tr;\n\n"
    "\t\t\tif (copy_from_user(&tr, ptr, sizeof(tr)))\n"
    "\t\t\t\treturn -EFAULT;\n"
    "\t\t\tptr += sizeof(tr);\n"
    "\t\t\tbinder_transaction(proc, thread, &tr, cmd == BC_REPLY);\n"
    "\t\t\tbreak;\n"
    "\t\t}\n",
    "\t\tcase BC_TRANSACTION_SG:\n"
    "\t\tcase BC_REPLY_SG: {\n"
    "\t\t\tstruct binder_transaction_data_sg tr;\n\n"
    "\t\t\tif (copy_from_user(&tr, ptr, sizeof(tr)))\n"
    "\t\t\t\treturn -EFAULT;\n"
    "\t\t\tptr += sizeof(tr);\n"
    "\t\t\tbinder_transaction(proc, thread, &tr.transaction_data,\n"
    "\t\t\t\t\t   cmd == BC_REPLY_SG, tr.buffers_size);\n"
    "\t\t\tbreak;\n"
    "\t\t}\n"
    "\t\tcase BC_TRANSACTION:\n"
    "\t\tcase BC_REPLY: {\n"
    "\t\t\tstruct binder_transaction_data tr;\n\n"
    "\t\t\tif (copy_from_user(&tr, ptr, sizeof(tr)))\n"
    "\t\t\t\treturn -EFAULT;\n"
    "\t\t\tptr += sizeof(tr);\n"
    "\t\t\tbinder_transaction(proc, thread, &tr, cmd == BC_REPLY, 0);\n"
    "\t\t\tbreak;\n"
    "\t\t}\n",
    "C11 dispatch")

# C12: command strings so ARRAY_SIZE(bc) matches (BUILD_BUG_ON).
c = rep(c,
    "\t\"BC_DEAD_BINDER_DONE\"\n};",
    "\t\"BC_DEAD_BINDER_DONE\",\n\t\"BC_TRANSACTION_SG\",\n\t\"BC_REPLY_SG\"\n};",
    "C12 command strings")

save(C, c)
print("V14_PATCH_APPLIED")
