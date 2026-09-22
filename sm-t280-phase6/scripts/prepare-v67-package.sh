#!/usr/bin/env bash
set -euo pipefail

root=${1:?Usage: prepare-v67-package.sh ANDROID_ROOT WORKSPACE}
workspace=${2:?Usage: prepare-v67-package.sh ANDROID_ROOT WORKSPACE}
product="$root/out/target/product/gtexswifi"
boot="$product/boot.img"
source_system="$product/system.img"
adapter="$product/system/vendor/lib/libhwc2onfbadapter.so"
converted="$workspace/results/phase-6/system-legacy-sparse-odin-v67.img"
package="$workspace/sm-t280-phase6/packages/SM-T280-android10-fb-adapter-power-PHASE6-v67-DO-NOT-FLASH.tar.md5"

grep -aFq 'V67 fb_blank cancelling pending legacy suspend' "$product/kernel"
strings -a "$adapter" | grep -F 'V67 HWC2 fb power mode'
grep -aFq 'V67 HWC2 fb power mode' "$source_system"
grep -aFq 'V64: userspace suspend counter enabled' "$source_system"

python3 "$workspace/sm-t280-phase6/scripts/legacy_sparse.py" "$source_system" "$converted"
file "$converted" | grep -F 'version: 1.0, Total of 524288 4096-byte output blocks'

bash "$workspace/sm-t280-phase6/scripts/package-system-for-odin.sh" "$boot" "$converted" "$package"
bash "$workspace/sm-t280-phase6/scripts/verify-odin-boot-system-package.sh" "$package"

printf 'boot_sha256=%s\n' "$(sha256sum "$boot" | awk '{print $1}')"
printf 'adapter_sha256=%s\n' "$(sha256sum "$adapter" | awk '{print $1}')"
printf 'legacy_system_sha256=%s\n' "$(sha256sum "$converted" | awk '{print $1}')"
printf 'package_sha256=%s\n' "$(sha256sum "$package" | awk '{print $1}')"
printf 'package=%s\n' "$package"
printf 'V67_PACKAGE_PASS\n'
