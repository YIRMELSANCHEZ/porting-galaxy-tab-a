# Phase 6 -- Analysis and detailed plan: framework bring-up to the launcher

Date: 2026-09-18. Base: consolidated phase 5 (graphics solved, V34 flashed, boot `8e11eb52` with the
binder FDA kernel). Goal: **boot the Java framework unattended, up to the launcher/home** (and from there
to installing/launching the target app).

## Phase success criterion

1. `getprop sys.boot_completed` == `1` on a normal boot (no manual commands).
2. SystemUI + launcher visible and stable (no system_server loop).
3. Working touch input (to install/use the app).
Intermediate metric: number of services in `service list` rising above 200 and stable.

## Strategy (order matters)

The current PMS/SF diagnosis is **contaminated**: zygote was started manually and late (`ctl.start
zygote`), which produced a double system_server (1399/1618) and a race with installd (`Installer: installd
not found; trying again`). Therefore:

> **Phase 6 golden rule: first get a clean auto-boot (6.1), and RE-DIAGNOSE PMS/SF/audio on a normal boot
> before touching them.** Do not optimize 6.2/6.3 with manual-boot data.

Sequence: 6.1 (auto-boot) -> capture a clean boot -> 6.4 (silence/fix audioserver to clean logs) -> 6.2
(PMS/dex2oat) -> 6.3 (SF) -> SystemUI/launcher.

---

## 6.1 -- Framework auto-boot (V35) -- FIRST

**Diagnosis (validated):** zygote and system_server ARE functional (manually they reach 32 services). They
do not start on their own because the init triggers depend on `ro.crypto.state`:
- `on zygote-start && property:ro.crypto.state=unencrypted` (init.rc:638) -> `start zygote`
- `on nonencrypted` (init.rc:770) -> `class_start main` + `class_start late_start`

`ro.crypto.state` is **EMPTY** at runtime. It is set by **vold** (`system/vold/cryptfs.cpp`, not fs_mgr);
with /data `formattable` (fstab without `encryptable`/`fileencryption`) the vold path that sets
`unencrypted` is not reached. Also, `on nonencrypted` has no visible `trigger nonencrypted` to fire it ->
the "nonencrypted" route is dead here.

**V35 fix (plan A -- the most direct and controlled):** in the ramdisk, in `init.sc8830.rc` `on
post-fs-data` (AT THE END, once /data is mounted and structured), add:
```
    setprop ro.crypto.state unencrypted
    trigger nonencrypted
```
`setprop ro.crypto.state unencrypted` fires `on zygote-start && ...unencrypted` (-> start zygote) as soon
as zygote-start is processed; and `trigger nonencrypted` fires `on nonencrypted` (-> class_start main). It
is a ramdisk change -> **boot.img changes** (over the V31 FDA kernel). script:
`apply-v35-crypto-state-unencrypted.py`.
- **Critical timing:** NOT before post-fs-data (zygote needs /data). Place it after the `mkdir`/`init_user0`
  of /data.
- **Plan B (if A is not enough):** add directly at the same point `class_start main` + `class_start
  late_start` (without depending on ro.crypto.state).
- **Plan C (cleaner, more work):** fix vold so it sets ro.crypto.state (investigate why the formattable
  path does not).

**Verification after flashing V35:**
- `getprop init.svc.zygote` == running (normal boot, no commands).
- `ps -A | grep system_server` present. `service list | wc -l` rising.
- Capture a CLEAN `logcat -b all` -> baseline for 6.2/6.3/6.4.

**Risk:** if class_start main fires too early or twice -> double zygote. Mitigation: place the trigger
once, at the end of post-fs-data, and verify there is no double system_server.

---

## 6.2 -- PackageManagerService / dex2oat (slow first boot)

**Main suspicion:** first boot = dex2oat compiles all the /system apps. On a Cortex-A7 + eMMC this takes a
LONG time; the **system_server Watchdog (60s)** can kill it before it finishes -> loop. Signal already
seen: `Watchdog WAITED_HALF` during `packagemanagermain`. (The `installd not found` was a manual-boot
race; re-evaluate.)

