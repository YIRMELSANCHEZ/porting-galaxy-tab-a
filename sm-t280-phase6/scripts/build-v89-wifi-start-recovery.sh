#!/bin/bash
# V89: V88 + bounded delayed recovery for the SC2331 Wi-Fi startup race.
set -eo pipefail

T=/home/lineage/android/lineage-17.1
WIN=/mnt/c/Dev/Experiments/porting-galaxy-tab-a
S=$WIN/sm-t280-phase6/scripts
OUT=$T/out/target/product/gtexswifi
PKG=$T/device/samsung/gtexswifi/swiftangle/lib/armeabi-v7a
APK=$OUT/system/app/SwiftAngle/SwiftAngle.apk
WIFI_JAR=$OUT/system/framework/wifi-service.jar
ODIN=$WIN/sm-t280-phase6/packages/SM-T280-android10-wifi-recovery-angle-PHASE6-v89-DO-NOT-FLASH.tar.md5

cd "$T"
python3 "$S/apply-v87-clean-wifi-angle.py" | grep -E 'ERROR|_DONE|V87:'
python3 "$S/apply-v88-swiftangle-scaled-egl.py" | grep -E 'ERROR|_DONE|V88:'
python3 "$S/apply-v89-wifi-start-recovery.py" | grep -E 'ERROR|_DONE|V89:'

source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null

echo "=== 1) wifi-service V89 ==="
mka wifi-service 2>&1 \
  | grep -E 'error:|FAILED|build completed' | tail -12 | tee /tmp/v89-wifi.log
grep -q 'build completed' /tmp/v89-wifi.log || { echo 'V89_FAIL: wifi-service'; exit 1; }

echo "=== 2) SwiftShader V88 acumulativo ==="
mka libEGL_swiftshader libGLESv2_swiftshader libGLESv1_CM_swiftshader 2>&1 \
  | grep -E 'error:|FAILED|build completed' | tail -12 | tee /tmp/v89-swiftshader.log
grep -q 'build completed' /tmp/v89-swiftshader.log || { echo 'V89_FAIL: SwiftShader'; exit 1; }
for m in EGL GLESv2 GLESv1_CM; do
  cp -f "$OUT/system/vendor/lib/egl/lib${m}_swiftshader.so" "$PKG/lib${m}_angle.so"
done

echo "=== 3) SwiftAngle + system.img ==="
mka SwiftAngle wifi-service systemimage 2>&1 \
  | grep -vE '^\[ *[0-9]+% ' \
  | grep -E 'error:|FAILED|build completed' | tail -12 | tee /tmp/v89-system.log
grep -q 'build completed' /tmp/v89-system.log || { echo 'V89_FAIL: systemimage'; exit 1; }

echo "=== 4) static validation ==="
grep -q 'V89_SC2331_START_RECOVERY' \
  "$T/frameworks/opt/net/wifi/service/java/com/android/server/wifi/WifiController.java" \
  || { echo 'V89_FAIL: source marker'; exit 1; }
grep -q 'V89_MAX_STA_START_RETRIES          = 6' \
  "$T/frameworks/opt/net/wifi/service/java/com/android/server/wifi/WifiController.java" \
  || { echo 'V89_FAIL: retry bound'; exit 1; }
grep -q 'V89_STA_START_RETRY_DELAY_MS       = 15 \* 1000' \
  "$T/frameworks/opt/net/wifi/service/java/com/android/server/wifi/WifiController.java" \
  || { echo 'V89_FAIL: retry delay'; exit 1; }
test -f "$WIFI_JAR" || { echo 'V89_FAIL: wifi-service.jar'; exit 1; }
unzip -p "$WIFI_JAR" classes.dex > /tmp/v89-wifi-service.dex
grep -a -q 'V89 SC2331 client start failure' /tmp/v89-wifi-service.dex \
  || { echo 'V89_FAIL: runtime code absent from wifi-service.jar'; exit 1; }
grep -q 'V88_SCALE_EGL' "$T/external/swiftshader/src/OpenGL/libEGL/Surface.cpp" \
  || { echo 'V89_FAIL: V88 EGL scaling absent'; exit 1; }
grep -a -q 'persist.swiftangle.scale' "$OUT/system/vendor/lib/egl/libEGL_swiftshader.so" \
  || { echo 'V89_FAIL: scale property absent from libEGL'; exit 1; }
grep -q '^persist.swiftangle.scale=2$' "$OUT/system/build.prop" \
  || { echo 'V89_FAIL: default scale'; exit 1; }
test -f "$APK" || { echo 'V89_FAIL: SwiftAngle.apk'; exit 1; }
echo 'V89_STATIC_VERIFY_PASS'

echo "=== 5) Odin package ==="
python3 "$S/legacy_sparse.py" "$OUT/system.img" \
  "$WIN/results/phase-5/system-legacy-sparse-odin-v89.img"
bash "$S/package-system-for-odin.sh" "$OUT/boot.img" \
  "$WIN/results/phase-5/system-legacy-sparse-odin-v89.img" "$ODIN"
bash "$S/verify-odin-boot-system-package.sh" "$ODIN"
sha256sum "$OUT/boot.img" "$OUT/system.img" \
  "$WIN/results/phase-5/system-legacy-sparse-odin-v89.img" \
  "$OUT/system/vendor/lib/egl/libEGL_swiftshader.so" "$WIFI_JAR" "$APK" "$ODIN"
echo "V89_PACKAGE=$ODIN"
echo 'V89_BUILD_AND_PACKAGE_PASS'
