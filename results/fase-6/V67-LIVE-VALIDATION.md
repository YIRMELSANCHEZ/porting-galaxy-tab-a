# V67 -- hardware validation and log audit

Date: 2026-09-20
Device: Samsung SM-T280 `gtexswifi`
Screen/button result: **PASS**

## Summary

The user confirmed that screen off and on were fixed. The ADB evidence shows that V67 runs the correct path
end to end, finishes each transition and also resolves the OFF->ON race before the legacy suspend finishes.

The audit found no critical system regressions caused by V67. It did find several pre-existing or
independent issues: EFS/productinfo not mounted, Bluetooth without a HIDL HAL, incomplete `wcnd`, incorrect
use of an fd in the gralloc ION invalidation, Wi-Fi scan timeouts and two additional sources of periodic
noise in audio/memtrack.

## Runtime identity

- `sys.boot_completed=1`
- kernel: `Linux 3.10.108-g95996f39350-dirty #30 SMP PREEMPT`, corresponding to V67
- stable processes during the capture:
  - Composer PID 217
  - SurfaceFlinger PID 228
  - system_server PID 402
  - SystemUI PID 585
  - Launcher3 PID 855
- memory: 1,490,128 KiB total; no swap used during the sample

## Off and on evidence

Userspace logged the new path actually loaded:

```text
V67 HWC2 fb power mode 0 complete (blank=4)
V67 HWC2 fb power mode 2 complete (blank=0)
```

The kernel logged the physical result:

```text
[59.844360] sprdfb: V67 fb_blank OFF complete
[60.417938] sprdfb: V67 fb_blank cancelling pending legacy suspend
[60.654937] sprdfb: V67 fb_blank ON complete
[60.864715] mip4_ts - Enabled
[61.094390] tc300k_resume
```

Three additional cycles were then observed:

| Cycle | OFF complete | ON complete | approx OFF | approx ON |
|---|---:|---:|---:|---:|
| 1 | 65.274 s | 66.265 s | 313 ms | 236 ms |
| 2 | 70.794 s | 71.675 s | 319 ms | 248 ms |
| 3 | 73.034 s | 73.415 s | 315 ms | 237 ms |

No `OFF complete` appeared after the last ON, even several minutes later. Real touch events were also
captured after the resume.

Final state:

- `mWakefulness=Awake`
- `mWakefulnessChanging=false`
- `mDisplayReady=true`
- `Display Power: state=ON`
- requested/real panel brightness: `143/143`
- touch device enabled and InputDispatcher active
- no `FBIOBLANK failed` or error opening fb0

## Graphics and kernel health

SurfaceFlinger reported:

- total missed frame count: 0
- HWC missed frame count: 0
- GPU missed frame count: 0

No real panic, Oops, hung task, soft lockup or ext4 errors were found. The matches for the word `panic`
belong only to the `errors=panic` mount option.

### Isolated DISPC warning

There was only one `BIT_DISPC0_EB still set` line, at 120.615 s. It was part of a suspend state dump that
also showed `BIT_USB_EB`, `BIT_DISP_EMC_EB` and several active wakelocks (`main`, `usb_work`, `usb_notify`,
`gtex_power_wake`). It did not coincide with a freeze: frames kept arriving after it and the final state
stayed operational. Classification: **monitor**, not a V67 blocker.

## Independent issues found

### 1. EFS and productinfo not mounted -- HIGH

The partitions and their `by-name` links exist:

- `efs` -> `/dev/block/mmcblk0p17`
- `prodnv` -> `/dev/block/mmcblk0p18`

However, `/efs` and `/productinfo` do not exist in the root filesystem and neither partition appears
mounted. The boot logs that fstab could not mount them. There is no evidence they were wiped or damaged;
the observed problem is that the mount directories are missing in the system-as-root image.

This is relevant because `ro.bt.bdaddr_path=/efs/bluetooth/bt_addr` and because EFS/prodnv usually contain
persistent WCN identifiers and calibration. It must be fixed by creating the mount points with appropriate
permissions before trying to complete Bluetooth. Those partitions must not be formatted or altered.

