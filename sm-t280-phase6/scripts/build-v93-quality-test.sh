#!/bin/bash
# V93 (test APK only, no Odin package): SwiftShader with fractional scale and quality via
# properties. Accumulates V87..V91b. Run in WSL (lineage).
set -eo pipefail
T=/home/lineage/android/lineage-17.1
WIN=/mnt/c/Dev/Experiments/porting-galaxy-tab-a
S=$WIN/sm-t280-phase6/scripts
OUT=$T/out/target/product/gtexswifi
PKG=$T/device/samsung/gtexswifi/swiftangle/lib/armeabi-v7a
APK=$OUT/system/app/SwiftAngle/SwiftAngle.apk
TEST=$WIN/sm-t280-phase6/apps/SwiftAngle-test-v93.apk

cd "$T"
for v in apply-v87-clean-wifi-angle apply-v88-swiftangle-scaled-egl apply-v89-wifi-start-recovery apply-v90-wifi-wcnd-notify \
         apply-v91-mediaprovider-pending-scan apply-v91b-swiftangle-scale-to-window apply-v93-swiftangle-quality-props; do
  python3 "$S/$v.py" | grep -E 'ERROR|_DONE'
done
source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null

echo "=== 1) SwiftShader ==="
mka libEGL_swiftshader libGLESv2_swiftshader libGLESv1_CM_swiftshader 2>&1 | grep -E 'error:|FAILED|build completed' | tail -8 | tee /tmp/v93-a.log
grep -q 'build completed' /tmp/v93-a.log || { echo 'V93_FAIL: SwiftShader'; exit 1; }
for m in EGL GLESv2 GLESv1_CM; do cp -f "$OUT/system/vendor/lib/egl/lib${m}_swiftshader.so" "$PKG/lib${m}_angle.so"; done
grep -a -q 'persist.swiftangle.texq' "$PKG/libGLESv2_angle.so" || { echo 'V93_FAIL: libGLESv2 without V93'; exit 1; }
grep -a -q 'persist.swiftangle.scale' "$PKG/libEGL_angle.so" || { echo 'V93_FAIL: libEGL without scale'; exit 1; }

echo "=== 2) SwiftAngle ==="
mka SwiftAngle 2>&1 | grep -E 'error:|FAILED|build completed' | tail -8 | tee /tmp/v93-b.log
grep -q 'build completed' /tmp/v93-b.log || { echo 'V93_FAIL: SwiftAngle'; exit 1; }

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
echo 'V93_TEST_APK_PASS'
