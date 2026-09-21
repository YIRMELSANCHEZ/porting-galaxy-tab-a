# Phase 6 (WiFi) -- V50/V51: the .ko path + generic vendor HAL (no SPRD Android 10 HAL exists)

Date: 2026-09-19.

## V50 -- WIFI_DRIVER_MODULE_PATH to /system/lib/modules
V49 (legacy HAL) initialized but: "Failed to open /lib/modules/sprdwl.ko: No such file". On this device
/lib does NOT exist; the .ko is in /system/lib/modules. V50 fixes WIFI_DRIVER_MODULE_PATH :=
"/system/lib/modules/sprdwl.ko". Result: the HAL now loads the driver itself (sprdwl in lsmod, wlan0
created by the HAL, not manually).

## V51 -- generic vendor HAL libwifi-hal-emu (BOARD_WLAN_DEVICE=emulator)

After V50, the legacy HAL fails again in init_wifi_vendor_hal_func_table -> NOT_SUPPORTED. INVESTIGATION
(user decision: "look for the SPRD HAL from another ROM"): it was confirmed that NO accessible SPRD WiFi
vendor HAL exists for Android 10:
- BOARD_WLAN_DEVICE=sc2341 is not in the libwifi_hal/Android.mk vendor HAL list -> libwifi-hal-fallback ->
  NOT_SUPPORTED. There is only qcom/broadcom/goldfish(emu)/fallback.
- hardware/sprd/wlan/ only has supplicant config + libsprd_wifi_priv (does NOT implement
  init_wifi_vendor_hal_func_table). There is no libwifi-hal-sprd blob in vendor/ or device/.
- The sibling tree Fabio-San device_samsung_gtexswifi (SM-T285) = LineageOS 14.1 (Android 7.1, pre-HIDL).
  T280 stock = Android 5.1. -> There is no SPRD Android 10 WiFi HAL to port.

SOLUTION: use the generic HAL libwifi-hal-emu (device/generic/goldfish/wifi/wifi_hal). It is NOT
emulator-specific: it implements the wifi_hal func table via STANDARD netlink/rtnetlink (RTM_GETLINK, real
wifi_initialize) and assumes the "wlan0" iface (matches sprdwl). The advanced functions return
NOT_SUPPORTED (tolerated); the real scan/connection are done by wificond+supplicant over nl80211. It is the
HAL used by generic AOSP targets for standard wlan interfaces. It is selected with BOARD_WLAN_DEVICE :=
emulator -> LIB_WIFI_HAL := libwifi-hal-emu. It does not affect the driver (V50) or the supplicant
(lib_driver_cmd_sprdwl). system.img only; boot = V45.

Expected success: init_wifi_vendor_hal_func_table = SUCCESS (emu funcs), wifi_initialize OK, the HAL
creates/manages the STA iface, the framework keeps wlan0 and starts the supplicant (V45) -> network scan +
connection.

## WiFi stack state (recap)
sprdwl driver (V44) | HIDL supplicant (V45, boot f8a355e5) | HAL caps root (V47) | insmod EEXIST=ok (V48) |
LineageOS legacy HAL (V49) | .ko path (V50) | generic emu vendor HAL (V51). Pending after V51: verify STA
iface + supplicant + scan/connection; then the power-button wake.
