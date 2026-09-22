# Phase 7 -- Packaging, maintenance and final decision

## Description

Consolidation of the technical work into reproducible artifacts, instructions and a final maintenance
decision.

## Goal

Deliver a recoverable, documented release, or close the project with verifiable technical reasons.

## Checks and steps

1. Freeze repositories, commits, patches, toolchains and permitted blobs.
2. Perform a clean, reproducible build and publish hashes.
3. Prepare install and restore instructions with clear warnings.
4. Define the required backups and stop criteria.
5. Repeat the functional matrix and a final long-running test.
6. Document known defects, security, SELinux and performance limitations.
7. Assess patch maintenance, updates and availability of maintainers.
8. Issue a decision: release candidate, restricted experimental use or abandoning the port.

## Exit criterion

Reproducible package with verified documentation and recovery, or a final `NO-GO` report that preserves
all the knowledge gained.
