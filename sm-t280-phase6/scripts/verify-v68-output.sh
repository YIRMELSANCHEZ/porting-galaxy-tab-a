#!/usr/bin/env bash
set -euo pipefail

root=${1:?Usage: verify-v68-output.sh ANDROID_ROOT}
product="$root/out/target/product/gtexswifi"
failed=0

check_file() {
  if test -s "$product/$1"; then
    printf 'V68_OUTPUT_OK %s\n' "$1"
  else
    printf 'V68_OUTPUT_MISSING %s\n' "$1" >&2
    failed=1
  fi
}

for path in \
  boot.img \
  system.img \
  root/efs/.keep \
  root/productinfo/.keep \
  system/lib/libiwnpi.so \
  system/lib/hw/audio.primary.sc8830.so \
  system/product/priv-app/SystemUI/SystemUI.apk \
  system/vendor/bin/hw/android.hardware.bluetooth@1.0-service \
  system/vendor/bin/hw/android.hardware.sensors@1.0-service \
  system/vendor/bin/hw/android.hardware.power@1.0-service \
  system/vendor/bin/hw/android.hardware.camera.provider@2.4-service \
  system/vendor/bin/hw/android.hardware.gnss@1.0-service \
  system/vendor/bin/hw/android.hardware.light@2.0-service \
  system/vendor/bin/hw/android.hardware.memtrack@1.0-service \
  system/vendor/bin/hw/android.hardware.drm@1.2-service.clearkey \
  system/vendor/lib/hw/android.hardware.bluetooth@1.0-impl.so \
  system/vendor/lib/hw/android.hardware.sensors@1.0-impl.so \
  system/vendor/lib/hw/android.hardware.power@1.0-impl.so \
  system/vendor/lib/hw/android.hardware.camera.provider@2.4-impl.so \
  system/vendor/lib/hw/android.hardware.gnss@1.0-impl.so \
  system/vendor/lib/hw/android.hardware.light@2.0-impl.so \
  system/vendor/lib/hw/android.hardware.memtrack@1.0-impl.so; do
  check_file "$path"
done

grep -aFq 'V67 fb_blank cancelling pending legacy suspend' "$product/kernel" || failed=1
strings -a "$product/system/lib/hw/audio.primary.sc8830.so" | \
  grep -F 'V68: modem monitor disabled on Wi-Fi-only gtexswifi' >/dev/null || failed=1
grep -RaF 'V68: using native Spreadtrum HWC through HWC2On1Adapter' \
  "$product/system/vendor/bin/hw" "$product/system/vendor/lib" \
  "$product/symbols/system/vendor" >/dev/null 2>&1 || failed=1

if test "$failed" -ne 0; then
  printf 'V68_OUTPUT_VERIFY_FAIL\n' >&2
  exit 1
fi

printf 'boot_sha256=%s\n' "$(sha256sum "$product/boot.img" | awk '{print $1}')"
printf 'system_sha256=%s\n' "$(sha256sum "$product/system.img" | awk '{print $1}')"
printf 'V68_OUTPUT_VERIFY_PASS\n'
