# Phase 2 -- Multimedia strategy

Functional priority: hardware H.264 decoding, stable audio and sustained playback, as these are the likely
requirements of the target app.

The `hardware/sprd` base includes the VPU, `libstagefrighthw` and OMX components; the vendor provides ARM32
H.264/MPEG4/VP8 components. However, CM 14.1 needed an extensive `frameworks/av` patch, a sign of
structural incompatibility.

Plan:

1. Get the OMX stack to build without optional blobs.
2. Record each component, role, color format and dependency.
3. Port only the essential SPRD changes to Android 10.
4. Test H.264 baseline/main, native resolution, seek, audio/video and suspend in an authorized phase.
5. Keep the software codec as a limited fallback, not as proof of viability.

HEVC or VP9 hardware is not assumed. The current result is **PARTIAL / CRITICAL RISK** because only static
evidence exists, not a functional test.
