# SM-T280 (gtexswifi) -- State and TO-DOs (updated 2026-09-21 04:30, V87 on HW; V91 and V92 offline)

## 0. PACKAGES PENDING FLASH (the user tests them on return)
| Package | Content | Risk |
|---|---|---|
| **V91** `SM-T280-android10-todo-sweep-PHASE6-v91-DO-NOT-FLASH.tar.md5` | V87-V90 (traces removed, persistent ANGLE opt-in, sprdwl retry, Wi-Fi recovery V89, **BTCOEX: WIFI-OPEN/CLOSE to wcnd**) + **MED1/GAL1** (MediaProvider scans captures on publish) + **V91b** (valid EGL scale, measured) + `persist.swiftangle.scale=3` by default | low; all verified on HW with the test APK except V90/MED1 (small changes, verified offline) |
| **V92** `SM-T280-android10-camera-PHASE6-v92-DO-NOT-FLASH.tar.md5` | V91 + **CAM1** (camera.provider@2.4 legacy + impl + `android_atomic_or` shim + rc with LD_SHIM_LIBS + VINTF) + **V92b** (linker tolerates the TEXTREL of `libynoise.so` only in `/vendor/bin/hw/` processes) | medium: the chain was tested live up to the blob's `dlopen` (blocked by TEXTREL); the real boot of the 5.1 HAL could not be verified without flashing. If it fails, go back to V91 |
Both: boot.img V75 unchanged (`fe89ef31...`). Odin AP flash, Auto Reboot OFF, no Re-Partition.

**2026-09-21 08:30 -- V91 flashed: bootloop. It is NOT V91.** `system_server` dies in
`LockSettingsService.tryDeriveAuthTokenForUnsecuredPrimaryUser` -> `SyntheticPasswordCrypto.decrypt` ->
`KeyPermanentlyInvalidatedException`. State in /data: the SEC1 test (`locksettings set-pin` at 03:47) left
`spblob/87375c6482c7083b.{pwd,secdis,spblob}` + keystore key `synthetic_password_87375c6482c7083b` **bound
to SID** + `/data/misc/gatekeeper/0`; at 03:50 the PIN was removed leaving `lockscreen.password_type=0` in
`locksettings.db` but with `sp-handle` intact and without regenerating the blob. With a "no-lock" user the
boot tries to decrypt that blob without a credential on every `onUnlockUser` and any exception there is
fatal (`RuntimeException("Failed to decrypt blob")`). There was no reboot between 03:50 and the flash, so
V87 did not show it. Remedy (without reflashing): `scripts/fixlock-sp-orphan.sh` on the tablet (backs up
to `/data/local/tmp/lockstate-backup`, deletes the orphaned blob/key/SID and sets `sp-handle=0`; the
system regenerates a clean SP when a PIN is set). The permission classifier blocks the agent's remote
writes: the user runs it.
**Side finding (08:34):** the flashed V91 **already contains the V92 camera provider**
(`/vendor/bin/hw/android.hardware.camera.provider@2.4-service`, rc `zz-camera-provider-shim.rc`) because
the CAM1 live-test binaries were left in `$OUT` before V91's `systemimage`, but **without** the V92b
linker: `camera provider init failed` (TEXTREL of `libynoise.so`) and `cameraserver` retries every second.
It does not affect the bootloop, but V91 is not the "clean" package described: **V92 is the consistent one**
(same provider + linker). Fix the V91 build if a camera-less package is wanted (`rm` the camera modules in
`$OUT` before `systemimage`).

