# Samsung SM-T280 -- Phase 2 Decision

## Result

**PHASE_2_RESEARCH_PASS**

**PORTING_DECISION: CONDITIONAL_GO**

There is enough information to authorize exclusively a **Phase 3 of preparation and building on a PC**,
without installing or testing on the tablet. The CM/Lineage 14.1 base, the 3.10.65 kernel and the SPRD
hardware tree constitute a real starting point. There is not enough evidence to authorize flashing or to
promise a working system.

## Reasons for the condition

- SM-T280 is ARM32 with 1.5 GB: Android 10 can be built, but the operating margin is narrow.
- There is no Treble, A/B, dynamic partitions or `vendor`; a standard GSI is not viable.
- The kernel lacks namespaces and requires considerable compatibility work.
- The CM 14.1 base uses SELinux permissive and invasive framework patches.
- The historical vendor contains 95 ARM32 ELFs, but the essential Mali GLES blob is missing.
- Graphics and multimedia OMX -- critical for the target app -- have not been tested.
- The exact source code of the AQJ1 firmware was not located.
- The target app is not installed and its current requirements, DRM and native ABIs are unknown.

## Mandatory gates before any hardware-test phase

1. Build the Android 10 kernel and userspace reproducibly on a PC.
2. Resolve or document the AQJ1/AQA4 divergence.
3. Inventory the exact graphics set and demonstrate Mali/HWC/gralloc linking.
4. Demonstrate OMX registration and a hardware H.264 path in build artifacts.
5. Keep `boot` under 16 MiB and `system` under 2 GiB with margin.
6. Define a SELinux strategy toward enforcing.
7. Have verifiable stock firmware and a recovery procedure before any write.
8. Request explicit user authorization for every future operation on the tablet.

## Proposed next phase

Phase 3: create a local LineageOS 17.1 manifest, port device/kernel/hardware in new branches, build tools
from source and produce a first diagnostic build. Phase 3 ends in PC artifacts and logs: **it does not
flash, does not reboot and does not modify the device**.

## Tablet state

Not modified during Phase 2. No software was installed, no configuration was changed, it was not rebooted
and no partition was written.
