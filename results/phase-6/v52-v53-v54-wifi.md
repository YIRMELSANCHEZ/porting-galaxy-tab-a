# Phase 6 (WiFi) -- V52/V53/V54: supplicant + internet. WiFi WORKING

Date: 2026-09-19.

## V52 -- wpa_supplicant binary path
V51 got the generic vendor HAL to start ("WifiVendorHal: Vendor Hal started successfully"). The framework
started the supplicant via HIDL but init could not find it: the service (V45) pointed to
/system/bin/wpa_supplicant and the binary is in /vendor/bin/hw/wpa_supplicant (Android 10). V52 fixes the
path in init.wifi.rc. Ramdisk -> NEW boot 21dcc288.

## V53 -- supplicant data directory
V52 got wpa_supplicant to start, but it failed to create its config: "Failed to write to
/data/vendor/wifi/wpa/wpa_supplicant.conf: No such file or directory" -> "Failed to create
ISupplicantIface". The dir /data/vendor/wifi/wpa did not exist. V53 creates it (+sockets) in on
post-fs-data of init.wifi.rc. Ramdisk -> NEW boot dd2d8154. RESULT: WiFi ASSOCIATES, scans and shows
networks, DHCP gets an IP (192.168.1.175/24).

## V54 -- "connected without internet": ONLINK in netd (kernel 3.10)

Symptom: connected to the network but "no internet". Diagnosis:
- DHCP OK: IP 192.168.1.175/24; the lease brings the default 0.0.0.0/0 -> 192.168.1.1.
- ConnectivityService: "Exception in addRoute for gateway: Network is unreachable (code 101)" -> the
  default route is NOT installed -> DNS (100.100.1.1, out of subnet, DIGI CGNAT) unreachable -> ENONET ->
  no internet.
- The gateway 192.168.1.1 DOES respond to ping; the subnet route is in table wlan0.
- CONFIRMED on the device: `ip route add default via 192.168.1.1 dev wlan0 table wlan0` -> "Network is
  unreachable"; with ONLINK -> OK and ping 8.8.8.8 + DNS WORK.
Root cause: kernel 3.10 rejects the default gatewayed route because the gateway reachability validation
fails even though it is on-link; the RTNH_F_ONLINK flag skips it. netd does not use ONLINK.
V54 fix: patch system/netd/server/RouteController.cpp modifyIpRoute() -> rtm_flags = RTNH_F_ONLINK when
there is a nexthop. Safe on this device (1 iface, gateway in the local subnet). netd goes in system.img;
boot = V53 (dd2d8154).

Expected success: the default route installs itself -> internet + DNS work on connect.

## 5GHz note
The SM-T280's sc2331/Marlin chip is 2.4GHz ONLY (802.11 b/g/n). There is no 5GHz in hardware; connect to
the 2.4GHz SSID. It is not a bug.

## State
WiFi: scan + association + DHCP OK (V53); internet via ONLINK (V54). Pending after V54: confirm stable
internet; then get the app's APK (now with internet) and install it. Separate pending: power-button wake
from sleep.
