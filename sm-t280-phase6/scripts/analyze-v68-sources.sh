#!/usr/bin/env bash
set -euo pipefail

root=${1:-/home/lineage/android/lineage-17.1}

section() { printf '\n===== %s =====\n' "$1"; }

section "ANDROID TREE STATUS"
for repo in device/samsung/gtexswifi hardware/sprd frameworks/base system/core; do
  if [ -d "$root/$repo/.git" ]; then
    printf '\n-- %s --\n' "$repo"
    git -C "$root/$repo" status --short
  fi
done

section "MEMTRACK MODULES"
find "$root/hardware/interfaces/memtrack" -maxdepth 5 -type f \
  \( -name 'Android.bp' -o -name 'service.cpp' -o -name '*.rc' \) -print 2>/dev/null
grep -RIn --include='Android.bp' --include='Android.mk' \
  'android.hardware.memtrack@1.0-service\|memtrack@1.0-impl' \
  "$root/hardware/interfaces" "$root/device" 2>/dev/null | head -80 || true

section "AUDIO MODEM MONITOR"
grep -RIn --include='*.c' --include='*.cpp' --include='*.h' \
  'vbc_ctl_modem_monitor\|modem_monitor\|connect.*modem\|modem.*socket' \
  "$root/hardware/sprd/audio" 2>/dev/null | head -160 || true

section "WIFI SCAN TIMEOUT"
grep -RIn --include='*.c' --include='*.cpp' --include='*.h' \
  'wlan_scan_timeout\|scan_timeout\|Scan aborted' \
  "$root/kernel/samsung/gtexswifi" "$root/hardware/sprd" 2>/dev/null | head -160 || true

section "GRALLOC SELECTION"
grep -RIn --include='Android.mk' --include='BoardConfig*.mk' --include='device.mk' \
  'gralloc.*sc8830\|hardware/sprd/gralloc\|TARGET_BOARD_PLATFORM' \
  "$root/device/samsung/gtexswifi" "$root/hardware/sprd/gralloc" 2>/dev/null | head -160 || true

section "ION INVALIDATE CALLS"
grep -RIn --include='*.cpp' --include='*.c' 'ion_invalidate_fd' \
  "$root/hardware/sprd/gralloc" 2>/dev/null || true

section "DEVICE MAKEFILE"
sed -n '1,280p' "$root/device/samsung/gtexswifi/device.mk"

section "MANIFEST"
cat "$root/device/samsung/gtexswifi/manifest.xml"

section "ROOTDIR INIT AND CONTENT"
grep -RIn 'mkdir /efs\|mkdir /productinfo\|mount_all' \
  "$root/device/samsung/gtexswifi/rootdir" 2>/dev/null || true
find "$root/device/samsung/gtexswifi/rootdir" -maxdepth 2 -type f -printf '%P\n' | sort

section "HWC LOADER"
sed -n '1,220p' \
  "$root/hardware/interfaces/graphics/composer/2.1/utils/passthrough/include/composer-passthrough/2.1/HwcLoader.h"

section "SCREENSHOT SAVE"
sed -n '330,420p' \
  "$root/frameworks/base/packages/SystemUI/src/com/android/systemui/screenshot/GlobalScreenshot.java"

section "HAL SERVICE BLUEPRINTS"
for bp in \
  hardware/interfaces/bluetooth/1.0/default/Android.bp \
  hardware/interfaces/sensors/1.0/default/Android.bp \
  hardware/interfaces/power/1.0/default/Android.bp \
  hardware/interfaces/camera/provider/2.4/default/Android.bp \
  hardware/interfaces/gnss/1.0/default/Android.bp \
  hardware/interfaces/light/2.0/default/Android.bp \
  hardware/interfaces/thermal/1.0/default/Android.bp \
  hardware/interfaces/drm/1.2/default/Android.bp; do
  if [ -f "$root/$bp" ]; then
    printf '\n-- %s --\n' "$bp"
    grep -nE 'name:|init_rc:|vintf_fragments:|relative_install_path:|compile_multilib:' "$root/$bp" || true
  fi
done

section "PROPRIETARY LIBIWNPI"
find "$root/vendor/samsung/gtexswifi" -type f -name 'libiwnpi.so' -o -name 'wcnd' 2>/dev/null
grep -RIn 'libiwnpi.so\|wcnd' "$root/vendor/samsung/gtexswifi" 2>/dev/null | head -100 || true

section "HAL SERVICE REGISTRATION"
for service in \
  hardware/interfaces/bluetooth/1.0/default/service.cpp \
  hardware/interfaces/sensors/1.0/default/service.cpp \
  hardware/interfaces/power/1.0/default/service.cpp \
  hardware/interfaces/camera/provider/2.4/default/service.cpp \
  hardware/interfaces/gnss/1.0/default/service.cpp \
  hardware/interfaces/light/2.0/default/service.cpp \
  hardware/interfaces/thermal/1.0/default/service.cpp \
  hardware/interfaces/memtrack/1.0/default/service.cpp; do
  printf '\n-- %s --\n' "$service"
  sed -n '1,180p' "$root/$service"
done

section "DRM SERVICE MODULES"
find "$root/hardware/interfaces/drm" -type f \
  \( -name Android.bp -o -name '*.rc' -o -name manifest.xml \) -print0 | \
  xargs -0 grep -nHE 'service.clearkey|name:.*service|<name>|<instance>' || true
