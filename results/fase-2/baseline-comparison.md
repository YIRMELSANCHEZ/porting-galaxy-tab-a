# Phase 2 -- Baseline comparison

| Area | Stock 5.1.1 AQJ1 | Community CM/Lineage 14.1 | Android 10 requirement |
|---|---|---|---|
| Architecture | ARMv7, 32-bit | ARMv7-A/NEON | ARM32 still possible, with a smaller compatibility margin |
| Kernel | 3.10.65 Samsung | 3.10.65 modified | Requires backports/config and userspace adaptation |
| Partitions | classic, no `vendor` | same partitions | Legacy non-Treble design; no standard GSI |
| Boot | boot 16 MiB + DHTB | custom mkbootimg + separate DT | Must keep the format and fit without repartitioning |
| Graphics | Mali-400 r5p0, GLES 2 | SPRD HWC/gralloc + legacy Mali | HWC1/gralloc and linker compatibility critical |
| Multimedia | SPRD OMX | extensive `frameworks/av` patches | Android 10 MediaCodec/OMX requires significant migration |
| Security | stock enforcing SELinux | permissive community baseline | Final goal enforcing; new policies needed |
| Framework | Samsung Lollipop | global patches for blobs | Port or replace patches without degrading security |

Conclusion: CM 14.1 is a hardware-enablement reference, not a directly updatable branch. The effective
transition is three major generations and crosses build, linker, SELinux, graphics and multimedia changes.
