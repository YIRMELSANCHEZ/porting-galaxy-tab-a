#!/usr/bin/env bash
set -euo pipefail

root=${1:?Usage: build-v68-consolidated.sh ANDROID_ROOT WORKSPACE}
workspace=${2:?Usage: build-v68-consolidated.sh ANDROID_ROOT WORKSPACE}
product="$root/out/target/product/gtexswifi"

# Patches are applied explicitly before entering this build script. Keeping
# mutation out of the build step prevents needless makefile timestamp churn.
bash "$workspace/sm-t280-phase6/scripts/verify-v68-static.sh" "$root"

# Preserve the proven V67 kernel/power path. V68 changes ramdisk + userspace.
grep -aFq 'V67 fb_blank cancelling pending legacy suspend' "$product/kernel"
grep -aFq 'V66 HWC power-mode request' "$product/kernel"

cd "$root"
export USE_CCACHE=1
export CCACHE_EXEC=/usr/bin/ccache
export CCACHE_DIR=/home/lineage/.ccache
ccache -M 50G >/dev/null 2>&1 || true
set +u
source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null

# One cumulative build. No Odin archive is created here.
# Build only the affected modules, then repack the already complete product.
# Calling systemimage directly on this old tree unnecessarily rebuilds ~51k
# unrelated goals.
m -j8 \
  bootimage \
  file_contexts.bin \
  device_manifest.xml \
  SystemUI \
  audio.primary.sc8830 \
  gralloc.sc8830 \
  android.hardware.graphics.composer@2.1-service \
  android.hardware.graphics.composer@2.1-impl \
  android.hardware.bluetooth@1.0-service \
  android.hardware.bluetooth@1.0-impl \
  android.hardware.sensors@1.0-service \
  android.hardware.sensors@1.0-impl \
  android.hardware.power@1.0-service \
  android.hardware.power@1.0-impl \
  android.hardware.camera.provider@2.4-service \
  android.hardware.camera.provider@2.4-impl \
  android.hardware.gnss@1.0-service \
  android.hardware.gnss@1.0-impl \
  android.hardware.light@2.0-service \
  android.hardware.light@2.0-impl \
  android.hardware.memtrack@1.0-service \
  android.hardware.memtrack@1.0-impl \
  android.hardware.drm@1.2-service.clearkey
m -j8 snod
set -u

bash "$workspace/sm-t280-phase6/scripts/verify-v68-output.sh" "$root"
printf 'V68_CONSOLIDATED_BUILD_PASS\n'
