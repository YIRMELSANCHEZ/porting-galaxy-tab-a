#!/bin/bash
# V87: V86 without V82/V83 traces, SDIO retry for sprdwl, persistent ANGLE opt-in and
# SwiftAngle buffer at half resolution (configurable 1..4). Camera/GNSS still out.
set -e
T=/home/lineage/android/lineage-17.1
WIN=/mnt/c/Dev/Experiments/porting-galaxy-tab-a
S=$WIN/sm-t280-phase6/scripts
OUT=$T/out/target/product/gtexswifi
PKG=$T/device/samsung/gtexswifi/swiftangle/lib/armeabi-v7a
APK=$OUT/system/app/SwiftAngle/SwiftAngle.apk
TEST=$WIN/sm-t280-phase6/apps/SwiftAngle-test-v87.apk
LDC=$OUT/system/apex/com.android.media.swcodec/etc/ld.config.txt
ODIN=$WIN/sm-t280-phase6/packages/SM-T280-android10-clean-wifi-angle-PHASE6-v87-DO-NOT-FLASH.tar.md5

cd "$T"
for v in apply-v78-swiftangle apply-v79-swiftangle-egl-name apply-v80-reactor-arm-symbols apply-v81-reactor-host-cpu \
         apply-v84-swcodec-sphal-angle-backend apply-v85-swcodec-sphal-hw apply-v86-libdither-deps \
         apply-v87-clean-wifi-angle; do
  python3 "$S/$v.py" | grep -E 'ERROR|_DONE|V87:'
done
source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null

echo "=== 1) clean SwiftShader ==="
mka libEGL_swiftshader libGLESv2_swiftshader libGLESv1_CM_swiftshader 2>&1 \
  | grep -E "error:|FAILED|build completed" | tail -8 | tee /tmp/v87-swiftshader.log
grep -q "build completed" /tmp/v87-swiftshader.log || { echo "V87_FAIL: SwiftShader does not compile"; exit 1; }
for m in EGL GLESv2 GLESv1_CM; do
  cp -f "$OUT/system/vendor/lib/egl/lib${m}_swiftshader.so" "$PKG/lib${m}_angle.so"
done

echo "=== 2) Wi-Fi HAL + SwiftAngle + system.img ==="
mka android.hardware.wifi@1.0-service.legacy libdither SwiftAngle systemimage 2>&1 \
  | grep -vE '^\[ *[0-9]+% ' | grep -E "error:|FAILED|build completed" | tail -8 | tee /tmp/v87-system.log
grep -q "build completed" /tmp/v87-system.log || { echo "V87_FAIL: systemimage"; exit 1; }

echo "=== 3) static checks ==="
test -f "$APK" || { echo "V87_FAIL: SwiftAngle.apk not built"; exit 1; }
unzip -v "$APK" | grep a4a_rules.json | grep -q "Stored" || { echo "V87_FAIL: compressed asset"; exit 1; }
"$T/prebuilts/sdk/tools/linux/bin/aapt" dump permissions "$APK" | grep -q 'android.permission.WRITE_SECURE_SETTINGS' \
  || { echo "V87_FAIL: WRITE_SECURE_SETTINGS permission missing"; exit 1; }
"$T/prebuilts/sdk/tools/linux/bin/aapt" dump xmltree "$APK" AndroidManifest.xml \
  | grep -q 'BootCompletedReceiver' || { echo "V87_FAIL: receiver outside the manifest"; exit 1; }
unzip -p "$APK" classes.dex | strings | grep -q 'BootCompletedReceiver' \
  || { echo "V87_FAIL: receiver missing from classes.dex"; exit 1; }
grep -R -q 'V82\|V83\|ssLogDraw\|GL blitFramebuffer #' "$T/external/swiftshader/src/OpenGL" \
  && { echo "V87_FAIL: V82/V83 traces remain"; exit 1; } || echo "V82/V83 traces: ABSENT"
grep -q 'V87_WIFI_SDIO_RETRY' "$T/frameworks/opt/net/wifi/libwifi_hal/wifi_hal_common.cpp" \
  || { echo "V87_FAIL: Wi-Fi retry missing"; exit 1; }
grep -q 'V87_SWIFTANGLE_SCALE' "$T/external/swiftshader/src/OpenGL/libEGL/Surface.cpp" \
  || { echo "V87_FAIL: SwiftAngle scaling missing"; exit 1; }
grep -q '^persist.swiftangle.scale=2$' "$OUT/system/build.prop" \
  || { echo "V87_FAIL: scale property missing"; exit 1; }
grep -q 'namespace.sphal.permitted.paths += /system/${LIB}/hw$' "$LDC" \
  || { echo "V87_FAIL: ld.config swcodec"; exit 1; }
grep -q 'debug.angle.backend=1' "$OUT/system/build.prop" \
  || { echo "V87_FAIL: debug.angle.backend"; exit 1; }
/usr/bin/readelf -d "$OUT/system/lib/libdither.so" | grep NEEDED | grep -q android_runtime \
  && { echo "V87_FAIL: libdither still has libandroid_runtime"; exit 1; } || true
test ! -e "$OUT/system/vendor/bin/hw/android.hardware.camera.provider@2.4-service" \
  || { echo "V87_FAIL: camera provider reappeared"; exit 1; }
echo "V87_STATIC_VERIFY_PASS"

echo "=== 4) test APK ==="
W=$(mktemp -d)
cp "$APK" "$W/u.apk"
mkdir -p "$W/lib/armeabi-v7a"
cp "$PKG"/*.so "$W/lib/armeabi-v7a/"
( cd "$W" && zip -q -0 -r u.apk lib )
java -Djava.library.path="$T/out/host/linux-x86/lib64" \
  -jar "$T/out/host/linux-x86/framework/signapk.jar" -a 4096 \
  "$T/build/target/product/security/platform.x509.pem" \
  "$T/build/target/product/security/platform.pk8" "$W/u.apk" "$TEST"
"$T/out/host/linux-x86/bin/zipalign" -c -p 4 "$TEST"
sha256sum "$TEST"
rm -rf "$W"

echo "=== 5) Odin package (boot V75 + system V87) ==="
sha256sum "$OUT/boot.img" | sed 's/^/boot: /'
python3 "$S/legacy_sparse.py" "$OUT/system.img" "$WIN/results/phase-5/system-legacy-sparse-odin-v87.img"
bash "$S/package-system-for-odin.sh" "$OUT/boot.img" \
  "$WIN/results/phase-5/system-legacy-sparse-odin-v87.img" "$ODIN"
bash "$S/verify-odin-boot-system-package.sh" "$ODIN"
echo "V87_PACKAGE=$ODIN"
sha256sum "$ODIN"
echo "V87_BUILD_AND_PACKAGE_PASS"