**2026-09-21 10:30 -- VID2 HARDWARE video achieved (in testing) and V94 package built.**
`SM-T280-android10-hwvideo-PHASE6-v94-DO-NOT-FLASH.tar.md5` (sha256 `864e5ab668f8ae8fe2a8810f573a18a5...`,
boot V75) = V92 + V93 + V94 + V94b. Verified live without flashing (catalog bind mount, VSP chmod, test
APKs): `OMX.sprd.h264.decoder` decodes 1440x810 with 1% CPU; SwiftShader shows NV12. The bottleneck is now
the SwiftShader render-thread/workers synchronization (7 fps in video): KNOWN-ISSUES V1 ("HW unfeasible,
ABI") is refuted: it was `/dev/sprd_vsp` permission + a premature `dlclose` in `SprdOMXPlugin`.
**2026-09-21 12:00 -- V95 (single package, replaces V94):**
`SM-T280-android10-perf-hwvideo-PHASE6-v95-DO-NOT-FLASH.tar.md5` (sha256
`39541978d25d13c7eae1d61a0f41fce6bd12d939b08324ef00496be10fd5d0f1`, boot V75 `fe89ef31...`, system in
package `45025692...`, `V95_STATIC_VERIFY_PASS`) = V92 + V93 + V94 + V94b + V95 (counters, gated) +
V96/V96b (real fences, deferred clears) + V96c/V96d + V97 (libgui) + V97b/V97c (gated H.264 traces,
`hwvideo` switch). Results and the real cause of the frozen video (Unity's resync policy, not the decoder).
Default properties: `scale=3 threads=4 texq=0 mipq=0 nice=10 fence=1 deferclear=1 spin=0 stats=0
bqdrop=1 hwvideo=1 vtrace=0`; all changeable with `setprop persist.swiftangle.<k>` + closing the app
(`hwvideo`/`bqdrop` require restarting the service: `stop vendor.media.omx; start vendor.media.omx`). After
flashing V95: `pm uninstall org.lineageos.gtexswifi.swiftangle` to remove the test APK from /data (the
system copy is the definitive one). The app has a limit on videos that can be watched: do not spend more
video tests except to validate V95.
Tablet state at session close: test mode (bind mounts of `media_codecs.xml`, `libgui.so`,
`libstagefright_sprd_h264dec.so` and VSP chmod; all reverts on reboot) + instrumented V96 test APK
installed; props `scale=4 threads=4 texq=0 mipq=0 nice=10 stats=1` (set `scale 3` and `stats 0`).
When booting V91/V92: optional `pm uninstall org.lineageos.gtexswifi.swiftangle` (removes the test APK from
/data; the system one is identical). Checks: (1) Wi-Fi connects on its own, BT on/off and Wi-Fi still has a
network (`ping`); (2) screenshot -> in Gallery the first one appears and with a size; (3) the target app:
launches, ~3 fps in 3D scenes (scale 3; `setprop persist.swiftangle.scale 2` for more sharpness / 1 for
native); (4) V92: `dumpsys media.camera` with 2 devices, Camera app.

Goal: a tablet 100% usable by a non-technical user (a child) for "an app that requires GLES 3.0"
(audio/video/3D). Flashing always: Odin AP, boot.img + system.img, Auto Reboot OFF, no Re-Partition.

---

## 1. RESOLVED (verified on hardware)

| System | Ver. | Verification | Detail |
|---|---|---|---|
| Boot, launcher, touch | -- | daily use | -- |
| Power button (on/off) | V62 | a press powers on/off | `POWER-BUTTON-FINDINGS.md` (sprdfb panel bug + keylayout) |
| WiFi 2.4 GHz + internet | V53 | ping ~48 ms | HIDL service + supplicant |
| **Bluetooth** A2DP/HFP | V70-V73 | headphones paired, 0 crashes | `BLUETOOTH-FINDINGS.md` (7 chained causes) |
| **Auto-rotation** (K2HH accelerometer) | V70 | rotates | sensors@1.0 + `input` group in its rc |
| SX9306 grip sensor | V68 | listed in sensorservice | -- |
| Audio (speaker + BT) | -- | plays | audio@4.0 |
| Mali-400 GLES2 HW GPU | -- | UI/2D | -- |
| **Power HAL** | V68 | `lshal` power@1.0, loads `power.sc8830.so`, `mHalInteractiveModeEnabled=true`, interactive governor boostpulse 80 ms | checked 2026-09-20 |
| Light HAL / brightness | V68 | light@2.0 | -- |
| DRM ClearKey 1.0/1.1/1.2 | V68 | `lshal` | Widevine no (no blob) |
| memtrack, health, keymaster@4.0, graphics allocator/composer@2.1/mapper | V68 | `lshal` | -- |
| Screenshots: **saving** | -- | valid PNG on disk | the failure was reading (STOR1) |
| **STOR1: /sdcard reading by apps** | **V74** | verified after clean boot: zygote `read=9997,23 write/full=9997,7`, MediaStore with `_size`, 0 `AccessDenied`, gallery with thumbnails | `STOR1-FINDINGS.md` (kernel `propagate_remount` bug) |
| **fd/ION leaks over hwbinder (GFX-ION, captures)** | **V75** | verified: SF/composer fds stable under scroll, Lost RAM 438->38 MB, captures OK after boot | `G1-FINDINGS.md` section 2 (V31 binder did not close `BINDER_TYPE_FDA`) |
| **G1: display capped at 8 fps** | **V76** | verified: `fb_post` 8-11 -> 17-18.5 fps, composer CPU 80% -> 18%; the limit is now the app's render (44 ms/frame in launcher) | `G1-FINDINGS.md` section 3 (uncached FB target ION) |

Sensors the SM-T280 **does not have** (not a failure): gyroscope, magnetometer, ambient light, proximity.

---

## 2. PENDING (agreed order)

### GFX-ION -- **ROOT CAUSE PROVEN, FIX IN V75 (kernel binder)** -- see `G1-FINDINGS.md`
fd and ION memory leak in every process that receives handles over hwbinder: the V31 binder backport does
not close the `BINDER_TYPE_FDA` fds and libhwbinder does not either ("closed in the kernel"). Measured:
composer +649 fds/20 s + ~1 MB/s of pinned ION; SF +305 fds/20 s. Attributed by restarting each process.
Fix `apply-v75-binder-fda-close.py`. Historical symptom text:

#### (historical) intermittent failure allocating graphics buffers (capture "could not be saved")
Observed on V74 right after boot (lowmemorykiller active); 3 later captures via adb OK. Trace:
`GraphicBufferAllocator: Failed to allocate (554 x 391) ... usage 702: 5` (NO_RESOURCES) -> `AHardwareBuffer
... failed (Out of memory)` -> `EGL_BAD_ALLOC` -> `SurfaceControl.screenshot()` returns null ->
`NullPointerException ... createAshmemBitmap()` in `SaveImageInBackgroundTask.<init>`
(GlobalScreenshot.java:249) -> `systemui:screenshot` dies. Lead:
`/sys/kernel/debug/ion/heaps/ion_heap_carveout_overlay` shows **8 MB orphaned** (buffers with no live
client = leak) over a small carveout; if gralloc.sc8830 serves certain `usage` from that carveout, it runs
out and returns NO_RESOURCES under pressure. Tied to G1/memory (1 GB). Review: which heap gralloc routes
each usage to, the carveout size (dts), who leaves orphans (HWC/SF when restarting processes). Verify: `cat
/sys/kernel/debug/ion/heaps/*` (orphaned) and repeated captures after boot.

### APP -- GLES 3.0 required by a class of apps - **HARDWARE BLOCK IDENTIFIED**
Finding (2026-09): some apps declare `<uses-feature glEsVersion=0x30000>` and the stores mark them
incompatible with this device. The SM-T280 has **Mali-400 = GLES 2.0 in hardware**; no driver/port can add
GLES 3.0. An app that requires GLES 3.0 (for example an engine with GLES-3-only shaders) on the Mali
creates a GLES 2 context but finds no shaders -> blank screen. Solution: **SwiftAngle** (SwiftShader, GLES
3.0 on the CPU, as an Android 10 "ANGLE package", per-app opt-in; `debug.angle.backend=1`). State measured
(V77-V88): the driver loads, a GLES 3.0 context is created, the shaders compile and frames are queued to
the SurfaceView. **Real limit:** rasterization runs on the CPU (4 SwiftShader threads), at a few fps; it is
a physical limit of the device. The ANativeWindow scale is adjusted with `persist.swiftangle.scale` (V88
sizes it together with the EGL backbuffer and FrameBuffer). See `V87-CLEAN-WIFI-ANGLE.md`,
`V88-SWIFTANGLE-SCALED-EGL.md`.

### AUDIT 2026-09-21 03:30 -- V87 on HW, re-verification of the "resolved"
| System | State on V87 | Evidence |
|---|---|---|
| STOR1 | OK | zygote `read gid=9997,mask=23 / write,full gid=9997,mask=7`; 94 KB capture on disk |
| GFX-ION | OK | SF fds 82 / composer 34 stable, Lost RAM -8 MB |
| G1 display | OK | `fb_post fps` 56 |
| Rotation | OK | K2HH emits events |
| VID1 | OK | `mediaswcodec` without tombstones; test video played |
| APP GLES3 | UI on screen | 757 ms/frame (scale 1) |
| MED1 | still | `_size=NULL` in MediaStore after capture |
| Wi-Fi (boot) | OK on 2 boots (t=8.5 s and t=138 s with V87 retry) | -- |
| **Bluetooth** | **BROKEN together with Wi-Fi** | see WIFI1/BTCOEX below |

**BTCOEX -- measured root cause (`wcnd` log):** `wcnd` counts CP2's clients: BT sends it `BT-OPEN/BT-CLOSE`
(libbt-vendor) and on 5.1 the Wi-Fi HAL sent `WIFI-OPEN/WIFI-CLOSE`
(`hardware/sprd/wlan/wifi_legacy/wifi_priv.c`). Our A10 `libwifi_hal` **does not notify**, so `wcnd` stays
in `WCND_STATE_CP2_STOPPED` even though Wi-Fi works (the firmware was loaded by `download` at boot). When
BT is turned on: `Enter WCND_STATE_CP2_STARTING from CP2_STOPPED` -> `startwcn` -> **restarts the Marlin**
-> the `sprdwl` driver loses the chip (`cfg80211_report_scan_frame err`, 0 networks, `DisconnectedState`,
does not recover by turning BT off or cycling Wi-Fi). When BT is turned off -> `stopwcn` -> same. And
conversely: BT fails with `startup_timer_expired` when the chip is degraded (285 `ack timeout` at boot with
both races). Reproduced 3 times on a clean boot. **Fix V90** (`apply-v90-wifi-wcnd-notify.py`):
`libwifi_hal` sends `wcn WIFI-OPEN` before loading `sprdwl` and `wcn WIFI-CLOSE` after unloading it
(abstract socket `wcnd`, reply `BTWIFI-CMD OK`). Accumulates V87-V89. Verify: boot -> Wi-Fi connects -> BT
on -> Wi-Fi still has a network (ping) -> BT off -> Wi-Fi still works; log `V90_WCND: 'wcn WIFI-OPEN' -> ...
BTWIFI-CMD OK` and `wcnd` in `CP2_STARTED`.

### WIFI1 -- boot race and SC2331/Marlin client drop - V89 CANDIDATE, HW PENDING
Seen at V86's boot (01:33): `dmesg` `[SC2331] wlan_module_init sdio is not ready` at t=9 s (the CP2
firmware was still downloading over SDIO) -> no `wlan0` -> the legacy HAL fails `Failed to set WiFi
interface up` -> "Wi-Fi is disabled" even though `wifi_on=1`. Live fix verified: `rmmod sprdwl; insmod
/system/lib/modules/sprdwl.ko; svc wifi enable` -> `wlan_module_init ok!`, connects. Fix pending: load
`sprdwl` only when `download` finishes (e.g. from wcnd/`init.wifi.rc` with `on property:` of the download
result, or a retry in the driver). For a child this is critical (without Wi-Fi the app says "not
connected").

V87 patches `libwifi_hal`: the driver returns exactly `-EPERM` when `get_sdiohal_status()!=1`; it is
retried **only on EPERM** every 500 ms up to 15 s. `EEXIST` is still success and any other error fails
immediately. It avoids depending on a private property of the `download`/`wcnd` blob. Verify after flashing
with several boots: `wlan0` must appear and Wi-Fi connect without `rmmod/insmod`; the log may show V87
retries before success.

**V87 result on HW:** there is a second race after loading the module. During the simultaneous boot of
Bluetooth and Wi-Fi, `wlan0` appears but SC2331 loses the wake handshake (`-110`), scans expire and
`CMD_STA_START_FAILURE` leaves Wi-Fi off. A late manual enable worked: first scan failed, second scan with
seven networks, WPA and DHCP complete. **V89** automates that recovery: normal client-mode teardown, wait
15 s and up to six restarts while the toggle stays ON; counter reset after 60 s stable or a manual cycle.
It does not restart `wcnd`/Marlin and does not touch Bluetooth. V89 accumulates V88 and passed all offline
validations.

### VID1 -- software video: `mediaswcodec` dies allocating the output buffer - **RESOLVED in V84+V85+V86 (verified)**
Three links in the swcodec APEX `sphal` namespace: V84 `/system/lib` (VNDK-SP), V85 `/system/lib/hw`
(gralloc module), V86 `libdither` without `libbinder/libandroid_runtime` (it pulled in `libnativehelper`,
only in the runtime APEX). Verified: `mediaswcodec` without a crash, the app plays the intro video. Pending
to check the browser video. Original analysis text:
Any video (the target app, browser) -> `C2SoftAvcDec::ensureDecoderState` ->
`C2AllocatorGralloc::Impl::newGraphicAllocation` SIGSEGV (null). Measured cause: `vndksupport: Could not
load /vendor/lib/hw/android.hardware.graphics.mapper@2.0-impl.so from sphal namespace: library
"android.hardware.graphics.mapper@2.0.so" not found`. The `com.android.media.swcodec` APEX carries its own
`ld.config.txt` (`frameworks/av/apex/`) whose `sphal` namespace looks for the VNDK-SP in
`/system/lib/vndk-sp29`, nonexistent in this legacy build (`ro.vndk.lite=true`, libs in `/system/lib`). V84
adds `/system/${LIB}` to the sphal search path. Verify after flashing: play a browser video and `logcat |
grep -E "swcodec|vndksupport"` without a crash. It also explains "I still don't see images in browser
videos".

### G1 -- graphics performance - **VERIFIED in V76 (display cap removed)**; the OSD/DISPC step remains optional
State after V76: the display no longer limits; the limit is the app's render (Mali-400/A7). Decide the
OSD/DISPC step only if performance is resumed. Minor pending: `_size=NULL` in MediaStore for new captures
until a scan (does not block). Original analysis:
Correction to the previous analysis: the SPRD HWC and gralloc are **in source** (not a blob). The measured
bottleneck is `fb_post`'s 4 MB/frame `memcpy` reading the FB target from ION **uncached** (~100 ms/frame).
V76 makes it cacheable (`SW_READ` -> `ion_invalidate_fd` in lock). The fb-slot page-flip (V33) is
unfeasible on A10 (the allocator in another process frees the slot on export; Mali does not render into fb
without UMP). Next step if not enough: FB target in a contiguous heap + the DISPC OSD plane
(HWC+gralloc+dts). Verify V76: `logcat | grep "fb_post fps"` with scroll (previously 8-11).

### CAM1 -- camera - priority MEDIUM - difficulty MEDIUM
`dumpsys media.camera` -> 0 devices. 15 SPRD blobs present; missing
`android.hardware.camera.provider@2.4-service` (+legacy) and VINTF; the `libmemoryheapion.so` blob needs
the symbol `android_atomic_or` -> shim via `LD_SHIM_LIBS` (the linker supports it). 5.1 ABI risk. Raises in
priority if the app uses it.

### SEC1 -- PIN/pattern - priority LOW-MEDIUM - **cause measured 2026-09-21: not gatekeeper, it is keystore**
`gatekeeperd` already uses `SoftGateKeeperDevice` when there is no HAL (system/core/gatekeeperd). Test:
`locksettings set-pin 2468` -> "Pin set", but `verify` -> "user has no password" and in the log
`SyntheticPasswordCrypto.decrypt` -> `KeyPermanentlyInvalidatedException` (keystore returns an invalid blob
for the synthetic password key bound to authentication). The software keymaster@4.0 does not validate/accept
the SoftGateKeeper auth tokens (no shared HMAC) or rejects keys with `USER_SECURE_ID`. Options: (a)
software keymaster with auth-token verification disabled (patch in `system/keymaster`
`SoftKeymasterContext`/`AndroidKeymaster::BeginOperation` to ignore `KM_TAG_USER_AUTH_TYPE` when there is no
TEE), (b) accept without a lock (child's tablet). Not touched in V91.
**Precision 2026-09-21 08:30** (source `KeyStore.getInvalidKeyException`): the exception comes from the
`KM_ERROR_KEY_USER_NOT_AUTHENTICATED/OP_AUTH_NEEDED` branch with the key bound to `USER_SECURE_ID` and
`GateKeeper.getSecureUserId()` not matching (or 0). That is: keystore/keymaster does reject for "user not
authenticated", and the root SID the framework sees is not the key's. Next step when resumed: compare the
handle's SID (`/data/misc/gatekeeper/0`) with the key's `USER_SECURE_ID` (`keystore_cli_v2`) and the one in
the auth token `gatekeeperd` sends to keystore (`AddAuthenticationToken` in the log). **Warning**: never
remove a PIN by editing `locksettings.db`; it leaves an orphan SP that crashes system_server on every boot
(see section 0).

### MED1 -- MediaStore does not fill `_size` of new captures until a scan - priority LOW - difficulty LOW-MEDIUM
Observed on V74/V76: SystemUI publishes the capture (`IS_PENDING` 1->0) and MediaProvider (legacy,
`packages/providers/MediaProvider`) should trigger `scanFile` in `update()` (lines ~4660/5088), but the row
stays `_size=NULL,width=NULL` until a `MEDIA_SCANNER_SCAN_FILE` or the boot scan. The image is visible and
opens fine; it only affects the size/dimensions shown in listings. Review why the publish `triggerScan`
does not update (`_data` null in `RELATIVE_PATH` inserts?, a silent failure in `ModernMediaScanner.scanFile`?).
Verify: `content query --uri content://media/external/images/media --projection _display_name:_size` right
after a capture -> `_size` with a value without a manual scan.

### GAL1 -- a gallery that sorts by creation date (not by name) - priority LOW - difficulty LOW
Requested by the user (2026-09-21). The current gallery (Gallery2/`com.android.gallery3d`) sorts by name.
Options: adjust the order in Gallery2 (source in `packages/apps/Gallery2`, `MediaSet`/`LocalAlbum` order by
`datetaken`/`date_added` DESC) or replace it with a lightweight gallery (e.g. Simple Gallery/Fossify from
F-Droid) set to "sort by date". Depends on MED1 if the order uses `date_added`/`datetaken` (new captures
have them; `_size` no).

### Minor - priority LOW
- **Battery saver**: the setting works (`mSettingBatterySaverEnabled=true`); Android suppresses it while
  charging over USB -> verify with the cable disconnected.
- **Thermal HAL** absent: the kernel throttles on its own (thermal_zone0/1 + cooling_device0). Optional.
- **Vibrator**: **closed** -- the DTS `sprd-scx35_gtexswifi_rev0x.dts` has no vibrator node and the
  defconfig has `CONFIG_SC_VIBRATOR`/`CONFIG_SPRD_VIBRATOR_2723` disabled: the SM-T280 has no motor.
- **V1 software-only video**: 5.1 OMX blobs ABI-incompatible (crash in makeComponentInstance). Accepted;
  depends on G1 for fps.
- **A1**: watch transient audioserver/keystore crashes at boot (stabilized).

### Out of scope (decided)
- **GPS1 GNSS**: deferred unless the app needs it (ICU 51, legacy OpenSSL, renamed libs).
- **Widevine**: no blob for the chip; at most software L3 if the app requires it.

---

## 3. Systemic port pattern (for any missing HAL)
The 5.1 blob/HAL exists in /system/lib/hw but the **HIDL service + VINTF entry + init rc** are missing
(+ sepolicy; Permissive helps). Mechanics: PRODUCT_PACKAGES in device.mk + manifest fragment + the
service rc, verifying the 5.1 blob's ABI in the service's logcat. Traps already seen: AID `net_bt_stack`
does not exist on A10 (use numeric GID 3008); kernel 3.10 without ambient caps (`capabilities` in rc ->
CapEff=0); daemons that setuid themselves must not carry `user`.

## 4. Compact history of causes (resolved)
- **Button**: the sprdfb panel did not resume on A10 (`late_resume` never arrives) + `WAKE` in the .kl
  invalidated the keylayout.
- **BT**: no HIDL service -> invalid GID -> ini with unknown keys -> failed ttyS0 chown -> LPM put the chip
  to sleep -> `wcnd` without caps (user system) -> VSC 0xFD53 not supported.
- **Rotation**: sensors@1.0 service without the `input` group (EPERM on the accelerometer node).
- **STOR1**: the kernel's `propagate_remount` skipped zygote's namespace.
- **V68 bootloop**: camera.provider and gnss without compatible blobs -> removed in V69.

## 5. Useful diagnostic commands
- HALs: `lshal | grep -E "sensors|power|camera|drm|gatekeeper|light|thermal|bluetooth"`.
- Storage: `grep " /storage/emulated " /proc/<pid>/mountinfo` (expected `gid=9997,mask=7`);
  `content query --uri content://media/external/images/media --projection _display_name:_size`.
- BT: `svc bluetooth enable`; `dumpsys bluetooth_manager`; snoop with
  `setprop persist.bluetooth.btsnoopdefaultmode full`.
- Graphics: `dumpsys SurfaceFlinger`; `getprop | grep -iE "hwc|debug.sf"`.
- Camera: `dumpsys media.camera`. Sensors: `dumpsys sensorservice`.
