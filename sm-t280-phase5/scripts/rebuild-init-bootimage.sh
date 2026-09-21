#!/usr/bin/env bash
# Rebuilds init (after a change in fs_mgr/system/core) and the boot image.
set -eo pipefail
root=${1:?Usage: rebuild-init-bootimage.sh ANDROID_ROOT}
rm -f "$root/out/target/product/gtexswifi/boot.img" "$root/out/target/product/gtexswifi/ramdisk.img"
cd "$root"
source build/envsetup.sh
lunch lineage_gtexswifi-userdebug
m init
m bootimage
