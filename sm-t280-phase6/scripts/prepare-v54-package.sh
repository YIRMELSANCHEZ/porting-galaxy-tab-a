#!/usr/bin/env bash
set -euo pipefail

root=${1:?Usage: prepare-v42-package.sh ANDROID_ROOT WORKSPACE}
workspace=${2:?Usage: prepare-v42-package.sh ANDROID_ROOT WORKSPACE}
boot="$root/out/target/product/gtexswifi/boot.img"
source_system="$root/out/target/product/gtexswifi/system.img"
converted="$workspace/results/phase-5/system-legacy-sparse-odin-v54.img"
package="$workspace/sm-t280-phase6/packages/SM-T280-android10-wifi-onlink-PHASE6-v54-DO-NOT-FLASH.tar.md5"

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
printf 'legacy_system_sha256=%s\n' "$(sha256sum "$converted" | awk '{print $1}')"
printf 'package_sha256=%s\n' "$(sha256sum "$package" | awk '{print $1}')"
printf 'package=%s\n' "$package"
printf 'V54_PACKAGE_PASS\n'
