# Phase 5 -- V31: MILESTONE, binder wall BROKEN. FramebufferSurface OK. Bit 0x400 missing

Date: 2026-09-18. Source: `logcat -b all` + `dmesg`,
`results/phase-5/v31-system-live/logcat.txt`.

## MILESTONE: BINDER_TYPE_FDA resolved

- `dmesg`: the error `binder: got transaction with invalid object type/size, 66646185`
  **disappeared**. The FDA backport (V31) works.
- **SurfaceFlinger allocates its FramebufferSurface**: 3x
  `V29 alloc usage=0x1a00` + `V30 passthrough alloc ... result=0` (triple buffer),
  without the previous `usage 1a00: 5` failure. The buffer handle reply crosses binder OK.
- This unblocks the transport of native_handles over HIDL in general.

## Only remaining blocker: usage bit 0x400 (bootanim)

```
E Gralloc2: buffer descriptor contains invalid usage bits 0x400
E GraphicBufferAllocator: Failed to allocate 800x1280 usage f02: -22
E BufferQueueProducer: [BootAnimation#0] dequeueBuffer: createGraphicBuffer failed
E [EGL-ERROR]: failed to dequeue buffer ... err = -12
```
The bootanim buffer (usage 0xf02) is rejected by libui's CLIENT validator
(`Gralloc2Mapper::validateBufferDescriptorInfo`): the **bit 10 (0x400 =
GRALLOC_USAGE_HW_2D)** is not in the valid mask (getValid10/11UsageBits). V26 only
added bit 25; bit 10 is missing. -> BAD_VALUE (-22) before reaching the gralloc.

## V32 (fix)

`apply-v32-gralloc-usage-more.py`: `TARGET_ADDITIONAL_GRALLOC_10_USAGE_BITS += (1<<10)`
(+ 13, 21 preventive, like Qualcomm) -> valid mask in libui. Change in
system.img (libui); **boot = V31 (unchanged)**.

Expected success: bootanim allocates its buffer -> draws -> SF composes and presents ->
**visible boot animation**. If another rejected bit appears, add it likewise.

## Secondary: audioserver SIGSEGV in `AudioFlinger::AudioFlinger()` in a loop.
