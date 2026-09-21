# Phase 6 -- V36: hwservicemanager STABLE (6.2 resolved). New root cause: JIT SIGSEGV

Date: 2026-09-19. Source: clean boot with V36 flashed, `results/fase-6/v36-system-live/` (logcat.txt,
dmesg.txt, ps-A.txt). User reports: "animation" (graphics OK) and a hang.

## 6.2 RESOLVED -- hwservicemanager no longer crashes

With the device VINTF manifest (V36, `/vendor/etc/vintf/manifest.xml`):
- `init.svc.hwservicemanager = running` (before: crash-loop from a null-deref in libvintf).
- `ps`: hwservicemanager pid 155 alive in `SyS_epoll_wait`, serving `interface_start`.
- `dmesg`: NO `Service 'hwservicemanager' received signal 11`. Confirmed stable.
- servicemanager/vndservicemanager/surfaceflinger/vold/logd = running.
- zygote (app_process pid 4394) and system_server (pid 4454) DO start and advance.

## NEW ROOT CAUSE (6.3): system_server crashes in the JIT -> restart loop

Sequence per cycle (~every 5 s), reproducible:
1. zygote forks system_server; StartWatchdog OK.
2. system_server advances up to PackageManager (scan of /system/.../overlay, framework).
3. Mid-scan:
   `F libc: Fatal signal 11 (SIGSEGV), code 2 (SEGV_ACCERR), fault addr 0xa749c014`
   `      in tid NNNN (Jit thread pool), pid MMMM (system_server)`
4. `Zygote: Exit zygote because system server (pid MMMM) has terminated` -> the whole zygote dies and
   relaunches. `sys.boot_completed` is never reached.

Fault addresses per cycle: 0xa749c014, 0xa7400014, 0xa749d014 (same mmap region). The culprit thread is
always "Jit thread pool" (ART's JIT compiler).

### Why (kernel 3.10 without memfd_create)

`cat /proc/version` = Linux 3.10.108. ART's JIT on Android 10 maps the code cache with a dual RW/RX view
backed by `memfd_create` (syscall added in kernel 3.17). On 3.10 it does not exist -> the dual mapping
fails -> the execution view is not left with PROT_EXEC -> when running the freshly compiled code, the MMU
throws SEGV_ACCERR (code 2 = access with wrong permissions). It is the classic JIT failure on a pre-3.17
kernel.

`dalvik.vm.usejit` at runtime = true (default of runtime_libart.mk).

## V37 (fix) -- disable the JIT

`apply-v37-disable-jit.py`: adds `dalvik.vm.usejit=false` (+ usejitprofiles=false) to the
`PRODUCT_PROPERTY_OVERRIDES` block of device.mk (wins over the default =true). ART switches to interpreter +
AOT (dex2oat produces file-backed .odex with PROT_EXEC, which DOES work on 3.10) and does not create the
JIT thread or the dual cache -> the SEGV disappears. Only changes system.img (build.prop); boot = V35
(27c04393). Cost: less peak performance; recoverable if memfd_create is backported to the kernel (future).

Expected success: system_server passes PackageManager without dying, starts the services, and reaches
`sys.boot_completed=1` (or at least much further). Re-diagnose whatever remains (audioserver SIGSEGV,
keystore SIGABRT -- see below).

## Secondary blockers pending (after V37)

- **audioserver**: `Fatal signal 11 (SIGSEGV) ... in tid (audioserver)` on every cycle, in AudioFlinger.
  SPRD audio HAL (hardware/sprd/audio/sc8830). May be independent of the JIT; re-evaluate after V37 (phase
  6.4).
- **keystore**: `Fatal signal 6 (SIGABRT), SI_QUEUE ... (keystore)`. Probable failure contacting the
  keymaster HAL or a boot assert. Re-evaluate after V37.
- Note: some of these crashes relaunch on every zygote restart; with the loop cut (V37), see which really
  persist on a stable boot.

## Ambient capabilities (kernel 3.10) -- known noise, not blocking here
`E libc: failed to raise ambient capability N: Invalid argument` (kernel 3.10 without ambient caps).
Already mitigated where it mattered (logd V22-V24). Watch whether it affects audioserver/keystore.
