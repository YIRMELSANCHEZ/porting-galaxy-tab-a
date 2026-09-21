# SM-T280 (gtexswifi) -- Deep analysis of incomplete systems (to integrate in upcoming Vs)

State after V69 (boots stably; good V68 HALs kept). Analysis with HW data + readelf of the 5.1 blobs
(2026-09-20). Goal: give the agent what it needs to integrate BT, camera, rotation and the rest, with root
cause, symbols, feasibility and verification.

Golden rule learned with V68: **a HAL that HANGS system_server (e.g. GNSS in
GnssLocationProvider.class_init_native) causes a BOOTLOOP** (the Watchdog kills system_server ~100s); one
that only crashes (camera) does not block boot but spams. Add HALs one at a time or ensure a graceful
failure.

---

## 1. BLUETOOTH -- the easiest. CLEAN blob; only the bdaddr is missing from the HAL
**State:** `android.hardware.bluetooth@1.0::IBluetoothHci` REGISTERS, but on calling `initialize()` the
service **aborts (SIGABRT)**.
**Root cause (tombstone_42):** `Abort message: 'Open: No Bluetooth Address!'` in `VendorInterface::Open` ->
`__android_log_assert` -> abort. The HAL cannot obtain the Bluetooth MAC.
**Key evidence:**
- The bdaddr **exists and is valid**: `/efs/bluetooth/bt_addr` = `D0:B1:28:**:**:**`, but permissions
  `-rw-r----- radio 3008` (0640). The `@1.0-service` runs as `bluetooth` -> **cannot read** the file (it
  is not in group `3008`/`radio`) -> empty address -> fatal assert.
- **readelf of `libbt-vendor.so`: NO missing 5.1 symbols** (only libc/libcutils/liblog/libm/libstdc++,
  all present on A10). So it is NOT an ABI problem. It is only the bdaddr access.
**Fix (pick one):**
- Give the HAL access: add group `radio`/gid 3008 (or the bt_addr's group) to the service in its init .rc
  (`group bluetooth net_bt_admin net_bt radio`), or
- Expose the MAC via property at boot: read `/efs/bluetooth/bt_addr` in init and `setprop`
  `persist.service.bdroid.bdaddr` (or `ro.boot.btmacaddr`), which the impl also consults, or
- `chmod`/`chown` the bt_addr so `bluetooth` can read it (less clean).
**Verify:** `dumpsys bluetooth_manager` -> `enabled: true, state: ON, address=D0:B1:28:...`; enable BT in
Settings and pair. **Feasibility: HIGH.**

## 2. CAMERA -- SPRD blob chain + old C++ ABIs. Laborious/risky
**State:** V68 added it and it **crashed in a loop** (does not block boot, but spams); removed in V69.
**readelf of `camera.sc8830.so`:**
- **NEEDED (SPRD deps that must exist):** libAF.so, libAl_Awb_v2.so, libae.so, libaf_running.so,
  libaf_tune.so, libawb.so, libcalibration.so, libdeflicker.so, liblsc.so, **libmemoryheapion.so**,
  libsft_af_ctrl.so, libspaf.so, libsprdlsc.so, libynoise.so + standard (libbinder, libcamera_client,
  libgui, libui, libutils, libcamera_metadata, libhardware).
- **Critical UND:** old Android C++ ABIs -- `android::CameraParameters`, `android::ISurfaceComposer`,
  `android::MemoryHeapBase`, `android::MemoryBase`, `String8/String16/Vector/RefBase`, `hw_get_module`,
  `__android_log_print`. The `AF_*/awb_*/ae_*/lsc_*` are provided by the SPRD blobs (NEEDED).
**Risk:** the blob is from Android 5.1. `CameraParameters`/`ISurfaceComposer`/`MemoryHeapBase` have an ABI
that **may not match** A10 (libcamera_client/libgui). And `libmemoryheapion.so` (SPRD) is suspected of
referencing old `android_atomic_*` (verify with readelf of that lib). The concrete crash is in that chain.
**How to integrate it (plan):**
1. Confirm that ALL the SPRD NEEDED (libAF, libawb, libmemoryheapion, etc.) are copied to
   /system(/vendor)/lib. If any is missing -> dlopen fails.
2. Run the camera service and **read the tombstone** for the exact symbol/lib that crashes.
3. If it is an old libcutils/atomic symbol -> **shim** (see section 5). If it is a CameraParameters/gui ABI
   -> much harder (would require a wrapper or patching); consider a timebox.
**Verify:** `dumpsys media.camera` lists cameras; the Camera app previews.
**Feasibility: MEDIUM-LOW** (depends on the type of symbol that crashes; get the tombstone first).

## 3. GNSS -- practically UNFEASIBLE. Recommended to leave out
**State:** V68 added it and it **hung system_server** (bootloop) in
`GnssLocationProvider.class_init_native()`.
**readelf of `gps.default.so`:**
- **NEEDED with obfuscated/nonexistent names:** `libool.so`, `libcrptoo.so`, `libicuoc.so` (renamed
  versions of libssl/libcrypto/libicuuc that are **not shipped** on A10).
- **UND impossible on A10:** **ICU 51** (`ucnv_open_51`, `ucnv_convertEx_51`, ... -- A10 ships ICU 63+,
  those versioned symbols do NOT exist); **old OpenSSL** (`TLSv1_client_method`, `TLSv1_1_client_method`,
  `SSL_library_init`... removed in A10's BoringSSL); `androidGetTid`, `androidSetThreadPriority` (old
  libcutils).
**Conclusion:** it would require shipping ICU 51 + classic OpenSSL + the renamed libs + a libcutils shim.
It is too much and fragile. **For an indoor WiFi tablet, GPS adds nothing.** **Recommendation: do NOT
integrate GNSS.** If ever wanted, it is a project of its own (porting/packaging ICU51+legacy OpenSSL).

## 4. AUTO-ROTATION (R1) -- sensor enumerated but with NO data
**State:** `dumpsys sensorservice` lists the accelerometer (`K2HH Acceleration | STM |
android.sensor.accelerometer`), but: **0 active connections, 0 recent events**, and
`/sys/class/sensors/accelerometer_sensor/raw_data = 0,0,0`. `settings accelerometer_rotation=1`, but
`WindowManager mOrientation=-1` (listener with no data) -> does not rotate.
**Diagnosis:** the sensors HAL (@1.0 over `sensors.sc8830.so`) **enumerates** the sensor but **no events
flow**. There is no `enable` node in that sysfs (the real enable is done by the HAL). Possible causes:
- The legacy HAL's `activate()/poll()` under the HIDL @1.0 wrapper does not deliver events (typical of an
  old sensors HAL with the multihal/wrapper).
