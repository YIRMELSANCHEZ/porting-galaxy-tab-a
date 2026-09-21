#!/usr/bin/env python3
# V70 (part 3: BT - ini compatible with libbt-vendor.so). On top of V69/V70.
#
# ROOT CAUSE (verified on HW):
#   After fixing the bdaddr, the BT HAL went on to crash with SIGSEGV in
#   libbt-vendor.so!vnd_load_conf+192 -> strcmp(NULL). Bisection on the device:
#     - ini with ONLY keys the blob recognizes  -> does NOT crash
#     - add ONE unknown key (or a "[SETCTION N]" header) -> CRASHES
#   The blob's parser walks its internal table and overflows on names it does not know.
#   The stock connectivity_configure.ini brings ~80 WiFi/Coex keys + headers that the BT blob
#   does not know -> immediate SEGV on load.
#
# FIX: leave in /system/etc/connectivity_configure.ini ONLY the 32 keys that libbt-vendor.so
# recognizes (stock values intact, without headers or inline comments).
# WiFi SAFETY: verified on HW that with the filtered ini WiFi stays CONNECTED and with
# internet (ping 2/2). The binary /system/bin/download (chip WiFi config) prefers
# /productinfo/connectivity_configure.ini and only falls back to this one; it does not depend on it.
#
# RESULT after the fix (HW): the HAL no longer crashes; the vendor progresses
#   bt_vendor: init -> marlin start up -> BT_VND_OP_POWER_CTRL -> BT_VND_OP_USERIAL_OPEN
#   and WCND starts the coprocessor (BT-OPEN/startcp2).
#   PENDING: the chip's HCI handshake still fails (hci_layer_android.cc: status != SUCCESS).
#
# Saves the stock as .stock. Idempotent.
import sys
from pathlib import Path

VENDOR_INI = Path("/home/lineage/android/lineage-17.1/vendor/samsung/gtexswifi/"
                  "proprietary/etc/connectivity_configure.ini")
BLOB = Path("/home/lineage/android/lineage-17.1/vendor/samsung/gtexswifi/"
            "proprietary/lib/libbt-vendor.so")
STOCK = VENDOR_INI.with_suffix(".ini.stock")

HEADER = ("# connectivity_configure.ini filtrado para libbt-vendor.so (V70).\n"
          "# Solo claves reconocidas por el blob: cualquier otra (WiFi/Coex/[SETCTION])\n"
          "# provoca SEGV en vnd_load_conf. Stock original en connectivity_configure.ini.stock\n")


def known_keys() -> set:
    data = BLOB.read_bytes()
    out, cur = set(), bytearray()
    for b in data:
        if 32 <= b < 127:
            cur.append(b)
        else:
            if len(cur) >= 3:
                out.add(cur.decode("ascii", "ignore"))
            cur = bytearray()
    if len(cur) >= 3:
        out.add(cur.decode("ascii", "ignore"))
    return out


def main() -> int:
    if not VENDOR_INI.exists():
        print("V70_INI_ERROR: no encuentro connectivity_configure.ini"); return 1

    src = STOCK if STOCK.exists() else VENDOR_INI
    text = src.read_text(encoding="utf-8", errors="surrogateescape")

    if not STOCK.exists():
        STOCK.write_text(text, encoding="utf-8", errors="surrogateescape")
        print(f"V70_INI_BACKUP -> {STOCK.name}")

    strings = known_keys()
    kept, dropped = [], 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("["):
            dropped += 1
            continue
        if "=" not in stripped:
            dropped += 1
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in strings:
            value = stripped.split("=", 1)[1]
            value = value.split("#", 1)[0].rstrip()   # quita comentario final
            kept.append(f"{key} ={value}")
        else:
            dropped += 1

    if not kept:
        print("V70_INI_ERROR: no key was kept (something is wrong)"); return 1

    out = HEADER + "\n".join(kept) + "\n"
    if VENDOR_INI.read_text(encoding="utf-8", errors="surrogateescape") == out:
        print("V70_INI_ALREADY"); return 0

    VENDOR_INI.write_text(out, encoding="utf-8", errors="surrogateescape")
    print(f"V70_INI_APPLIED -> {len(kept)} BT keys kept,{dropped} lineas descartadas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
