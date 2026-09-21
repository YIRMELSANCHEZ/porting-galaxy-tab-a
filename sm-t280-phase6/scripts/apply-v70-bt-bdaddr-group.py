#!/usr/bin/env python3
# V70 (functional Bluetooth). On top of V69. Change ONLY in the BT service's init.rc -> system.img.
#
# ROOT CAUSE (verified on HW with tombstone_42):
#   Abort message: 'Open: No Bluetooth Address!'  en VendorInterface::Open -> __android_log_assert
#   The HAL android.hardware.bluetooth@1.0-service registers IBluetoothHci but ABORTS in
#   initialize() because it cannot get the Bluetooth MAC.
# EVIDENCIA:
#   - /efs/bluetooth/bt_addr EXISTS and is valid: D0:B1:28:**:**:**
#   - permisos: uid 1001 (radio), gid 3008 (net_bt_stack), modo 0640
#   - the service runs as uid 1002 (bluetooth), gid 1002, WITHOUT supplementary groups
#     -> it cannot read a 0640 file of 1001:3008.
#   - readelf of libbt-vendor.so: NO missing 5.1 symbol -> it is NOT an ABI problem.
#
# FIX: add the net_bt_stack group (3008) to the service so it can read the bdaddr.
# Idempotente.
import sys
from pathlib import Path

SRC = Path("/home/lineage/android/lineage-17.1/hardware/interfaces/bluetooth/1.0/default/"
           "android.hardware.bluetooth@1.0-service.rc")

s = SRC.read_text(encoding="utf-8", errors="surrogateescape")

# NOTE: the NUMERIC GID 3008 is used. The name 'net_bt_stack' NO longer exists in the AID list
# of Android 10 -> host_init_verifier fails with "Unable to decode GID for 'net_bt_stack'".
# init/DecodeUid accepts numeric values, so 3008 is valid and avoids touching the efs partition
# (which contains factory data).
if "group bluetooth 3008" in s:
    print("V70_ALREADY"); sys.exit(0)

OLD = "    group bluetooth\n"
NEW = "    group bluetooth 3008\n"

if OLD not in s:
    print("V70_ERROR: cannot find 'group bluetooth' in the BT service rc"); sys.exit(1)

s = s.replace(OLD, NEW, 1)
SRC.write_text(s, encoding="utf-8", errors="surrogateescape")
print("V70_APPLIED -> net_bt_stack group added (access to /efs/bluetooth/bt_addr)")
