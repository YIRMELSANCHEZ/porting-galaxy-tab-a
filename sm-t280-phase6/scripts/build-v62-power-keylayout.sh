#!/usr/bin/env bash
set -eo pipefail
cd /home/lineage/android/lineage-17.1

export USE_CCACHE=1
export CCACHE_EXEC=/usr/bin/ccache
export CCACHE_DIR=/home/lineage/.ccache
ccache -M 50G >/dev/null 2>&1 || true

printf '=== V62 BUILD START %s ===\n' "$(date -Is)"
source build/envsetup.sh
lunch lineage_gtexswifi-userdebug
m -j8 systemimage

product=out/target/product/gtexswifi
layout="$product/system/usr/keylayout/sci-keypad.kl"
generic="$product/system/usr/keylayout/Generic.kl"

test -f "$layout"
test -f "$generic"
grep -Eq '^key[[:space:]]+116[[:space:]]+POWER[[:space:]]*$' "$layout"
grep -Eq '^key[[:space:]]+172[[:space:]]+HOME[[:space:]]*$' "$layout"
if grep -Eq '(^|[[:space:]])WAKE([[:space:]]|$)' "$layout"; then
    printf '%s\n' 'V62_ERROR: unsupported WAKE flag remains in sci-keypad.kl'
    exit 1
fi
grep -Eq '^key[[:space:]]+116[[:space:]]+POWER[[:space:]]*$' "$generic"

boot_hash=$(sha256sum "$product/boot.img" | awk '{print $1}')
test "$boot_hash" = 4f8649fe853b5fbef7d4eb75aa766e2169775677ba91bb4504f089eae055973f

printf 'boot_sha256=%s\n' "$boot_hash"
printf 'system_img_sha256=%s\n' "$(sha256sum "$product/system.img" | awk '{print $1}')"
printf 'V62_KEYLAYOUT_OFFLINE_VERIFY_PASS\n'

