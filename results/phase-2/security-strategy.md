# Phase 2 -- Security strategy

The device is legacy non-Treble and has no vendor partition. Android 10 allows a legacy linker-namespace
configuration for non-Treble devices, but this does not guarantee that the Lollipop blobs will link.

Principles:

- The final goal is SELinux **enforcing**.
- Permissive mode could only be used as a temporary bring-up instrument in an expressly authorized phase;
  it is not an acceptable result.
- Replace `SERVICES_WITHOUT_SELINUX_DOMAIN` with concrete domains.
- Avoid global allow rules, `dac_override`, execution from data and shims that disable validations.
- Limit linker exceptions to libraries identified by the ELF inventory.
- Separate proprietary blobs from publishable code and keep provenance/hash.
- Do not reuse precompiled host executables from the historical tree without rebuilding or auditing them.

Current risk: **HIGH**, due to CM 14.1's permissive cmdline and the private dependencies of old blobs.
