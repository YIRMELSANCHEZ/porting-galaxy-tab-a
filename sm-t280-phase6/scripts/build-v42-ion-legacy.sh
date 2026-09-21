#!/usr/bin/env bash
set -eo pipefail
cd /home/lineage/android/lineage-17.1

export USE_CCACHE=1
export CCACHE_EXEC=/usr/bin/ccache
export CCACHE_DIR=/home/lineage/.ccache
ccache -M 50G >/dev/null 2>&1 || true

printf '=== V42 BUILD START %s ===\n' "$(date -Is)"
source build/envsetup.sh
lunch lineage_gtexswifi-userdebug
m -j8 libion_sprd systemimage

nm_tool=prebuilts/clang/host/linux-x86/clang-r353983c/bin/llvm-nm
ion=out/target/product/gtexswifi/system/lib/libion_sprd.so
codec=out/target/product/gtexswifi/system/lib/libcodec2_vndk.so
mediaserver=out/target/product/gtexswifi/system/bin/mediaserver

test -f "$ion"
test -f "$codec"
test -f "$mediaserver"
"$nm_tool" -D "$ion" | grep -E '[[:space:]]T[[:space:]]+ion_is_legacy$'
"$nm_tool" -D "$codec" | grep -E '[[:space:]]U[[:space:]]+ion_is_legacy$'
readelf -d "$codec" | grep -F 'Shared library: [libion.so]'
test "$(readlink out/target/product/gtexswifi/system/lib/libion.so)" = libion_sprd.so

printf 'libion_sprd_sha256=%s\n' "$(sha256sum "$ion" | awk '{print $1}')"
printf 'system_img_sha256=%s\n' "$(sha256sum out/target/product/gtexswifi/system.img | awk '{print $1}')"
printf 'V42_ION_OFFLINE_VERIFY_PASS\n'
