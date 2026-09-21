#!/usr/bin/env python3
# V71 (Bluetooth: disable LPM). On top of V70. Changes the AOSP @1.0-impl -> system.img.
#
# CAUSE (chronology verified on HW):
#   OnFirmwareConfigured result: 0  (firmware OK, the chip responds: "Firmware Node: 5150")
#   -> op(BT_VND_OP_LPM_SET_MODE, ENABLE) and watchdog with lpm_timeout_ms = 1500
#   -> at ~1.5s OnTimeout() DE-ASSERTS the wake (BT_VND_LPM_WAKE_DEASSERT) => the chip sleeps
#   -> the BLE startup HCI commands get no response
#   -> at ~3s: "AdapterState: BLE_TURNING_ON : BLE_START_TIMEOUT" -> BT turns off.
#   The wake re-assert that Send() does cannot wake the chip with this SPRD 5.1 blob.
#
# FIX: do not enable LPM and do not arm the watchdog; leave BT_WAKE asserted permanently.
#   - manda BT_VND_LPM_DISABLE en lugar de ENABLE
#   - does not call fd_watcher_.ConfigureTimeout(...) -> OnTimeout() never de-asserts the wake
#   - forces lpm_wake_deasserted=false so Send() does not rearm the watchdog either
# TRADE-OFF: slightly more consumption with BT on (the chip does not enter low-power). Acceptable:
# the goal is for BT to work. Idempotent.
import sys
from pathlib import Path

SRC = Path("/home/lineage/android/lineage-17.1/hardware/interfaces/bluetooth/1.0/default/"
           "vendor_interface.cc")

s = SRC.read_text(encoding="utf-8", errors="surrogateescape")

if "V71: LPM deshabilitado" in s:
    print("V71_ALREADY"); sys.exit(0)

OLD = """  bt_vendor_lpm_mode_t mode = BT_VND_LPM_ENABLE;
  lib_interface_->op(BT_VND_OP_LPM_SET_MODE, &mode);

  ALOGD("%s Calling StartLowPowerWatchdog()", __func__);
  fd_watcher_.ConfigureTimeout(std::chrono::milliseconds(lpm_timeout_ms),
                               [this]() { OnTimeout(); });
"""

NEW = """  /* V71: LPM deshabilitado en gtexswifi (SM-T280). El blob vendor SPRD de Android 5.1 duerme
   * el chip ~1.5s despues de configurar el firmware y el re-assert del wake no lo despierta:
   * los comandos HCI del arranque de BLE se quedan sin respuesta y el stack aborta con
   * BLE_START_TIMEOUT. Mantenemos el BT_WAKE asertado y no armamos el watchdog. */
  bt_vendor_lpm_mode_t mode = BT_VND_LPM_DISABLE;
  lib_interface_->op(BT_VND_OP_LPM_SET_MODE, &mode);
  lpm_wake_deasserted = false;
  ALOGI("%s: V71 LPM disabled; BT_WAKE kept asserted (no watchdog)", __func__);
"""

if OLD not in s:
    print("V71_ERROR: cannot find the LPM block of OnFirmwareConfigured"); sys.exit(1)

s = s.replace(OLD, NEW, 1)
SRC.write_text(s, encoding="utf-8", errors="surrogateescape")
print("V71_APPLIED -> LPM disabled and permanent wake in the BT HAL")
