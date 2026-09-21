# SM-T280 project general plan

## Purpose

Evaluate and, only if the evidence allows it, develop an Android 10 / LineageOS 17.1 port for the Samsung
Galaxy Tab A 7.0 (2016) SM-T280 (`gtexswifi`), with particular attention to running stably an app that
requires GLES 3.0.

This directory holds reusable procedures and goals. Tablet-specific results are stored in `../results/`;
the original ADB captures remain in `../sm-t280-phase1/raw/`.

## Phase summary

| Phase | Name | Goal | Expected result |
|---:|---|---|---|
| 1 | Non-destructive technical analysis | Identify hardware, firmware, partitions, HALs and risks without modifying the tablet | Preliminary feasibility report |
| 2 | Port research and strategy | Locate sources, blobs, prior art and define a viable architecture | Completed: `PHASE_2_RESEARCH_PASS / CONDITIONAL_GO` |
| 3 | Environment and source preparation | Create a reproducible environment and prepare device/kernel/vendor trees | Preparation complete; build blocked until Linux/WSL enabled |
| 4 | Build and controlled boot | Produce a first image and verify the boot path with safeguards | Recovery goal met: `PHASE_4_RECOVERY_OBJECTIVE_MET` (Android 10 recovery validated on hardware, V21) |
| 5 | Hardware bring-up | Enable and stabilize the device subsystems | Functional hardware matrix |
| 6 | Android, Google and target-app validation | Check stability, performance, security and target-app compatibility | Acceptance or rejection report |
| 7 | Packaging, maintenance and final decision | Prepare reproducible deliverables and decide whether the port is maintainable | Release candidate or decision to stop |

## Cross-cutting rules

- Each phase requires reviewing and approving the risks before moving to the next.
- Procedures live in `docs/`; measurements, logs and specific reports live in `results/`.
- Every destructive action -- unlock, custom recovery, wipe or flash -- requires explicit prior
  authorization.
- A documented, tested recovery procedure must exist before the first flash.
- "Detected" does not mean "functionally tested".
