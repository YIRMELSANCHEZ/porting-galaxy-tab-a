#!/bin/bash
# V96 (test APK only): SwiftShader V94 + V95 (stats gated) + V96 (real fences, deferred clears).
set -eo pipefail
T=/home/lineage/android/lineage-17.1
WIN=/mnt/c/Dev/Experiments/porting-galaxy-tab-a
S=$WIN/sm-t280-phase6/scripts
OUT=$T/out/target/product/gtexswifi
PKG=$T/device/samsung/gtexswifi/swiftangle/lib/armeabi-v7a
APK=$OUT/system/app/SwiftAngle/SwiftAngle.apk
TEST=$WIN/sm-t280-phase6/apps/SwiftAngle-test-v96.apk

cd "$T"
for v in apply-v93-swiftangle-quality-props apply-v94-swiftshader-nv12 apply-v94b-omx-hw-video apply-v95-stats apply-v96-fence-deferclear apply-v96b-clear-per-cluster apply-v96c-worker-spin apply-v96d-gl-time; do
  python3 "$S/$v.py" | grep -E 'ERROR|_DONE'
done
source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null

echo "=== 1) SwiftShader ==="
mka libEGL_swiftshader libGLESv2_swiftshader libGLESv1_CM_swiftshader 2>&1 | grep -E 'error:|FAILED|build completed' | tail -20 | tee /tmp/v96-a.log
grep -q 'build completed' /tmp/v96-a.log || { echo 'V96_FAIL: SwiftShader'; exit 1; }
for m in EGL GLESv2 GLESv1_CM; do cp -f "$OUT/system/vendor/lib/egl/lib${m}_swiftshader.so" "$PKG/lib${m}_angle.so"; done
grep -a -q 'persist.swiftangle.deferclear' "$PKG/libGLESv2_angle.so" || { echo 'V96_FAIL: without deferclear'; exit 1; }
grep -a -q 'persist.swiftangle.fence' "$PKG/libEGL_angle.so" || { echo 'V96_FAIL: without fence'; exit 1; }

echo "=== 2) SwiftAngle ==="
mka SwiftAngle 2>&1 | grep -E 'error:|FAILED|build completed' | tail -8 | tee /tmp/v96-b.log
grep -q 'build completed' /tmp/v96-b.log || { echo 'V96_FAIL: SwiftAngle'; exit 1; }

echo "=== 3) test APK ==="
W=$(mktemp -d)
cp "$APK" "$W/u.apk"
mkdir -p "$W/lib/armeabi-v7a"
cp "$PKG"/*.so "$W/lib/armeabi-v7a/"
( cd "$W" && zip -q -0 -r u.apk lib )
java -Djava.library.path="$T/out/host/linux-x86/lib64" -jar "$T/out/host/linux-x86/framework/signapk.jar" -a 4096 \
  "$T/build/target/product/security/platform.x509.pem" "$T/build/target/product/security/platform.pk8" "$W/u.apk" "$TEST"
"$T/out/host/linux-x86/bin/zipalign" -c -p 4 "$TEST"
rm -rf "$W"
sha256sum "$TEST"
echo 'V96_TEST_APK_PASS'
