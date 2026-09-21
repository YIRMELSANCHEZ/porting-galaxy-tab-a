# Phase 6 (WiFi) -- V47/V48/V49: driver OK; migrate to the LineageOS legacy HAL

Date: 2026-09-19. Chain of layered WiFi-stack fixes.

## V47 -- remove the `capabilities` line from the HAL (real fix for finit_module EPERM)
V46 (user root) was not enough: /proc/<pid>/status of the wifi@1.0-service showed Uid=0 but CapEff=CapBnd=0
(root with ZERO caps). The `capabilities ... SYS_MODULE` line on kernel 3.10 (no ambient) CLEARS the cap
sets. V47 removes it -> CapEff=0x1fffffffff -> the HAL loads the driver: sprdwl in lsmod, wlan0 created,
firmware OK.

## V48 -- insmod() treats EEXIST as success
After V47 the HAL loaded the driver but retried insmod on an already-loaded module -> finit_module EEXIST
("File exists") -> Failed to start vendor HAL. V48 patches insmod() in
frameworks/opt/net/wifi/libwifi_hal/wifi_hal_common.cpp: if errno==EEXIST, ret=0 (the driver is already
operational). Result: the finit_module error disappears.

## V49 -- use the LineageOS legacy HAL (BOARD_WLAN_DEVICE=sc2341 with no vendor HAL in AOSP)
After V48, a new AOSP HAL error:
  Failed to initialize legacy hal function table
  Failed to initialize legacy HAL: NOT_SUPPORTED
  Wifi HAL start failed
Cause: BOARD_WLAN_DEVICE=sc2341 is NOT in the vendor HAL list of
frameworks/opt/net/wifi/libwifi_hal/Android.mk -> it links libwifi-hal-fallback, whose
init_wifi_vendor_hal_func_table() returns NOT_SUPPORTED. The Marlin sc2341 has no vendor HAL (only standard
nl80211).
V49 fix: use android.hardware.wifi@1.0-service.legacy (hardware/lineage/interfaces/wifi/1.0-legacy),
designed for drivers without a vendor HAL (wifi_legacy_hal_stubs.cpp populates the table with stubs,
operates over nl80211). Changes:
  - device.mk PRODUCT_PACKAGES: android.hardware.wifi@1.0-service -> android.hardware.wifi@1.0-service.legacy.
  - its .rc: remove `capabilities`, user root (same 3.10 caps fix).
It registers the same IWifi/vendor.wifi_hal_legacy. boot = V45. system.img only.

Expected success: the vendor HAL starts (function table with stubs), creates the STA interface, the
framework keeps wlan0 and starts the supplicant (V45) -> scan + connection.

## Stack state (context)
sprdwl driver: OK (V44). Supplicant HIDL: in place (V45, boot f8a355e5). HAL caps: OK (V47). insmod EEXIST:
OK (V48). Vendor HAL func table: V49 (legacy). Pending after V49: verify STA iface creation + supplicant +
scan/connection; then the button wake.
