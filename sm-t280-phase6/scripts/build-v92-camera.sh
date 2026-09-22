#!/bin/bash
# V92: V91 + CAM1 (camera.provider@2.4 legacy + impl + libcamera_shim + rc override with LD_SHIM_LIBS +
# VINTF) + V92b (linker tolerates TEXTREL in vendor HAL services, due to libynoise.so). SEPARATE package
# from V91 for risk: if the camera provider caused problems, V91 remains the safe candidate.
# Run in WSL (lineage) AFTER build-v91 (accumulates its patches).
set -eo pipefail
T=/home/lineage/android/lineage-17.1
WIN=/mnt/c/Dev/Experiments/porting-galaxy-tab-a
S=$WIN/sm-t280-phase6/scripts
OUT=$T/out/target/product/gtexswifi
SCALE_DEFAULT=${SWIFTANGLE_SCALE_DEFAULT:-3}
ODIN=$WIN/sm-t280-phase6/packages/SM-T280-android10-camera-PHASE6-v92-DO-NOT-FLASH.tar.md5

cd "$T"
for v in apply-v87-clean-wifi-angle apply-v88-swiftangle-scaled-egl apply-v89-wifi-start-recovery apply-v90-wifi-wcnd-notify \
         apply-v91-mediaprovider-pending-scan apply-v91b-swiftangle-scale-to-window apply-v92-camera-provider apply-v92b-linker-textrel-vendor-hal; do
  python3 "$S/$v.py" | grep -E 'ERROR|_DONE'
done
sed -i -E "s/^(PRODUCT_PROPERTY_OVERRIDES \+= persist\.swiftangle\.scale=)[0-9]+/\1${SCALE_DEFAULT}/" device/samsung/gtexswifi/device.mk
source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null

echo "=== 1) linker (V92b) + camera ==="
mka linker android.hardware.camera.provider@2.4-service android.hardware.camera.provider@2.4-impl libcamera_shim 2>&1 | grep -E 'error:|FAILED|build completed' | tail -8 | tee /tmp/v92-a.log
grep -q 'build completed' /tmp/v92-a.log || { echo 'V92_FAIL: phase 1'; exit 1; }

echo "=== 2) system.img ==="
mka systemimage 2>&1 | grep -vE '^\[ *[0-9]+% ' | grep -E 'error:|FAILED|build completed' | tail -8 | tee /tmp/v92-b.log
grep -q 'build completed' /tmp/v92-b.log || { echo 'V92_FAIL: systemimage'; exit 1; }

echo "=== 3) static validation ==="
test -f "$OUT/system/vendor/bin/hw/android.hardware.camera.provider@2.4-service" || { echo 'V92_FAIL: provider'; exit 1; }
test -f "$OUT/system/vendor/lib/hw/android.hardware.camera.provider@2.4-impl.so" || { echo 'V92_FAIL: impl'; exit 1; }
test -f "$OUT/system/lib/libcamera_shim.so" || { echo 'V92_FAIL: shim'; exit 1; }
grep -q 'LD_SHIM_LIBS' "$OUT/system/vendor/etc/init/zz-camera-provider-shim.rc" || { echo 'V92_FAIL: rc override'; exit 1; }
grep -q 'android.hardware.camera.provider' "$OUT/system/vendor/etc/vintf/manifest.xml" 2>/dev/null || grep -q 'android.hardware.camera.provider' "$OUT/system/vendor/manifest.xml" 2>/dev/null || { echo 'V92_FAIL: VINTF'; exit 1; }
grep -q 'V92_TEXTREL' "$T/bionic/linker/linker.cpp" || { echo 'V92_FAIL: linker src'; exit 1; }
L=$(find "$OUT/system/apex" -path '*runtime*' -name 'linker' | head -1); test -n "$L" || L="$OUT/system/bin/linker"
test -f "$L" || { echo 'V92_FAIL: linker bin'; exit 1; }
grep -a -q '/system/vendor/bin/hw/' "$L" || { echo 'V92_FAIL: linker without V92b'; exit 1; }
grep -q "^persist.swiftangle.scale=${SCALE_DEFAULT}$" "$OUT/system/build.prop" || { echo 'V92_FAIL: scale'; exit 1; }
grep -a -q 'V90_WCND' "$OUT/system/vendor/lib/libwifi-hal.so" || { echo 'V92_FAIL: V90'; exit 1; }
grep -q '^    user system' "$OUT/system/etc/init/wcnd.rc" && { echo 'V72_REGRESSION'; exit 1; }
echo 'V92_STATIC_VERIFY_PASS'

echo "=== 4) Odin package ==="
python3 "$S/legacy_sparse.py" "$OUT/system.img" "$WIN/results/phase-5/system-legacy-sparse-odin-v92.img"
bash "$S/package-system-for-odin.sh" "$OUT/boot.img" "$WIN/results/phase-5/system-legacy-sparse-odin-v92.img" "$ODIN"
bash "$S/verify-odin-boot-system-package.sh" "$ODIN"
sha256sum "$OUT/boot.img" "$OUT/system.img" "$ODIN"
echo 'V92_BUILD_AND_PACKAGE_PASS'
