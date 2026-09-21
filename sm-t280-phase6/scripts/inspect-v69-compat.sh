#!/usr/bin/env bash
set -euo pipefail
root=/home/lineage/android/lineage-17.1
cd "$root"
printf '%s\n' '--- device shim configuration ---'
rg -n 'LD_SHIM|shim|androidGetTid|android_atomic_or' device/samsung/gtexswifi vendor/samsung/gtexswifi hardware/sprd 2>/dev/null | head -300 || true
printf '%s\n' '--- current V68 package and manifest fragments ---'
sed -n '/V68 consolidated legacy-HAL bridge/,/# Usb accessory/p' device/samsung/gtexswifi/device.mk
rg -n -A8 -B2 'android.hardware.(camera.provider|gnss)' device/samsung/gtexswifi/manifest.xml
printf '%s\n' '--- undefined symbols in legacy blobs ---'
arm-linux-gnueabihf-readelf -Ws vendor/samsung/gtexswifi/proprietary/lib/hw/gps.default.so 2>/dev/null | grep -E 'UND.*(androidGetTid|android_atomic)' || true
arm-linux-gnueabihf-readelf -Ws vendor/samsung/gtexswifi/proprietary/lib/libmemoryheapion.so 2>/dev/null | grep -E 'UND.*android_atomic' || true
