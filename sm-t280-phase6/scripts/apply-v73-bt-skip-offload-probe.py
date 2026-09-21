#!/usr/bin/env python3
# V73 (Bluetooth: do not probe "BLE offload features" 0xFD53 on the SPRD chip). On top of V72.
# Cambia system/bt (libbluetooth.so -> system.img) y device.mk (propiedad en build.prop).
#
# CAUSE (verified with btsnoop on HW, V72):
#   With wcnd now with caps (V72) the HCI startup is SANE: Reset, Read Local Version, Read BD_ADDR
#   (e2:07:c9:**:**:**), Local Features, Ext Features p1, Write Simple Pairing, Write LE Host
#   Support... all with Command Complete OK. The LAST command sent is 0xFD53
#   (HCI_BLE_VENDOR_CAP_OCF, "BLE vendor capabilities", VSC of Broadcom/Qualcomm) and the SPRD chip
#   responds with COMMAND STATUS 0x01 (Unknown HCI Command) instead of Command Complete:
#       TX 01 53 fd 00           RX 04 0f 04 01 01 53 fd
#   It is sent by system/bt/device/src/controller.cc (a LineageOS addition, "read BLE offload features
#   support") with AWAIT_COMMAND (a future that only resolves with Command Complete). hci_layer ignores the
#   Command Status for commands with a future -> the future never resolves -> controller_module does not
#   start -> "BLE_TURNING_ON : BLE_START_TIMEOUT" at 4s. (The AOSP send of the same VSC via
#   BTM_VendorSpecificCommand DOES handle the Command Status; only this extra probe fails.)
#
# FIX: skip the probe when ro.bluetooth.skip_offload_probe=1 (ble_offload_features_supported
#      stays false, as on a chip that answers "not supported"). Property in device.mk.
# Idempotente.
import sys
from pathlib import Path

T = Path("/home/lineage/android/lineage-17.1")
CTRL = T / "system/bt/device/src/controller.cc"
DEVMK = T / "device/samsung/gtexswifi/device.mk"

OLD_INC = '#include "osi/include/future.h"\n'
NEW_INC = '#include "osi/include/future.h"\n#include "osi/include/properties.h"\n'

OLD = """  // read BLE offload features support from controller
  response = AWAIT_COMMAND(packet_factory->make_ble_read_offload_features_support());
  packet_parser->parse_ble_read_offload_features_response(response, &ble_offload_features_supported);
"""
NEW = """  // read BLE offload features support from controller
  // V73 (gtexswifi/SPRD): el chip contesta a 0xFD53 con Command Status "Unknown HCI Command"
  // (no Command Complete) y el future no resuelve nunca -> BLE_START_TIMEOUT. Saltable por prop.
  if (osi_property_get_bool("ro.bluetooth.skip_offload_probe", false)) {
    LOG(INFO) << __func__ << ": V73 skipping BLE offload features probe (0xFD53)";
    ble_offload_features_supported = false;
  } else {
    response = AWAIT_COMMAND(packet_factory->make_ble_read_offload_features_support());
    packet_parser->parse_ble_read_offload_features_response(response, &ble_offload_features_supported);
  }
"""

PROP_OLD = """PRODUCT_PROPERTY_OVERRIDES += \\
    ro.surface_flinger.primary_display_orientation=ORIENTATION_180
"""
PROP_NEW = PROP_OLD + """
# V73: el chip BT SPRD (Marlin sc2331) no soporta el VSC 0xFD53 (BLE offload/vendor caps) y
# contesta con Command Status -> el stack se colgaba en BLE_START_TIMEOUT. Ver controller.cc.
PRODUCT_PROPERTY_OVERRIDES += \\
    ro.bluetooth.skip_offload_probe=1
"""

changed = 0
s = CTRL.read_text(encoding="utf-8", errors="surrogateescape")
if "V73 skipping BLE offload" in s:
    print("V73_CTRL_ALREADY")
else:
    if OLD not in s or OLD_INC not in s:
        print("V73_ERROR: unexpected controller.cc"); sys.exit(1)
    s = s.replace(OLD_INC, NEW_INC, 1).replace(OLD, NEW, 1)
    CTRL.write_text(s, encoding="utf-8", errors="surrogateescape")
    print("V73_CTRL_APPLIED"); changed += 1

d = DEVMK.read_text(encoding="utf-8", errors="surrogateescape")
if "ro.bluetooth.skip_offload_probe=1" in d:
    print("V73_PROP_ALREADY")
else:
    if PROP_OLD not in d:
        print("V73_ERROR: V43 property block not found in device.mk"); sys.exit(1)
    DEVMK.write_text(d.replace(PROP_OLD, PROP_NEW, 1), encoding="utf-8", errors="surrogateescape")
    print("V73_PROP_APPLIED"); changed += 1

print(f"V73_DONE ({changed} changes)")
