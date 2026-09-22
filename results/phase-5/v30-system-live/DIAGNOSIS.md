# Phase 5 -- V30: graphics ROOT CAUSE = kernel binder without BINDER_TYPE_FDA. V31 fix

Date: 2026-09-18. Source: `logcat -b all` (V30 diag) + kernel `dmesg`.

## The V30 diagnosis resolved the contradiction

The instrumented logs prove that ALL graphics work:
```
gralloc.sc8830: V30 ion_alloc: heap=0x2 size=4096000 ret=0 client=5   -> ION OK (SYSTEM heap)
gralloc.sc8830: V30 alloc_device_alloc OK: usage=0x1a00 stride=800     -> gralloc success
AllocatorHal:   V30 passthrough alloc: 800x1280 usage=0x1a00 result=0  -> allocator NONE (success)
GraphicBufferAllocator: Failed to allocate 800x1280 usage 1a00: 5      -> but SF (229) receives 5
```
`kTransactionError = NO_RESOURCES(5)` in `frameworks/native/libs/ui/Gralloc2.cpp`:
returned when `ret.isOk()` is false = **the binder transaction fails**, not the
allocation.

## Root cause (kernel binder)

`dmesg`:
```
binder: 216:287 got transaction with invalid object type/size, 66646185
binder: 216:287 transaction failed 29201, size 112-16
binder: send failed reply for transaction 254 to 229:229
```
`0x66646185` = `B_PACK_CHARS('f','d','a')` = **BINDER_TYPE_FDA** (fd array).
When the allocator@2.0-service (216) returns the buffer's `native_handle` (with its
fd) to SurfaceFlinger (229) via HIDL, the handle is serialized as a
`binder_fd_array_object` (BINDER_TYPE_FDA). The kernel 3.10 binder
(`binder_object_size(FDA)` = 0) **does not know that type** -> "invalid object type" ->
reply fails -> SF receives NO_RESOURCES.

The previous binder backport (V13 multi-device, V14/V15 scatter-gather) added
`BINDER_TYPE_PTR` but **omitted `BINDER_TYPE_FDA`**. HIDL calls without a
native_handle worked (composer getService, etc.); buffer allocation is the first
that returns a native_handle with an fd -> first FDA -> first failure.

## V31 (fix) -- BINDER_TYPE_FDA backport

`apply-v31-binder-fda.py` in `kernel/.../drivers/staging/android/`:
1. `uapi/binder.h`: `BINDER_TYPE_FDA` + `struct binder_fd_array_object`.
2. `binder.c binder_object_size()`: FDA -> sizeof(binder_fd_array_object).
3. `binder.c binder_transaction()`: FDA case -> finds the parent buffer (PTR already
   copied to sg), validates parent/offset, and translates EACH fd of the array as
   BINDER_TYPE_FD (fget + security_binder_transfer_file + task_get_unused_fd_flags + task_fd_install).
4. `binder.c binder_transaction_buffer_release()`: FDA case (clean; the receiver closes
   the fds).
Recompiles the kernel -> **boot.img changes** (first change since V20). It also changes
system (drags V29 gralloc ION + V30 logs, which can be left).

Expected success: the buffer reply reaches SF -> FramebufferSurface allocates -> SF
composes and presents -> **boot animation**. It also unblocks ANY HAL that passes
native_handles (camera, video, etc.).

## Note: V29 (gralloc ION-copy) turned out to be orthogonal
The real failure was the binder, not the page-flip. V29 makes the allocation succeed
(does no harm); it can be kept or reverted. The V30 logs can be removed in the final fix.
