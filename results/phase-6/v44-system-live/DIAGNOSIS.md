# Phase 6 (WiFi) -- V44: sprdwl driver OK (wlan0 created). Missing HIDL supplicant (V45)

Date: 2026-09-19. Source: V44 flashed.

## V44 CONFIRMED -- the WiFi driver and the interface work

- `init.svc.vendor.wifi_hal_legacy=running`; lshal: IWifi@1.0/1.1/1.2/1.3 REGISTERED (pid 221).
- `sprdwl.ko` installed in /system/lib/modules (vermagic 3.10.108-g95996f39350-dirty = boot.img V35's
  kernel).
- MANUAL insmod of the module (isolating from the framework):
  ```
  [SC2331][wlan_module_init] ... sdio is ready !!!
  [SC2331]wlan_wiphy_new enter ; ieee80211 phy1
  [SC2331][wlan_vif_init][0][wlan0][addr]:72 c2 ed 36 66 66
  [SC2331][wlan_vif_init][1][p2p0]
  [SC2331]wlan_module_init ok!
  ```
  -> wlan0 and p2p0 CREATED, the Marlin sc2331 chip communicates over SDIO, firmware loaded. Driver 100%
  operational.

## Why WiFi does not stay active yet: the framework unloads the driver when the supplicant fails

On a normal boot, dmesg shows the driver loaded at ~10s and then wlan_module_exit (unloaded). Framework
sequence when enabling WiFi: IWifi.start (loads driver, creates iface) -> starts supplicant -> supplicant
FAILS -> teardown (unloads driver). That is why `svc wifi enable` does not leave wlan0 (it unloads ~5s
later). The driver itself is correct (proven by the manual insmod).

Cause of the supplicant failure: the device's init.wifi.rc defines wpa_supplicant in the OLD style
(pre-HIDL): -iwlan0 -c<conf>, without declaring the HIDL interface
android.hardware.wifi.supplicant@1.1::ISupplicant. Android 10 talks over HIDL (ISupplicant) and adds the
interface via addInterface -> it does not connect to the old supplicant. Log: `SupplicantStaIfaceHal:
Starting supplicant using init` -> `WifiNative: Failed to connect to supplicant` -> `wifi driver unloaded`.

## V45 (fix) -- HIDL wpa_supplicant

`apply-v45-wifi-supplicant-hidl.py`: rewrites the wpa_supplicant service in the Android 10 HIDL style (no
-i/-c; -O<sock> -dd -g@android:wpa_wlan0; declares ISupplicant interface 1.0 and 1.1; group system wifi
inet) + VINTF manifest wifi.supplicant@1.1 ISupplicant. Goal: the framework connects to the supplicant,
keeps the driver loaded and can scan/associate to a network. Cumulative over V44; boot = V35.

## Pending after V45
- Verify scan + connection to a real network (it will need /data/vendor/wifi or /data/misc/wifi with
  permissions; see logs if it fails -> V46).
- Power button (wake from sleep) still pending (workaround: it does not turn off with USB).
