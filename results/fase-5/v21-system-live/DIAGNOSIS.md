# Phase 5 -- V21 (system with adb) boots FAR: system_server alive; SF hung

Date: 2026-09-18. Source: **live ADB shell** on the booted system (V21),
`dmesg` + `/proc` + `service list`. logcat NOT available (logd looping).

## Huge milestone

With V21 (FunctionFS props) adbd comes up in the system boot and gives a **live
root shell** (`uid=0 context=u:r:su:s0`). The boot goes much further than the logo
suggests:

- `zygote` (pid 654) **running**
- `system_server` (pid 696) **running** -- the Java framework booted
- `surfaceflinger` (660), `hwservicemanager`, `servicemanager`, `vold` running
- `vendor.gralloc-2-0` (allocator@2.0, pid 438) and `vendor.hwcomposer-2-1`
  (composer@2.1, pid 662): **no longer in a status-1 loop -- running** (advance over V20)
- `service list` -> 25 services registered (partial boot; normal is >200)

## Root blocker: SurfaceFlinger hung initializing the display

- `SurfaceFlinger` is alive but **does NOT register its binder** (does not appear
  in `service list`; `dumpsys SurfaceFlinger` empty).
- `/proc/660`: **only 1 thread**, State S, in `binder_thread_read`. Its main thread
  made a **synchronous binder call at boot** (display init / composer getService)
  and **waits for a reply that does not come**.
- composer@2.1 (662) and allocator (438): both **idle** in `binder_thread_read`
  (they do not process the transaction).
- `system_server` depends on SurfaceFlinger -> stays at 25 services -> **freeze on
  the logo**.
- `bootanim` never starts (SF gives no display).

The EXACT SF error (why the display hangs) is **only in logcat**.

## Second blocker: logd in a loop -> blind logcat

`dmesg` gives the exact cause:

```
logd: failed to set CAP_SETGID, CAP_SYSLOG or CAP_AUDIT_CONTROL (1)
init: Service 'logd' (pid ....) exited with status 1
init: updatable process 'logd' exited 4 times before boot completed
```

`system/core/logd/main.cpp` `drop_privs()`: `cap_set_proc()` (line ~128) fails with
EPERM on the **3.10** kernel (the ambient/prctl capabilities Android 10 assumes do
not exist) -> `return -1` -> `main()` exits `EXIT_FAILURE` -> init restarts logd every 5 s.
Without logd there is no `/dev/socket/logd*` or logcat.

`lshal` also **segfaults** (the HIDL registration cannot be confirmed that way).

## V22 (fix) -- unblock logcat

`apply-v22-logd-caps.py`: make the two `cap_set_proc` of `drop_privs()`
**NON-FATAL** (warn + continue), same pattern as the pthread shim (V19). logd
still does `setgid/setuid` to AID_LOGD (which work as root) and serves the
main/system/crash buffers over its sockets -> **logcat returns**. Change in system.img.

## After V22 (plan)

1. Flash V22, boot to system (leave it on the logo), direct `adb`.
2. Confirm `init.svc.logd=running` and `adb logcat -b all -d > .../logcat.txt`.
3. Look for the SurfaceFlinger error opening the display (composer getService,
   `createDisplay`, HWC2On1Adapter, gralloc alloc). With that, decide the
   HWC1->composer@2.1 fix (explicit hwc2on1adapter, Spreadtrum display init, or the
   version/name of the HIDL service SF expects).
4. Investigate the `lshal` segfault as a parallel clue of the graphics HIDL stack.
