# Phase 2 -- Partition budget

| Partition | Observed/configured limit | Engineering target | Risk |
|---|---:|---:|---|
| boot | 16 MiB | max 14.4 MiB (10% margin) | HIGH |
| recovery | 16 MiB | out of this phase | NOT_APPLICABLE |
| system | 2,048 MiB | max 1,800 MiB initially | HIGH |
| cache | 200 MiB | do not rely on it to grow system | MEDIUM |
| userdata | ~5,044 MiB configured; ~4.8 GiB visible | preserve without repartitioning | MEDIUM |

The first build must be `userdebug`, ARM32, without GApps and with a minimal set of applications. It is not
proposed to create `vendor`, `super`, A/B or dynamic partitions, or to resize partitions. The real size of
LineageOS 17.1 is **UNKNOWN** until building in Phase 3.

A full Google Apps package can make the `/system` margin unfeasible; microG or a minimal selection are
later, separate decisions from the first boot.
