#!/usr/bin/env python3
# V70 (part 4: BT - UART + wakelock). On top of V69/V70. Changes in init.board.rc (device) and in the
# init.rc of the BT service. Both go in system.img.
#
# FINDING 1 - inaccessible UART (THE BIG BLOCKER):
#   logcat: "bt_userial_vendor: userial vendor open: unable to open /dev/ttyS0"
#           -> hci_layer_android.cc: Check failed: status == Status::SUCCESS -> stack aborta.
#   /dev/ttyS0 stayed at system:system 0660 and the HAL runs as 'bluetooth'.
#   CAUSE: init.board.rc did `chown bluetooth net_bt_stack /dev/ttyS0`, but the AID
#   'net_bt_stack' NO LONGER EXISTS in Android 10 -> init cannot resolve it and the chown FAILS.
#   (Same problem that forced using the numeric GID 3008 for the bdaddr.)
#   FIX: `chown bluetooth bluetooth /dev/ttyS0` (the HAL is the owner -> rw with 0660).
#   VERIFIED ON HW: after the manual chown, the chip RESPONDS:
#     "bt_chip_vendor: Bluetooth Firmware Node: 5150 Date: 2016-12-16"
#     "OnFirmwareConfigured result: 0 / Firmware configured in 0.203s"
#
# FINDING 2 - without the 'wakelock' group:
#   /sys/power/wake_lock is radio:wakelock 0660 and the BT service had Groups: 3008 (without wakelock)
#   -> it cannot take wakelocks during the HCI/LPM startup. After configuring the firmware the
#   stack keeps waiting and BLE_START_TIMEOUT fires. We add 'wakelock' to the service.
#
# Idempotente.
import sys
from pathlib import Path

BOARD_RC = Path("/home/lineage/android/lineage-17.1/device/samsung/gtexswifi/rootdir/init.board.rc")
BT_RC = Path("/home/lineage/android/lineage-17.1/hardware/interfaces/bluetooth/1.0/default/"
             "android.hardware.bluetooth@1.0-service.rc")

def main() -> int:
    changed = 0

    # 1) /dev/ttyS0: grupo valido
    s = BOARD_RC.read_text(encoding="utf-8", errors="surrogateescape")
    OLD = "    chown bluetooth net_bt_stack /dev/ttyS0\n"
    NEW = "    chown bluetooth bluetooth /dev/ttyS0\n"
    if NEW in s:
        print("V70_UART_ALREADY")
    elif OLD in s:
        BOARD_RC.write_text(s.replace(OLD, NEW, 1), encoding="utf-8", errors="surrogateescape")
        print("V70_UART_APPLIED -> chown bluetooth bluetooth /dev/ttyS0")
        changed += 1
    else:
        print("V70_UART_ERROR: cannot find the expected chown of /dev/ttyS0"); return 1

    # 2) BT service: add the wakelock group
    b = BT_RC.read_text(encoding="utf-8", errors="surrogateescape")
    if "group bluetooth 3008 wakelock" in b:
        print("V70_WAKELOCK_ALREADY")
    elif "    group bluetooth 3008\n" in b:
        b = b.replace("    group bluetooth 3008\n", "    group bluetooth 3008 wakelock\n", 1)
        BT_RC.write_text(b, encoding="utf-8", errors="surrogateescape")
        print("V70_WAKELOCK_APPLIED -> group bluetooth 3008 wakelock")
        changed += 1
    else:
        print("V70_WAKELOCK_ERROR: cannot find 'group bluetooth 3008' (apply the bdaddr patch first)")
        return 1

    print(f"V70_BT_UART_WAKELOCK_DONE ({changed} changes)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
