# Phase 5 -- V23 (logd user root) advances but fails setuid; V24 = definitive fix

Date: 2026-09-18. Source: live ADB shell on V23 + `dmesg`.

## V23 result

`user root` in `logd.rc` passed the V22 failures (cap_set_proc and setgroups no
longer fail: as root there is CAP_SETGID). But `logd` falls at the final step:

```
logd: failed to set AID_LOGD uid     <-- setuid(AID_LOGD)
init: Service 'logd' (pid ..) exited with status 1
```

## Cause (full mechanism)

`drop_privs()` does `cap_set_proc()` setting the EFFECTIVE set to only
`{SETGID, SYSLOG, AUDIT_CONTROL}` -> **clears `CAP_SETUID`**. Then:

```
setuid(AID_LOGD=1036)  // from uid 0
```

In Linux, `setuid()` that CHANGES uid uses `capable(CAP_SETUID)`, not euid==0
directly. Since `cap_set_proc` just removed `CAP_SETUID`, the 0->1036 change gives
**EPERM**.

In Android's normal flow this is NOT seen because init launches `logd` as
`user logd` (uid **1036**) from the start, so `setuid(1036)` is a **no-op**
(target uid == current uid) and does not require `CAP_SETUID`. V23 launched it as root, so
`setuid` does change uid and needs the removed cap. A dead end that way.

## V24 (definitive fix)

`apply-v24-logd-privs.py`:

1. `.rc`: `user root` -> **`user logd`** (init sets uid 1036 + groups, like the normal
   flow). Reverts V23.
2. `main.cpp`: `setgroups`/`setgid`/`setuid` of `drop_privs` **non-fatal** (extends
   the V22 `cap_set_proc` shim).

With init's uid 1036:
- `cap_set_proc` fails (no ambient caps) -> skipped (V22).
- `setgroups({readproc})` fails (no CAP_SETGID) -> skipped (V24); the groups init set
  are kept (`logd system package_info readproc`, includes readproc).
- `setgid(1036)`: current gid is already logd(1036) -> **no-op**, OK.
- `setuid(1036)`: current uid is already 1036 -> **no-op**, OK.
- final `cap_set_proc` (clear) fails -> skipped (V22).

-> `drop_privs` completes, `logd` runs as AID_LOGD with its sockets -> **logcat**.
Change in system.img (logd.rc + logd binary). boot unchanged.

## After V24 (plan)

1. Flash V24, boot to system (logo), adb.
2. `getprop init.svc.logd` = **running**; `logcat -b all -d > .../logcat.txt`.
3. Look for the **SurfaceFlinger** hang opening the display (composer getService /
   createDisplay / HWC2On1Adapter / gralloc) -- the root logo blocker.