### 2. Bluetooth -- HIGH

`com.android.bluetooth` aborts repeatedly in `bt_hci_thread`. The visible root cause is:

```text
getTransport: Cannot find entry
android.hardware.bluetooth@1.0::IBluetoothHci/default
FATAL hci_layer_android.cc(119): Check failed: btHci != nullptr
```

There is no Bluetooth HAL binary in `/system/vendor/bin/hw`, no corresponding HAL library, and no service
declaration in the device's VINTF manifest. ActivityManager retries the service with backoff and it aborts
again. Bluetooth is not operational and this loop adds noise and consumption. It must be fixed in a separate
bring-up iteration.

Also, the Spreadtrum connectivity daemon does not even link:

```text
CANNOT LINK EXECUTABLE "/system/bin/wcnd": library "libiwnpi.so" not found
```

`wcnd` is not running and `libiwnpi.so` does not exist in system. Although the absence of the HIDL is
Bluetooth's immediate abort, this dependency must also be restored or replaced when preparing the combined
chip's transport.

### 3. Gralloc ION invalidation -- MEDIUM/HIGH for performance

641 messages were counted during the first minutes:

```text
ion_invalidate_for_cpu: dmabuf is error and dmabuf is fffffff7!
```

`fffffff7` is `ERR_PTR(-9)`, i.e. `-EBADF`. The path is:

`gralloc_lock()` -> `ion_invalidate_fd(m->ion_client, hnd->share_fd)` -> `ION_IOC_INVALIDATE` ->
`dma_buf_get(fd)`.

The legacy implementation calls the invalidation for any SW lock without checking that the handle uses ION
and that `share_fd` is valid. The failure does not break the current composition, but it generates spam at
frame rate and can worsen the performance of the already costly CPU `fb_post`. It must be fixed separately
with strict handle/fd validation and a visual-coherence test.

### 4. Wi-Fi SC2331 -- PARTIAL / MEDIUM

The kernel logs `wlan_scan_timeout()` periodically, about every 13.6 seconds in the sample; wificond
confirms several `Scan aborted` and cannot query `NL80211_ATTR_EXT_FEATURES`. However, during the same
audit Wi-Fi was associated at 2.4 GHz, had an IPv4 address, a default route, stable RSSI and Android marked
`validatedInternetAccess`. So the current connection works, but the periodic scan is unreliable and
deserves an independent functional test.

### 5. Legacy audio looking for a modem -- LOW/MEDIUM

The audio HAL logs every two seconds:

```text
vbc_ctl_modem_monitor_routine:socket_local_client failed 111
```

The SM-T280 is Wi-Fi-only and does not offer the modem socket the legacy HAL expects. Audioserver and the
HIDL service stay alive, and the speaker routes exist, so it is not an audio crash; it is an unnecessary
loop that should be disabled to reduce logs and wakeups.

### 6. Memtrack and EGL -- LOW/MEDIUM

- Android cannot load a memtrack module; it affects graphics-memory accounting/diagnosis, not the current
  render.
- The Composer intermittently logs `OpenGL ES API with no current context`. It produced no dropped frames
  in this capture, but it must be watched when measuring sustained graphics performance.

### 7. Other warnings -- LOW

- init warns that it cannot expand `persist.sys.usb.sport` in `init.sc8830.usb.rc`; it did not affect this
  session's ADB.
- There are touch warnings at start, but `mip4_ts` and touchkey resumed and touch worked after the cycles.

## Conclusion

**V67_DISPLAY_POWER_PASS**

The requested function -- turning the screen off and on with POWER, including a fast OFF->ON without a late
power-off and with touch recovery -- is validated. The next priority is to restore the EFS/productinfo
mount and then complete Bluetooth/`wcnd`; the ION invalidation is the graphics priority. After that come the
Wi-Fi scan reliability and the periodic audio noise. None justifies reopening or reverting V67.