**Attack plan (after a clean boot):**
1. Confirm whether dex2oat runs and progresses: `ps | grep dex2oat`, `logcat | grep dex2oat`, see whether
   it advances app by app or hangs on one.
2. If it is slow but progressing: options to make the first boot fit:
   - `pm.dexopt.first-boot=quicken` / `verify` (less work than `speed`) via PRODUCT_PROPERTY_OVERRIDES.
   - `WITH_DEXPREOPT := true` (precompile at build -> no dex2oat on first boot; increases system.img but
     removes the bottleneck). Assess size (SYSTEM partition).
   - As a diagnostic: raise the Watchdog timeout or set PMS to interpret-only
     (`dalvik.vm.dex2oat-filter=verify-none` or `pm.dexopt.*=verify`).
3. If it hangs on a specific APK: identify it and exclude/repair it.

**Goal:** PMS finishes the first scan without the Watchdog killing system_server.

---

## 6.3 -- SurfaceFlinger restarts when system_server connects

**Symptom (contaminated):** `BootAnimation: SurfaceFlinger died`. It may be an artifact of the manual
late-start (SF already had bootanim and system_server took the display late). **Plan:** re-evaluate ONLY
after 6.1 (clean boot). If SF keeps restarting:
- See SF's exact crash in logcat (when creating the second display, receiving vsync from system_server, on
  hotplug?).
- Suspicions: DisplayManager<->HWC2OnFbAdapter interaction (vsync, hotplug, modes), or the V34 FBIOPAN
  path under real composition load.
It is probably NOT blocking for boot_completed (SF restarts and continues), but it is for UI stability.

---

## 6.4 -- audioserver SIGSEGV in a loop (clean up and fix)

**Diagnosis:** `AudioFlinger::AudioFlinger()` null-deref every 5s; the audio HAL does not register
`android.hardware.audio@2.0/4.0/5.0::IDevicesFactory` (hwservicemanager cannot find it). The SPRD audio
HAL is **source** (`hardware/sprd/audio/sc8830`).

**Plan:**
- **Short term (clean boot):** temporarily disable audioserver (mark the service `disabled` in its .rc, or
  remove it from PRODUCT_PACKAGES) to remove the noise/CPU and isolate 6.2/6.3. The UI can boot without
  audio.
- **Medium term (fix):** add the SPRD audio HAL service (`android.hardware.audio@N.0-service` + impl
  `audio.primary.sc8830`/`hardware/sprd/audio/sc8830`) to PRODUCT_PACKAGES + VINTF entries, analogous to
  what was done with graphics (V20/V25). Verify that AudioFlinger stops crashing once it gets
  IDevicesFactory.

---

## Foreseeable later blockers (not yet confirmed)

- **SystemUI / launcher**: on reaching boot_completed, SystemUI needs graphics (already ok) + input. Watch
  RenderThread/HWUI (it uses Mali GLES, should work).
- **Input**: touchscreen (driver `mip4_ts` seen in dmesg) -> InputFlinger/EventHub. Verify `/dev/input/*`
  and that events arrive.
- **keystore/keymaster**: if some service requires it. keymaster was pending.
- **Other HALs** (sensors, light, power) -- they degrade but do not block the launcher.

## Method (same as phase 5)
- Build as `lineage`: `wsl.exe -u lineage bash -lc '.../build-full-rom.sh'`. Package with `prepare-vNN`.
  Avoid inline variables in `wsl -lc`.
- Logs: `adb.exe` repo + `MSYS_NO_PATHCONV=1`; system has adbd (ffs V21).
- Flashing: user only, Odin AP, Auto Reboot OFF, no PIT. boot.img changes in V35.
- Document each iteration: `phase-6/vNN-*/DIAGNOSIS.md` + HANDOFF + ARTIFACTS.
- Rescue available: `SM-T280-AQJ1-STOCK-BOOT-SYSTEM-ONLY-RESTORE.tar.md5`.

## Immediate first step
Implement and build **V35** (`ro.crypto.state=unencrypted` + `trigger nonencrypted` at the end of
post-fs-data). Flash -> confirm zygote/system_server auto-boot on a normal boot -> capture a clean logcat
-> re-plan 6.2/6.3/6.4 with that data.