- The sensor's **metadata** (minDelay/maxRange/resolution) arrives invalid -> the framework does not use it
  for orientation (or the WindowOrientationListener does not activate it).
**How to integrate it:**
1. Review the @1.0 wrapper: confirm that `poll()` returns events from `sensors.sc8830.so` (sensors service
   log; try an app that reads the accelerometer and see whether `active connections` rises and `raw_data`
   changes when moving).
2. Check the sensor metadata (detailed dumpsys): minDelay>0, maxRange/resolution !=0.
3. Confirm the WindowOrientationListener activates (launcher orientation not locked).
**Feasibility: MEDIUM.** The sensor is half-wired; the data still needs to flow up.

## 5. SHIM strategy for 5.1 blobs (for camera and others)
Several blobs reference Android 5.1 symbols removed on A10 (`androidGetTid`, `androidSetThreadPriority`,
`android_atomic_*`, etc.). The standard pattern is a **shim library** that re-exports them, loaded via
`LD_SHIM`/`__ANDROID_SHIM__` or linked into the wrapper. It helps to:
- readelf each SPRD dep (libmemoryheapion.so, libAF.so, ...) to list the "old" UNDs.
- Create a `libgtexcompat.so` that implements those symbols (androidGetTid -> gettid;
  androidSetThreadPriority -> setpriority; android_atomic_* -> __sync_*), and apply it via shim.
- BT does NOT need it (clean blob). GNSS needs it but also has ICU51/OpenSSL (unfeasible).

## 6. State of what ALREADY works (do not touch)
V68/V69 left REGISTERED and OK: `power@1.0` (smoothness), `light@2.0`, `memtrack@1.0`, `drm@1.2
clearkey`, `sensors@1.0` (enumerates), `bluetooth@1.0` (registers; bdaddr pending). Stable boot,
WiFi+internet, audio, button (V62-V67), sw video.

## 7. Suggested priority for the next V
1. **BT (section 1)** -- bdaddr fix, HIGH feasibility, high usability value.
2. **Rotation (section 4)** -- wire the accelerometer data flow, MEDIUM.
3. **Camera (section 2)** -- get the tombstone of the exact symbol and decide (shim vs unfeasible ABI),
   timebox.
4. **GNSS (section 3)** -- do NOT integrate (unfeasible/not needed).
Rule: add each HAL and **test boot** before piling up, so as not to repeat the V68 bootloop.

## Diagnostic commands used
- BT tombstone: `cat /data/tombstones/tombstone_NN | grep 'Abort message'`.
- bdaddr: `ls -l /efs/bluetooth/bt_addr; cat /efs/bluetooth/bt_addr`.
- Symbols: `<toolchain>/arm-linux-androideabi-readelf --dyn-syms <blob>.so | grep ' UND '`;
  `... -d <blob>.so | grep NEEDED`.
- Rotation: `dumpsys sensorservice`; `cat /sys/class/sensors/accelerometer_sensor/raw_data`;
  `dumpsys window | grep -i mOrientation`.
