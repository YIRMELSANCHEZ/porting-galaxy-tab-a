# Phase 5 -- V22 (logd binary shim) partial; V23 = logd as root (root fix)

Date: 2026-09-18. Source: live ADB shell on V22 + `dmesg`.

## V22 result

The binary shim (`cap_set_proc` non-fatal in `drop_privs`) **works at its point**
-- dmesg confirms it:

```
logd: V22 non-fatal: cap_set_proc SETGID/SYSLOG/AUDIT_CONTROL failed (1) on legacy
      kernel; continuing without them
logd: failed to set AID_READPROC groups     <-- NEW failure point
init: Service 'logd' (pid ..) exited with status 1
```

`logd` advances further, but falls at the **next** step: `setgroups()` (AID_READPROC).

## Real root cause (finally complete)

`system/core/logd/logd.rc` launches the service like this:

```
service logd /system/bin/logd
    user logd                                  <-- uid 1036, NOT root
    group logd system package_info readproc
    capabilities SYSLOG AUDIT_CONTROL SETGID   <-- via ambient caps
```

In Android 10 the model is: init runs logd as uid `logd` (not root) and grants it
SYSLOG/AUDIT_CONTROL/SETGID via **ambient capabilities**. The **3.10 kernel has NO
ambient capabilities** (they arrived in 4.3) -> logd starts as uid 1036 **without
effective CAP_SETGID**. Then:

- drop_privs's `cap_set_proc()` fails (the V22 shim masked it), and
- `setgroups({AID_READPROC})` fails (needs CAP_SETGID), and
- `setgid/setuid` to AID_LOGD would also fail.

The binary shim can never suffice: the process simply **does not have** the caps
because init could not give them to it.

## Live validation (without reflashing)

With the device's root shell, running `/system/bin/logd` itself **as root**:
`drop_privs` passes **without any error** (neither caps nor AID_READPROC). It
confirms the problem is the startup uid, not the binary.

## V23 (fix) -- logd as root in logd.rc

`apply-v23-logd-rc-root.py`: in the `service logd` block, `user logd` -> `user root`
and **remove** the `capabilities SYSLOG AUDIT_CONTROL SETGID` line. init launches
logd as root with all caps; its own `drop_privs()` does the sequence correctly
(`cap_set_proc` to the subset, `setgroups`, `setgid`/`setuid` to AID_LOGD) and ends
as AID_LOGD serving the buffers -> **logcat returns**. The V22 shim stays as a safety
net. Change in /system/etc/init/logd.rc (system.img). boot unchanged.

## After V23 (plan)

1. Flash V23, boot to system (logo), adb.
2. `getprop init.svc.logd` = **running**; `logcat -b all -d > .../logcat.txt`.
3. Look for the **SurfaceFlinger** hang opening the display (composer getService,
   `createDisplay`, HWC2On1Adapter, gralloc) -- the root blocker keeping the logo
   (SF with 1 thread in binder_thread_read, does not register its binder).
