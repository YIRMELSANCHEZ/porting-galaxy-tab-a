#!/usr/bin/env bash
# Produce a raw ext4 SYSTEM image smaller than the exact 2 GiB PIT limit.
# Offline only; source sparse image is never modified.
set -euo pipefail

root=${1:?Usage: prepare-shrunk-raw-system-odin-candidate.sh ANDROID_ROOT WORKSPACE}
workspace=${2:?Usage: prepare-shrunk-raw-system-odin-candidate.sh ANDROID_ROOT WORKSPACE}
product="$root/out/target/product/gtexswifi"
simg2img="$root/out/host/linux-x86/bin/simg2img"
sparse="$product/system.img"
boot="$product/boot.img"
raw="$workspace/results/fase-5/system-raw-shrunk-odin-v3.img"
package="$workspace/sm-t280-phase5/packages/SM-T280-system-android10-shrunk-ext4-PHASE5-v3-DO-NOT-FLASH.tar.md5"

test -x "$simg2img"
"$simg2img" "$sparse" "$raw"
e2fsck -fy "$raw" >/dev/null
resize2fs -M "$raw" >/dev/null
e2fsck -fn "$raw" >/dev/null

raw_size=$(stat -c %s "$raw")
test "$raw_size" -lt 2147483648
test "$raw_size" -gt 0

bash "$workspace/sm-t280-phase5/scripts/package-system-for-odin.sh" \
  "$boot" "$raw" "$package"
tar --list --file "$package" | sed '/^$/d' > "$workspace/results/fase-5/SHRUNK-SYSTEM-V3-TAR-CONTENTS.txt"
test "$(cat "$workspace/results/fase-5/SHRUNK-SYSTEM-V3-TAR-CONTENTS.txt")" = $'boot.img\nsystem.img'

printf 'system_raw_size=%s system_margin=%s\n' "$raw_size" "$((2147483648 - raw_size))"
printf 'SHRUNK_RAW_SYSTEM_ODIN_CANDIDATE_PASS\n'
