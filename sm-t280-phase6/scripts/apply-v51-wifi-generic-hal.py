#!/usr/bin/env python3
# V51 (WiFi bring-up, step 8 - generic nl80211 vendor HAL): after V50 the legacy HAL loads the
# driver (wlan0 created) but fails in init_wifi_vendor_hal_func_table -> NOT_SUPPORTED. It was
# confirmed that NO SPRD WiFi vendor HAL exists for Android 10 (BOARD_WLAN_DEVICE=
# sc2341 is not in the vendor HAL list -> libwifi-hal-fallback -> NOT_SUPPORTED;
# hardware/sprd/wlan does not implement the func table; there is no blob; the sibling SM-T285 tree is
# Android 7.1 and the stock is 5.1).
#
# Solution: use the generic HAL libwifi-hal-emu (device/generic/goldfish/wifi/wifi_hal), which
# implements the wifi_hal func table via STANDARD netlink/rtnetlink (real wifi_initialize,
# iface "wlan0"); the advanced functions return NOT_SUPPORTED (tolerated; the scan/
# connection is done by wificond+supplicant over nl80211).
#
# BUILD NOTE: setting BOARD_WLAN_DEVICE := emulator enables core modules of the goldfish device
# that force a system variant of libwifi-hal without the corresponding variant of
# libwifi-hal-emu -> error de build ("libwifi-hal (SHARED android-arm) missing
# libwifi-hal-emu (STATIC android-arm)"). That is why BOARD_WLAN_DEVICE := sc2341 is KEPT and
# the emu is selected directly by adding an sc2341 -> libwifi-hal-emu case in the
# LIB_WIFI_HAL selector of frameworks/opt/net/wifi/libwifi_hal/Android.mk. This way the emu (static
# vendor) is linked only in the vendor variant of libwifi-hal (the HAL service's), without
# dragging in emulator modules. Only system.img; boot = V45. Cumulative over V50.
# Idempotente.
import sys

ROOT = "/home/lineage/android/lineage-17.1"
BC = ROOT + "/device/samsung/gtexswifi/BoardConfig.mk"
MK = ROOT + "/frameworks/opt/net/wifi/libwifi_hal/Android.mk"

# 1) Asegurar BOARD_WLAN_DEVICE = sc2341 (revertir emulator si V51 previo lo puso)
s = open(BC, encoding="utf-8", errors="surrogateescape").read()
if "BOARD_WLAN_DEVICE           := emulator" in s:
    s = s.replace("BOARD_WLAN_DEVICE           := emulator",
                  "BOARD_WLAN_DEVICE           := sc2341", 1)
    open(BC, "w", encoding="utf-8", errors="surrogateescape").write(s)
    print("V51_BC_REVERTED -> BOARD_WLAN_DEVICE = sc2341")
elif "BOARD_WLAN_DEVICE           := sc2341" in s:
    print("V51_BC_OK (sc2341)")
else:
    print("V51_WARN: unexpected BOARD_WLAN_DEVICE (continuing)")

# 2) Add sc2341 -> libwifi-hal-emu case in the LIB_WIFI_HAL selector
m = open(MK, encoding="utf-8", errors="surrogateescape").read()
if "BOARD_WLAN_DEVICE), sc2341" in m:
    print("V51_MK_ALREADY"); sys.exit(0)

OLD = (
    "else ifeq ($(BOARD_WLAN_DEVICE), slsi)\n"
    "  LIB_WIFI_HAL := libwifi-hal-slsi\n"
    "endif\n"
)
NEW = (
    "else ifeq ($(BOARD_WLAN_DEVICE), slsi)\n"
    "  LIB_WIFI_HAL := libwifi-hal-slsi\n"
    "else ifeq ($(BOARD_WLAN_DEVICE), sc2341)\n"
    "  # Spreadtrum sc2331/sc2341 (Marlin): sin vendor HAL propio -> HAL generico nl80211\n"
    "  LIB_WIFI_HAL := libwifi-hal-emu\n"
    "endif\n"
)
if OLD not in m:
    print("V51_ERROR: cannot find the expected slsi/endif selector block")
    sys.exit(1)
m = m.replace(OLD, NEW, 1)
open(MK, "w", encoding="utf-8", errors="surrogateescape").write(m)
print("V51_MK_APPLIED -> sc2341 selecciona libwifi-hal-emu")
