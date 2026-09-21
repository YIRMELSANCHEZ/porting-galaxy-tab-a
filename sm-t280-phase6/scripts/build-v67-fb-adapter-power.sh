#!/usr/bin/env bash
set -euo pipefail

root=${1:?Usage: build-v67-fb-adapter-power.sh ANDROID_ROOT}
product="$root/out/target/product/gtexswifi"
kernel_src="$root/kernel/samsung/gtexswifi"
kernel_out="$product/obj/KERNEL_OBJ"
cross="$root/prebuilts/gcc/linux-x86/arm/arm-eabi-4.8/bin/arm-eabi-"
adapter_src="$root/hardware/interfaces/graphics/composer/2.1/utils/hwc2onfbadapter/HWC2OnFbAdapter.cpp"

grep -Fq 'V67 HWC2 fb power mode' "$adapter_src"
grep -Fq 'V67 fb_blank cancelling pending legacy suspend' \
  "$kernel_src/drivers/video/sprdfb/sprdfb_main.c"
grep -Fq 'V66 HWC power-mode request' \
  "$kernel_src/drivers/video/sprdfb/sprdfb_main.c"

make -C "$kernel_src" O="$kernel_out" ARCH=arm CROSS_COMPILE="$cross" -j8 Image
cp -f "$kernel_out/arch/arm/boot/Image" "$product/kernel"

cd "$root"
export USE_CCACHE=1
export CCACHE_EXEC=/usr/bin/ccache
export CCACHE_DIR=/home/lineage/.ccache
ccache -M 50G >/dev/null 2>&1 || true
set +u
source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null
m -j8 bootimage
m -j8 libhwc2onfbadapter
m -j8 snod
set -u

adapter="$product/system/vendor/lib/libhwc2onfbadapter.so"
grep -aFq 'V67 fb_blank cancelling pending legacy suspend' "$product/kernel"
strings -a "$adapter" | grep -F 'V67 HWC2 fb power mode'
grep -aFq 'V67 HWC2 fb power mode' "$product/system.img"
grep -aFq 'V64: userspace suspend counter enabled' "$product/system.img"
test -s "$product/boot.img"

printf 'kernel_sha256=%s\n' "$(sha256sum "$product/kernel" | awk '{print $1}')"
printf 'boot_sha256=%s\n' "$(sha256sum "$product/boot.img" | awk '{print $1}')"
printf 'adapter_sha256=%s\n' "$(sha256sum "$adapter" | awk '{print $1}')"
printf 'system_sha256=%s\n' "$(sha256sum "$product/system.img" | awk '{print $1}')"
printf 'V67_BOOT_SYSTEM_BUILD_PASS\n'
