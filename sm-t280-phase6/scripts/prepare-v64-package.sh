#!/usr/bin/env bash
set -euo pipefail

root=${1:?Usage: prepare-v64-package.sh ANDROID_ROOT WORKSPACE}
workspace=${2:?Usage: prepare-v64-package.sh ANDROID_ROOT WORKSPACE}
boot="$root/out/target/product/gtexswifi/boot.img"
source_system="$root/out/target/product/gtexswifi/system.img"
converted="$workspace/results/fase-6/system-legacy-sparse-odin-v64.img"
package="$workspace/sm-t280-phase6/packages/SM-T280-android10-suspend-counter-PHASE6-v64-DO-NOT-FLASH.tar.md5"
service="$root/out/target/product/gtexswifi/system/bin/hw/android.system.suspend@1.0-service"

[[ "$(sha256sum "$boot" | awk '{print $1}')" == "e4641a1672e610aab448bb666678b43981116f271b2c373b9042ab14534fbf38" ]]
strings -a "$service" | grep -F 'V64: userspace suspend counter enabled'
grep -aFq '# Android 10 accepts only VIRTUAL/FUNCTION/GESTURE key-layout flags.' "$source_system"
grep -aFq 'V64: userspace suspend counter enabled' "$source_system"
if grep -aFq 'key 116   POWER          WAKE' "$source_system"; then
  echo 'V64_ERROR: obsolete WAKE flag returned to sci-keypad.kl' >&2
  exit 1
fi
python3 "$workspace/sm-t280-phase6/scripts/legacy_sparse.py" "$source_system" "$converted"
file "$converted" | grep -F 'version: 1.0, Total of 524288 4096-byte output blocks'
python3 - "$converted" <<'PY'
import struct, sys
with open(sys.argv[1], 'rb') as stream:
    header = struct.unpack('<IHHHHIIII', stream.read(28))
assert header[3:5] == (32, 16), header
print("legacy_sparse_headers_ok file_hdr_sz=%d chunk_hdr_sz=%d" % (header[3], header[4]))
PY

bash "$workspace/sm-t280-phase6/scripts/package-system-for-odin.sh" "$boot" "$converted" "$package"
bash "$workspace/sm-t280-phase6/scripts/verify-odin-boot-system-package.sh" "$package"

printf 'boot_sha256=%s\n' "$(sha256sum "$boot" | awk '{print $1}')"
printf 'service_sha256=%s\n' "$(sha256sum "$service" | awk '{print $1}')"
printf 'legacy_system_sha256=%s\n' "$(sha256sum "$converted" | awk '{print $1}')"
printf 'package_sha256=%s\n' "$(sha256sum "$package" | awk '{print $1}')"
printf 'package=%s\n' "$package"
printf 'V64_PACKAGE_PASS\n'
