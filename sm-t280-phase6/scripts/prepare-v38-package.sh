#!/usr/bin/env bash
# Phase 5 V38 - boot (V21 fstab+ffs) + system with device VINTF manifest (health@2.0-service, IHealth hang fix).
# The system did NOT change vs V5/V7; the deterministic legacy sparse is regenerated.
set -euo pipefail

root=${1:?Usage: prepare-v8-package.sh ANDROID_ROOT WORKSPACE}
workspace=${2:?Usage: prepare-v8-package.sh ANDROID_ROOT WORKSPACE}
boot="$root/out/target/product/gtexswifi/boot.img"
source_system="$root/out/target/product/gtexswifi/system.img"
converted="$workspace/results/phase-5/system-legacy-sparse-odin-v38.img"
package="$workspace/sm-t280-phase6/packages/SM-T280-android10-health-hal-PHASE6-v38-DO-NOT-FLASH.tar.md5"

# 1) system.img (sparse AOSP) -> sparse legacy (file_hdr_sz=32, chunk_hdr_sz=16).
python3 "$workspace/sm-t280-phase6/scripts/legacy_sparse.py" "$source_system" "$converted"
file "$converted" | grep -F 'version: 1.0, Total of 524288 4096-byte output blocks'
python3 - "$converted" <<'PY'
import struct, sys
with open(sys.argv[1], 'rb') as f:
    h = struct.unpack('<IHHHHIIII', f.read(28))
assert h[3:5] == (32, 16), h
print("legacy_sparse_headers_ok file_hdr_sz=%d chunk_hdr_sz=%d" % (h[3], h[4]))
PY

# 2) Package boot + legacy system into an AP tar.md5.
bash "$workspace/sm-t280-phase6/scripts/package-system-for-odin.sh" "$boot" "$converted" "$package"

# 3) Verify the package content/integrity.
bash "$workspace/sm-t280-phase6/scripts/verify-odin-boot-system-package.sh" "$package"

printf 'boot_sha256=%s\n' "$(sha256sum "$boot" | awk '{print $1}')"
printf 'legacy_system_sha256=%s\n' "$(sha256sum "$converted" | awk '{print $1}')"
printf 'package=%s\n' "$package"
printf 'V38_PACKAGE_PASS\n'
