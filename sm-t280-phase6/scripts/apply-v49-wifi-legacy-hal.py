#!/usr/bin/env python3
# V49 (WiFi bring-up, step 6 - the AOSP vendor HAL does not support this chip): with V48 the
# driver loads and wlan0 exists, but the HAL android.hardware.wifi@1.0-service (AOSP) fails:
#   Failed to initialize legacy hal function table
#   Failed to initialize legacy HAL: NOT_SUPPORTED
#   Wifi HAL start failed
# Cause: BOARD_WLAN_DEVICE = sc2341 (SPRD) is NOT in the list of devices with a vendor
# HAL en frameworks/opt/net/wifi/libwifi_hal/Android.mk (bcmdhd/qcwcn/MediaTek/rtl/slsi/
# emulator) -> libwifi-hal-fallback is linked, whose init_wifi_vendor_hal_func_table()
# returns NOT_SUPPORTED. The Marlin sc2341 chip has no vendor HAL (only standard nl80211).
#
# Fix: use the LineageOS LEGACY HAL android.hardware.wifi@1.0-service.legacy
# (hardware/lineage/interfaces/wifi/1.0-legacy), meant for drivers without a vendor HAL: it uses
# wifi_legacy_hal_stubs.cpp to populate the function table with stubs (not NOT_SUPPORTED)
# and operates via basic nl80211. It registers the same IWifi/service vendor.wifi_hal_legacy.
# Changes:
#   1) device.mk PRODUCT_PACKAGES: android.hardware.wifi@1.0-service ->
#      android.hardware.wifi@1.0-service.legacy.
#   2) its .rc has the SAME kernel-3.10 caps problem (user wifi + capabilities
#      SYS_MODULE -> CapEff=0 -> finit_module EPERM): remove the capabilities line and set
#      user root (as V46/V47 for the AOSP HAL).
# Both rc install in /vendor/etc/init (system.img); on removing the AOSP package its rc does not
# install -> no duplicate of the vendor.wifi_hal_legacy service. boot = V45. Cumulative
# on top of V48. Idempotent.
import sys

ROOT = "/home/lineage/android/lineage-17.1"
DEVMK = ROOT + "/device/samsung/gtexswifi/device.mk"
RC = ROOT + "/hardware/lineage/interfaces/wifi/1.0-legacy/android.hardware.wifi@1.0-service.legacy.rc"

# 1) device.mk: change the HAL package
s = open(DEVMK, encoding="utf-8", errors="surrogateescape").read()
if "android.hardware.wifi@1.0-service.legacy" in s:
    print("V49_DEVMK_ALREADY")
else:
    OLD = "    android.hardware.wifi@1.0-service\n"
    if OLD not in s:
        print("V49_ERROR: no encuentro 'android.hardware.wifi@1.0-service' en device.mk"); sys.exit(1)
    s = s.replace(OLD, "    android.hardware.wifi@1.0-service.legacy\n", 1)
    open(DEVMK, "w", encoding="utf-8", errors="surrogateescape").write(s)
    print("V49_DEVMK_APPLIED -> HAL legacy de LineageOS")

# 2) legacy rc: remove capabilities + user root
r = open(RC, encoding="utf-8", errors="surrogateescape").read()
CAP = "    capabilities NET_ADMIN NET_RAW SYS_MODULE\n"
changed = False
if CAP in r:
    r = r.replace(CAP, "", 1); changed = True
if "    user wifi\n" in r:
    r = r.replace("    user wifi\n", "    user root\n", 1); changed = True
if changed:
    open(RC, "w", encoding="utf-8", errors="surrogateescape").write(r)
    print("V49_RC_APPLIED -> legacy rc: root, without capabilities")
else:
    print("V49_RC_ALREADY")
