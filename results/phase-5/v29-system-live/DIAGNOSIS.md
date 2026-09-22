# Phase 5 -- V29: gralloc patch ACTIVE (scx30g_v2); alloc contradiction; V30 diag

Date: 2026-09-18. Source: `logcat -b all`,
`results/phase-5/v29-system-live/logcat.txt`.

## V29 confirmed active (correct directory = scx30g_v2)

My logs come out: `gralloc.sc8830: V29 alloc: w=800 h=1280 format=0x1 usage=0x1a00`
(pid 216 = allocator@2.0-service) and `V29: HW_FB via ION copy, size=4096000
usage=0xe00`. The ION-copy path for HW_FB **runs** (usage 0x1a00 -> 0xe00).

## Unresolved contradiction

1. **HW_FB (0x1a00):** the gralloc in 216 takes the ION-copy path, runs
   `gralloc_alloc_buffer(0xe00)` and logs **NO AERR** (neither "Failed to ion_alloc",
   nor ion_share/ion_map). All the gralloc code returns 0 (success) after setting the
   handle. BUT SurfaceFlinger (228) reports
   `GraphicBufferAllocator: Failed to allocate 800x1280 usage 1a00: 5 (NO_RESOURCES)`.
   The only path to NO_RESOURCES(5) is `mDevice->alloc()` returning non-zero/non-EINVAL.
   Static analysis: the whole chain (gralloc_alloc_framebuffer ->_locked -> V29 ->
   gralloc_alloc_buffer) returns 0. **Contradiction.** Hypothesis: SF's request
   fails on the CLIENT (228) without reaching the gralloc, and the `V29 alloc` seen is from another
   allocation (e.g. the composer's framebuffer_open).
2. **bootanim (0xf02, -22 EINVAL):** produces NO `V29 alloc` -> **does not reach the
   gralloc**; fails on the client (228/324) with EINVAL.

## V30 (DIAGNOSTIC, not fix)

`apply-v30-alloc-diag.py` instruments 3 points:
1. gralloc: `ion_alloc` heap/size/ret ALWAYS.
2. gralloc: final return value of `alloc_device_alloc`.
3. **allocator@2.0 passthrough** (`Gralloc0Hal.h allocateOneBuffer`): the `result` of
   `mDevice->alloc()` and its w/h/fmt/usage.

Objective: if SF's 800x1280 request appears as `V30 passthrough alloc` in 216,
see the gralloc's exact `result`; if it does NOT appear, it confirms it fails on the client
(and the fix goes in the client mapper/allocator, not the gralloc). Change in system.img
(gralloc.sc8830 + allocator@2.0-impl). boot unchanged.

## gralloc state: SOURCE, directory scx30g_v2

`gralloc.sc8830` is compiled from `hardware/sprd/gralloc/scx30g_v2/` (NOT sc8830/).
`GRALLOC_ARM_DMA_BUF_MODULE=1` (modern ion, `ion_user_handle_t`). Default heap
for HW_2D/normal = `ION_HEAP_ID_MASK_SYSTEM` (1<<1).

## Secondary: audioserver SIGSEGV in `AudioFlinger::AudioFlinger()` in a loop.
