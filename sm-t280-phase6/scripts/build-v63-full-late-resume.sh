#!/usr/bin/env bash
set -euo pipefail

root=${1:?Usage: build-v63-full-late-resume.sh ANDROID_ROOT}
product="$root/out/target/product/gtexswifi"
kernel_src="$root/kernel/samsung/gtexswifi"
kernel_out="$product/obj/KERNEL_OBJ"
cross="$root/prebuilts/gcc/linux-x86/arm/arm-eabi-4.8/bin/arm-eabi-"

grep -Fq 'V63: request the complete legacy late_resume' \
  "$kernel_src/drivers/video/sprdfb/sprdfb_main.c"
grep -Fq 'void request_suspend_state(suspend_state_t state);' \
  "$kernel_src/include/linux/earlysuspend.h"

# Rebuild only the kernel first; the existing validated ramdisk and DT remain inputs.
make -C "$kernel_src" O="$kernel_out" ARCH=arm CROSS_COMPILE="$cross" -j8 Image
cp -f "$kernel_out/arch/arm/boot/Image" "$product/kernel"

# Use the device's existing Samsung mkbootimg/signing rules to rebuild boot.img.
cd "$root"
set +u
source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null
m -j8 bootimage
set -u

grep -aFq 'V63 requesting full late_resume' "$product/kernel"
grep -aFq 'V63 framebuffer off while suspend state is ON' "$product/kernel"
test -s "$product/boot.img"
[[ "$(sha256sum "$product/boot.img" | awk '{print $1}')" != \
   "4f8649fe853b5fbef7d4eb75aa766e2169775677ba91bb4504f089eae055973f" ]]
printf 'kernel_sha256=%s\n' "$(sha256sum "$product/kernel" | awk '{print $1}')"
printf 'boot_sha256=%s\n' "$(sha256sum "$product/boot.img" | awk '{print $1}')"
printf 'V63_BOOT_BUILD_PASS\n'
