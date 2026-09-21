#!/usr/bin/env bash
# Fase 5.0 — full build of the LineageOS 17.1 ROM for gtexswifi.
# Reproducible: kernel in-tree (rev 95996f39350, = V10 probado) + GCC 4.8 via
# KERNEL_TOOLCHAIN from BoardConfig. Does not interact with the tablet.
set -o pipefail
cd /home/lineage/android/lineage-17.1 || exit 2

export USE_CCACHE=1
export CCACHE_EXEC=/usr/bin/ccache
export CCACHE_DIR=/home/lineage/.ccache
ccache -M 50G >/dev/null 2>&1 || true

echo "=== BUILD START $(date -Is) ==="
git -C kernel/samsung/gtexswifi rev-parse HEAD
source build/envsetup.sh || exit 3
lunch lineage_gtexswifi-userdebug || exit 4

echo "=== mka droid (systemimage + bootimage + recoveryimage) $(date -Is) ==="
mka -j8
rc=$?
echo "=== BUILD_EXIT=$rc $(date -Is) ==="

echo "=== PRODUCT_OUT images ==="
ls -la out/target/product/gtexswifi/*.img 2>/dev/null
exit $rc
