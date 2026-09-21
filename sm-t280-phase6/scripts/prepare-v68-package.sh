#!/usr/bin/env bash
set -euo pipefail

root=${1:?Usage: prepare-v68-package.sh ANDROID_ROOT WORKSPACE}
workspace=${2:?Usage: prepare-v68-package.sh ANDROID_ROOT WORKSPACE}
product="$root/out/target/product/gtexswifi"
boot="$product/boot.img"
source_system="$product/system.img"
converted="$workspace/results/fase-6/system-legacy-sparse-odin-v68.img"
package="$workspace/sm-t280-phase6/packages/SM-T280-android10-consolidated-PHASE6-v68-DO-NOT-FLASH.tar.md5"

# Refuse packaging unless every consolidated build output is present.
bash "$workspace/sm-t280-phase6/scripts/verify-v68-static.sh" "$root"
bash "$workspace/sm-t280-phase6/scripts/verify-v68-output.sh" "$root"
bash "$workspace/sm-t280-phase6/scripts/verify-v68-vintf.sh" "$root"
test -s "$boot"
test -s "$source_system"
test -s "$product/root/efs/.keep"
test -s "$product/root/productinfo/.keep"
test -s "$product/system/lib/libiwnpi.so"
for binary in \
  android.hardware.bluetooth@1.0-service \
  android.hardware.sensors@1.0-service \
  android.hardware.power@1.0-service \
  android.hardware.camera.provider@2.4-service \
  android.hardware.gnss@1.0-service \
  android.hardware.light@2.0-service \
  android.hardware.memtrack@1.0-service \
  android.hardware.drm@1.2-service.clearkey; do
  test -s "$product/system/vendor/bin/hw/$binary"
done

python3 "$workspace/sm-t280-phase6/scripts/legacy_sparse.py" "$source_system" "$converted"
file "$converted" | grep -F 'version: 1.0, Total of 524288 4096-byte output blocks'

bash "$workspace/sm-t280-phase6/scripts/package-system-for-odin.sh" \
  "$boot" "$converted" "$package"
bash "$workspace/sm-t280-phase6/scripts/verify-odin-boot-system-package.sh" "$package"

printf 'boot_sha256=%s\n' "$(sha256sum "$boot" | awk '{print $1}')"
printf 'source_system_sha256=%s\n' "$(sha256sum "$source_system" | awk '{print $1}')"
printf 'legacy_system_sha256=%s\n' "$(sha256sum "$converted" | awk '{print $1}')"
printf 'package_sha256=%s\n' "$(sha256sum "$package" | awk '{print $1}')"
printf 'package=%s\n' "$package"
printf 'V68_CONSOLIDATED_PACKAGE_PASS\n'
