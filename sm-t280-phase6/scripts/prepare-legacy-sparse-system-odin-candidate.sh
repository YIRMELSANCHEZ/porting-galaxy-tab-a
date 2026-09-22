#!/usr/bin/env bash
# Offline-only: use stock AQJ1's legacy padded Android sparse structure.
set -euo pipefail

root=${1:?Usage: prepare-legacy-sparse-system-odin-candidate.sh ANDROID_ROOT WORKSPACE}
workspace=${2:?Usage: prepare-legacy-sparse-system-odin-candidate.sh ANDROID_ROOT WORKSPACE}
source_system="$root/out/target/product/gtexswifi/system.img"
boot="$root/out/target/product/gtexswifi/boot.img"
converted="$workspace/results/phase-5/system-legacy-sparse-odin-v5.img"
package="$workspace/sm-t280-phase5/packages/SM-T280-system-android10-legacy-sparse-PHASE5-v5-DO-NOT-FLASH.tar.md5"

python3 "$workspace/sm-t280-phase5/scripts/legacy_sparse.py" "$source_system" "$converted"
file "$converted" | grep -F 'version: 1.0, Total of 524288 4096-byte output blocks'
python3 - "$converted" <<'PY'
import struct, sys
with open(sys.argv[1], 'rb') as f:
    h = struct.unpack('<IHHHHIIII', f.read(28))
assert h[3:5] == (32, 16), h
PY
bash "$workspace/sm-t280-phase5/scripts/package-system-for-odin.sh" "$boot" "$converted" "$package"
tar --list --file "$package" | sed '/^$/d' > "$workspace/results/phase-5/LEGACY-SPARSE-SYSTEM-V5-TAR-CONTENTS.txt"
test "$(cat "$workspace/results/phase-5/LEGACY-SPARSE-SYSTEM-V5-TAR-CONTENTS.txt")" = $'boot.img\nsystem.img'
printf 'legacy_system_sha256=%s\n' "$(sha256sum "$converted" | awk '{print $1}')"
printf 'LEGACY_SPARSE_SYSTEM_ODIN_CANDIDATE_PASS\n'
