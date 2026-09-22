# Phase 2 -- Risk register

| ID | Risk | Level | Mitigation / exit gate |
|---|---|---|---|
| R1 | The exact AQJ1 kernel was not located | HIGH | Get the Samsung source and compare with AQA4/CM14 |
| R2 | Kernel 3.10 without namespaces | CRITICAL | Backport/config and reproducible build before an image |
| R3 | Main Mali blob missing in the historical vendor | CRITICAL | Exact and legal inventory of the stock; validate ABI/linker |
| R4 | Old HWC1/gralloc/SurfaceFlinger | CRITICAL | Incremental port and EGL/HWC test before UX |
| R5 | SPRD OMX depends on framework patches | CRITICAL | Build/register OMX and test hardware H.264 |
| R6 | 1.5 GB RAM and ARM32 | HIGH | Minimal build, tuned LMKD/zram, no heavy packages |
| R7 | `/system` limited to 2 GiB | HIGH | First build without GApps, budget <1.8 GiB |
| R8 | Permissive SELinux in the community baseline | HIGH | Specific policies; enforcing as an exit criterion |
| R9 | Camera/GPS depend on private APIs | HIGH | Minimal shims or explicit degradation; do not block the target app if it is not a requirement |
| R10 | The target app is not installed; ABI/requirements unknown | CRITICAL | Get the APK/versioning legitimately and analyze compatibility without private data |
| R11 | Blobs without a clear redistribution license | HIGH | Keep local extraction and exclude them from publication |
| R12 | No viable GSI (no Treble/vendor) | CRITICAL | Device-specific port; discard the GSI route |
