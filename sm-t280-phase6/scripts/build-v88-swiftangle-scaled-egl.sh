#!/bin/bash
# V88: V87 + EGL/FrameBuffer dimensions consistent with the scaled SwiftAngle buffer.
set -eo pipefail
T=/home/lineage/android/lineage-17.1
WIN=/mnt/c/Dev/Experiments/porting-galaxy-tab-a
S=$WIN/sm-t280-phase6/scripts
OUT=$T/out/target/product/gtexswifi
PKG=$T/device/samsung/gtexswifi/swiftangle/lib/armeabi-v7a
APK=$OUT/system/app/SwiftAngle/SwiftAngle.apk
ODIN=$WIN/sm-t280-phase6/packages/SM-T280-android10-swiftangle-scaled-egl-PHASE6-v88-DO-NOT-FLASH.tar.md5

cd "$T"
python3 "$S/apply-v87-clean-wifi-angle.py" | grep -E 'ERROR|_DONE|V87:'
python3 "$S/apply-v88-swiftangle-scaled-egl.py" | grep -E 'ERROR|_DONE|V88:'
source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null

echo "=== SwiftShader V88 ==="
mka libEGL_swiftshader libGLESv2_swiftshader libGLESv1_CM_swiftshader 2>&1 \
  | grep -E "error:|FAILED|build completed" | tail -8 | tee /tmp/v88-swiftshader.log
grep -q "build completed" /tmp/v88-swiftshader.log || { echo "V88_FAIL: SwiftShader"; exit 1; }
for m in EGL GLESv2 GLESv1_CM; do
  cp -f "$OUT/system/vendor/lib/egl/lib${m}_swiftshader.so" "$PKG/lib${m}_angle.so"
done

echo "=== SwiftAngle + system.img ==="
mka SwiftAngle systemimage 2>&1 \
  | grep -vE '^\[ *[0-9]+% ' | grep -E "error:|FAILED|build completed" | tail -8 | tee /tmp/v88-system.log
grep -q "build completed" /tmp/v88-system.log || { echo "V88_FAIL: systemimage"; exit 1; }
grep -a -q 'persist.swiftangle.scale' "$OUT/system/vendor/lib/egl/libEGL_swiftshader.so" \
  || { echo "V88_FAIL: property not compiled"; exit 1; }
grep -q 'V88_SCALE_EGL' "$T/external/swiftshader/src/OpenGL/libEGL/Surface.cpp" \
  || { echo "V88_FAIL: EGL patch missing"; exit 1; }
grep -q '^persist.swiftangle.scale=2$' "$OUT/system/build.prop" \
  || { echo "V88_FAIL: default scale"; exit 1; }
test -f "$APK" || { echo "V88_FAIL: SwiftAngle.apk"; exit 1; }
echo "V88_STATIC_VERIFY_PASS"

echo "=== Odin ==="
python3 "$S/legacy_sparse.py" "$OUT/system.img" "$WIN/results/phase-5/system-legacy-sparse-odin-v88.img"
bash "$S/package-system-for-odin.sh" "$OUT/boot.img" \
  "$WIN/results/phase-5/system-legacy-sparse-odin-v88.img" "$ODIN"
bash "$S/verify-odin-boot-system-package.sh" "$ODIN"
sha256sum "$ODIN"
echo "V88_BUILD_AND_PACKAGE_PASS"
