# Phase 2 -- Kernel gap analysis

## Confirmed baseline

- Linux `3.10.65`, ARM32, SMP and PREEMPT.
- 32-bit Binder, ashmem, sync and ION/ION_SPRD present.
- seccomp and seccomp-filter present.
- cgroups present, but `CONFIG_CGROUP_DEVICE` is disabled.
- `CONFIG_NAMESPACES` is disabled: a major gap for an Android 10 userspace.
- SELinux is compiled, with developer mode and `CHECKREQPROT_VALUE=1`.
- pstore is disabled, reducing boot-failure diagnostics.
- CM 14.1 adds Mali-400/SC8830, UID stats and filesystem changes, but forces
  `androidboot.selinux=permissive`.

## Work needed before running on hardware

1. Reproduce an ARM32 kernel build without changing its ABI yet.
2. Compare AQA4, CM 14.1 and, when it appears, the exact AQJ1 source.
3. Enable and validate the required namespaces and cgroups; backport fixes if the branch does not implement
   them adequately.
4. Keep legacy binder/ashmem/ION initially and adapt Android 10 around them.
5. Add pstore/ramoops if the memory map allows it; this requires prior validation and does not authorize
   flashing.
6. Remove the permissive cmdline and build progressive SELinux policies.
7. Verify the final kernel+DT+ramdisk size within 16 MiB and sign/package DHTB only as a PC test artifact.

## Risk

**HIGH.** The kernel contains the legacy Android blocks, but its age and the absence of namespaces mean an
Android 10 boot is not a simple defconfig change.
