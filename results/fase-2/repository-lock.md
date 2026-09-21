# Phase 2 -- Repository lock

Reproducible inventory queried on 2026-09-15.

| Local directory | Repository/branch | Commit |
|---|---|---|
| `device-gtexswifi-cm14` | underscoremone device / `cm-14.1` | `0826fd4d9714e0c5568383a408a55801b958c9c2` |
| `vendor-gtexswifi-cm14` | underscoremone vendor / default branch | `b65668464d13a608d74670fad197d351c71e3e0c` |
| `hardware-sprd-cm14` | underscoremone hardware / `cm-14.1` | `13ebb821b17fcd53e7c02dc1b11374f56046109a` |
| `device-gtexswifi-archived` | gtexswifi device / `cm-14.1-other` | `1539d9d6448a775b4ec30e75d3a48c2ddef04ccd` |
| `kernel-gtexswifi-cm14` | underscoremone kernel / `cm-14.1` | `af605083776fb8ec1197e7aafb291bff6043c0a2` |
| `kernel-gtexswifi-cm14` | underscoremone kernel / `T280XXU0AQA4` | `07b76a6c60264cc339de9c1c276c26ef46d03ad8` |
| `kernel-gtexswifi-bfourk` | bfourk kernel / `cm-14.1` | `d2e4ebf84f685a87acd90650f998facdefe06c51` |
| `kernel-gtexswifi-stock-19atlas` | 19atlas stock kernel / `main` | `6f47c3829469c986bd1c08b9dc329b0c4abbb12b` |
| `dhtbsign` | osm0sis / `master` | `2b2711dff153485c549240423d9c908a2912f4b2` |

The kernel repositories are kept as Git bases without a full checkout because Windows rejects the reserved
name `drivers/gpu/drm/nouveau/core/subdev/i2c/aux.c`. The objects and commits are analyzable via Git. No
precompiled binaries bundled in the historical repositories were run.
