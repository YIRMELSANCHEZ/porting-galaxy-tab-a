#!/usr/bin/env python3
# V75 (G1 / GFX-ION: leak of fds and ION memory in every process that receives handles via HIDL).
# On top of V74. Changes the KERNEL (drivers/staging/android/binder.c) -> boot.img.
#
# CAUSE (measured on HW, see results/fase-6/G1-FINDINGS.md):
#   - composer@2.1-service: +3 sync_fence fds per frame (mali_flag_fence = acquire fences of the
#     layers) and it retains the imported buffer handles -> the ION system heap grows without limit
#     (513 MB "orphaned" at 25 min; on restarting the composer it drops to 80 MB).
#   - surfaceflinger: +1 sync_fence fd per frame (HWCRetire = present fence).
#   - Consecuencia: "Lost RAM" ~440 MB, lowmemorykiller, GraphicBufferAllocator NO_RESOURCES ->
#     EGL_BAD_ALLOC -> SurfaceControl.screenshot()==null -> NPE in SystemUI ("could not
#     save the screenshot"). With a 32768 fd limit, SF/composer would eventually die after hours.
#   All the leaked fds are EXACTLY those received in hwbinder transactions within
#   objetos BINDER_TYPE_FDA (fd arrays de hidl_handle). Propiedad de esos fds:
#     * system/libhwbinder/Parcel.cpp release_object(): "case BINDER_TYPE_FDA: The enclosed file
#       descriptors are closed in the kernel" -> userspace does NOT close them (dup() what it keeps).
#     * kernel upstream (binder.c, binder_transaction_buffer_release): case BINDER_TYPE_FDA cierra
#       all the fds of the array with task_close_fd() on freeing the buffer (BC_FREE_BUFFER).
#     * local V31 backport of this kernel 3.10.108: "case BINDER_TYPE_FDA: /* fds closed by the
#       receiver */ break;" -> NOBODY closes them.
#
# FIX: implement in binder_transaction_buffer_release() the FDA case as upstream: locate the
#   parent object (BINDER_TYPE_PTR, already fixed to the receiver's user address), convert it to
#   a kernel address with proc->user_buffer_offset and close each fd of the array in 'proc'.
#   'proc' is the receiver in the normal release and target_proc in the sender's failure path
#   (where the fds were already installed by translate) -> both correct, same as upstream.
# Idempotente.
import sys
from pathlib import Path

SRC = Path("/home/lineage/android/lineage-17.1/kernel/samsung/gtexswifi/drivers/staging/android/binder.c")

OLD_DECL = """	binder_size_t *offp, *off_end;
	int debug_id = buffer->debug_id;

	binder_debug(BINDER_DEBUG_TRANSACTION,
		     "%d buffer release %d, size %zd-%zd, failed at %pK\\n",
		     proc->pid, buffer->debug_id,
		     buffer->data_size, buffer->offsets_size, failed_at);

	if (buffer->target_node)
		binder_dec_node(buffer->target_node, 1, 0);

	offp = (binder_size_t *)(buffer->data +
				 ALIGN(buffer->data_size, sizeof(void *)));
	if (failed_at)
"""
NEW_DECL = """	binder_size_t *offp, *off_end, *off_start;
	int debug_id = buffer->debug_id;

	binder_debug(BINDER_DEBUG_TRANSACTION,
		     "%d buffer release %d, size %zd-%zd, failed at %pK\\n",
		     proc->pid, buffer->debug_id,
		     buffer->data_size, buffer->offsets_size, failed_at);

	if (buffer->target_node)
		binder_dec_node(buffer->target_node, 1, 0);

	offp = (binder_size_t *)(buffer->data +
				 ALIGN(buffer->data_size, sizeof(void *)));
	off_start = offp; /* V75 */
	if (failed_at)
"""

OLD_CASE = """		case BINDER_TYPE_FDA: /* V31: fd array, fds los cierra el receptor */
			break;
"""
NEW_CASE = """		case BINDER_TYPE_FDA: { /* V75: como upstream, el kernel cierra los fds */
			struct binder_fd_array_object *fda =
				(struct binder_fd_array_object *)fp;
			struct binder_buffer_object *parent;
			binder_size_t parent_index = (binder_size_t)(offp - off_start);
			uintptr_t parent_buffer;
			u32 *fd_array;
			size_t fd_index;

			if (fda->parent >= parent_index) {
				pr_err("transaction release %d bad FDA parent index\\n",
				       debug_id);
				break;
			}
			parent = (struct binder_buffer_object *)
				(buffer->data + off_start[fda->parent]);
			if (parent->hdr.type != BINDER_TYPE_PTR) {
				pr_err("transaction release %d FDA parent not PTR\\n",
				       debug_id);
				break;
			}
			if (fda->num_fds >= (SIZE_MAX / sizeof(u32)) ||
			    fda->parent_offset > parent->length ||
			    parent->length - fda->parent_offset <
			    sizeof(u32) * fda->num_fds) {
				pr_err("transaction release %d bad FDA parent_offset\\n",
				       debug_id);
				break;
			}
			/* parent->buffer ya esta fijado a la direccion de usuario de proc */
			parent_buffer = (uintptr_t)parent->buffer -
				proc->user_buffer_offset;
			fd_array = (u32 *)(parent_buffer + fda->parent_offset);
			for (fd_index = 0; fd_index < fda->num_fds; fd_index++)
				task_close_fd(proc, fd_array[fd_index]);
		} break;
"""

s = SRC.read_text(encoding="utf-8", errors="surrogateescape")
if "V75: como upstream" in s:
    print("V75_ALREADY"); sys.exit(0)
for name, old in (("decl", OLD_DECL), ("case", OLD_CASE)):
    if s.count(old) != 1:
        print(f"V75_ERROR: block '{name}' not found exactly once"); sys.exit(1)
s = s.replace(OLD_DECL, NEW_DECL, 1).replace(OLD_CASE, NEW_CASE, 1)
SRC.write_text(s, encoding="utf-8", errors="surrogateescape")
print("V75_APPLIED -> binder closes the BINDER_TYPE_FDA fds on freeing the buffer")
