# Phase 6 (WiFi) -- V45: HIDL supplicant in place; the vendor HAL does not load the driver (3.10 caps)

Date: 2026-09-19. Source: V45 flashed (NEW boot f8a355e5 + system V45).

## Packaging note: init.wifi.rc goes in the RAMDISK

`init.wifi.rc` is installed in `root/` (device.mk:62 -> ramdisk), NOT in system.img. That is why V45
required rebuilding boot.img (same kernel #15, ramdisk with the HIDL supplicant) -> boot_sha256 f8a355e529...
Any future change to rootdir/*.rc needs a new boot.img.

## State after V45: the failure moved to the WiFi vendor HAL

The framework no longer gets stuck at the supplicant; now it fails EARLIER, when starting the vendor HAL:
```
android.hardware.wifi@1.0-service: finit_module return: -1: Operation not permitted
android.hardware.wifi@1.0-service: Failed to load WiFi driver
android.hardware.wifi@1.0-service: Wifi HAL start failed
WifiVendorHal: Failed to start vendor HAL
```
Diagnosis:
- SELinux = Permissive -> it is NOT SELinux.
- The running kernel is still the same (#15, boot reused the cached kernel); the MANUAL insmod (root) of the
  .ko STILL works (wlan0/p2p0 created, firmware OK). The driver is perfect.
- finit_module returns EPERM because the wifi@1.0-service runs as `user wifi` with `capabilities ...
  SYS_MODULE`, but kernel 3.10 does NOT have ambient capabilities: on setuid(wifi) CAP_SYS_MODULE is lost.
  It is the SAME problem that broke logd in V22-V24.

## V46 (fix) -- the WiFi vendor HAL runs as root

`apply-v46-wifi-hal-root.py`: in
hardware/interfaces/wifi/1.3/default/android.hardware.wifi@1.0-service.rc changes `user wifi` -> `user
root`. As root there is no setuid, it keeps CAP_SYS_MODULE and finit_module loads the driver. The .rc is
installed in /vendor/etc/init (system.img); boot = V45 (unchanged). Bring-up fix (permissive), reversible.

Expected success: the vendor HAL loads sprdwl -> stable wlan0 under the framework -> the supplicant (V45)
can associate. Verify scan + connection to a network.

## Pending
- After V46: verify stable wlan0, network scan, connection. Possible loose end with /data/vendor/wifi
  (supplicant paths) -> see logs.
- Power button (wake from sleep) pending (workaround: it does not turn off with USB).
