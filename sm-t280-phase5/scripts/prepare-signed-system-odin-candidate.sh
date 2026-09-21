#!/usr/bin/env bash
# Wrap and sign the shrunk raw SYSTEM image for Samsung/Spreadtrum Download Mode.
# Offline only; does not contact the tablet.
set -euo pipefail

root=${1:?Usage: prepare-signed-system-odin-candidate.sh ANDROID_ROOT WORKSPACE}
workspace=${2:?Usage: prepare-signed-system-odin-candidate.sh ANDROID_ROOT WORKSPACE}
device="$root/device/samsung/gtexswifi"
boot="$root/out/target/product/gtexswifi/boot.img"
source_system="$workspace/results/fase-5/system-raw-shrunk-odin-v3.img"
output_system="$workspace/results/fase-5/system-signed-odin-v4.img"
package="$workspace/sm-t280-phase5/packages/SM-T280-system-android10-signed-ext4-PHASE5-v4-DO-NOT-FLASH.tar.md5"
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT

test -f "$boot"
test -f "$source_system"
cp "$source_system" "$work/system.img"

"$device/insertheader/prebuilt/bin/imgheaderinsert" "$work/system.img" 1
mv "$work/system-sign.img" "$work/system.img"
"$device/signimage/prebuilt/bin/sprd_sign" "$work/system.img" "$device/signimage/config"

test "$(dd if="$work/system.img" bs=1 count=4 status=none)" = DHTB
signed_size=$(stat -c %s "$work/system.img")
test "$signed_size" -lt 2147483648
cp "$work/system.img" "$output_system"

bash "$workspace/sm-t280-phase5/scripts/package-system-for-odin.sh" \
  "$boot" "$output_system" "$package"
tar --list --file "$package" | sed '/^$/d' > "$workspace/results/fase-5/SIGNED-SYSTEM-V4-TAR-CONTENTS.txt"
test "$(cat "$workspace/results/fase-5/SIGNED-SYSTEM-V4-TAR-CONTENTS.txt")" = $'boot.img\nsystem.img'

printf 'signed_system_size=%s system_margin=%s\n' "$signed_size" "$((2147483648 - signed_size))"
printf 'signed_system_sha256=%s\n' "$(sha256sum "$output_system" | awk '{print $1}')"
printf 'SIGNED_SYSTEM_ODIN_CANDIDATE_PASS\n'
