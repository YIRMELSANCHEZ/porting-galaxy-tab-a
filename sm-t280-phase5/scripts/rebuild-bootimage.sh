#!/usr/bin/env bash
# Rebuild only the boot ramdisk/image after a device configuration change.
set -eo pipefail
root=${1:?Usage: rebuild-bootimage.sh ANDROID_ROOT}
rm -f "$root/out/target/product/gtexswifi/boot.img" "$root/out/target/product/gtexswifi/ramdisk.img"
cd "$root"
source build/envsetup.sh
lunch lineage_gtexswifi-userdebug
m bootimage
