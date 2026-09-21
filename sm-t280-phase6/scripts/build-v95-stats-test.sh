#!/bin/bash
# V95 (test APK only): SwiftShader V94 + synchronization counters (V95_STATS). Does not produce a package.
set -eo pipefail
T=/home/lineage/android/lineage-17.1
WIN=/mnt/c/Dev/Experiments/porting-galaxy-tab-a
S=$WIN/sm-t280-phase6/scripts
OUT=$T/out/target/product/gtexswifi
PKG=$T/device/samsung/gtexswifi/swiftangle/lib/armeabi-v7a
APK=$OUT/system/app/SwiftAngle/SwiftAngle.apk
TEST=$WIN/sm-t280-phase6/apps/SwiftAngle-test-v95-stats.apk

cd "$T"
for v in apply-v93-swiftangle-quality-props apply-v94-swiftshader-nv12 apply-v94b-omx-hw-video apply-v95-stats; do
  python3 "$S/$v.py" | grep -E 'ERROR|_DONE'
done
source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null

echo "=== 1) SwiftShader ==="
mka libEGL_swiftshader libGLESv2_swiftshader libGLESv1_CM_swiftshader 2>&1 | grep -E 'error:|FAILED|build completed' | tail -12 | tee /tmp/v95-a.log
grep -q 'build completed' /tmp/v95-a.log || { echo 'V95_FAIL: SwiftShader'; exit 1; }
for m in EGL GLESv2 GLESv1_CM; do cp -f "$OUT/system/vendor/lib/egl/lib${m}_swiftshader.so" "$PKG/lib${m}_angle.so"; done
grep -a -q 'V95_STATS' "$PKG/libGLESv2_angle.so" || { echo 'V95_FAIL: without stats'; exit 1; }
grep -a -q 'V95_EGL' "$PKG/libEGL_angle.so" || { echo 'V95_FAIL: without stats EGL'; exit 1; }

echo "=== 2) SwiftAngle ==="
mka SwiftAngle 2>&1 | grep -E 'error:|FAILED|build completed' | tail -8 | tee /tmp/v95-b.log
grep -q 'build completed' /tmp/v95-b.log || { echo 'V95_FAIL: SwiftAngle'; exit 1; }

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
echo 'V95_TEST_APK_PASS'
