# Phase 2 -- Graphics strategy

## Primary route

Port the Spreadtrum HWC/gralloc available in source to the Android 10 interfaces, initially keeping ION and
HWC1 via whatever compatibility layer proves viable. Pair it with the exact Mali-400 r5p0 userspace from the
firmware, once legally inventoried, and isolate its dependencies with minimal, documented shims.

## Acceptance criteria in later phases

- SurfaceFlinger starts without permanent software composition.
- EGL/GLES 2 creates contexts, renders and releases buffers without leaks.
- Rotation, suspend/resume and video overlay work.
- No framebuffer corruption or sustained ION failures.

SwiftShader/software composition is only for early diagnosis: with a Cortex-A7 and 1.5 GB it is not a
suitable final solution for the target app. The missing Mali blob and the historical SurfaceFlinger
modifications make graphics a **CRITICAL** risk.
