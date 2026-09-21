#!/usr/bin/env bash
# Create a Samsung/Odin-compatible raw ext4 SYSTEM image from Android sparse.
# Offline only: does not contact the tablet.
set -euo pipefail

root=${1:?Usage: prepare-raw-system-odin-candidate.sh ANDROID_ROOT WORKSPACE}
workspace=${2:?Usage: prepare-raw-system-odin-candidate.sh ANDROID_ROOT WORKSPACE}
product="$root/out/target/product/gtexswifi"
sparse="$product/system.img"
boot="$product/boot.img"
simg2img="$root/out/host/linux-x86/bin/simg2img"
raw="$workspace/results/fase-5/system-raw-odin-v2.img"
package="$workspace/sm-t280-phase5/packages/SM-T280-system-android10-rawext4-PHASE5-v2-DO-NOT-FLASH.tar.md5"

test -x "$simg2img"
test -f "$sparse"
test -f "$boot"

"$simg2img" "$sparse" "$raw"
e2fsck -fn "$raw" >/dev/null

raw_size=$(stat -c %s "$raw")
test "$raw_size" -eq 2147483648

bash "$workspace/sm-t280-phase5/scripts/package-system-for-odin.sh" \
  "$boot" "$raw" "$package"

tar --list --file "$package" | sed '/^$/d' > "$workspace/results/fase-5/RAW-SYSTEM-V2-TAR-CONTENTS.txt"
test "$(cat "$workspace/results/fase-5/RAW-SYSTEM-V2-TAR-CONTENTS.txt")" = $'boot.img\nsystem.img'

printf 'RAW_SYSTEM_ODIN_CANDIDATE_PASS\n'
