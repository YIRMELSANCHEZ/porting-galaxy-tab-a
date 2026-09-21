#!/bin/bash
# V84: on top of V83. Applies V78..V84 (SwiftAngle + SwiftShader patches + ld.config of the swcodec APEX +
# debug.angle.backend=1), rebuilds system.img, generates the test APK and packages boot(V75) +
# system(V84). Run in WSL (lineage).
set -e
T=/home/lineage/android/lineage-17.1
WIN=/mnt/c/Dev/Experiments/porting-galaxy-tab-a
S=$WIN/sm-t280-phase6/scripts
OUT=$T/out/target/product/gtexswifi
PKG=$T/device/samsung/gtexswifi/swiftangle/lib/armeabi-v7a
APK=$OUT/system/app/SwiftAngle/SwiftAngle.apk
TEST=$WIN/sm-t280-phase6/apps/SwiftAngle-test-v84.apk
LDC=$OUT/system/apex/com.android.media.swcodec/etc/ld.config.txt

cd "$T"
for v in apply-v78-swiftangle apply-v79-swiftangle-egl-name apply-v80-reactor-arm-symbols apply-v81-reactor-host-cpu \
         apply-v82-egl-window-log apply-v83-gles-draw-log apply-v84-swcodec-sphal-angle-backend; do
  python3 "$S/$v.py" | grep -E 'ERROR|_DONE'
done
source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null

echo "=== 1) SwiftShader ==="
mka libEGL_swiftshader libGLESv2_swiftshader libGLESv1_CM_swiftshader 2>&1 | grep -E "error:|FAILED|build completed" | tail -8 | tee /tmp/v84-mka.log
grep -q "build completed" /tmp/v84-mka.log || { echo "V84_FAIL: SwiftShader does not compile"; exit 1; }
for m in EGL GLESv2 GLESv1_CM; do cp -f "$OUT/system/vendor/lib/egl/lib${m}_swiftshader.so" "$PKG/lib${m}_angle.so"; done

echo "=== 2) SwiftAngle + system.img ==="
mka SwiftAngle systemimage 2>&1 | grep -vE '^\[ *[0-9]+% ' | grep -E "error:|FAILED|build completed" | tail -5 | tee /tmp/v84-mka2.log
grep -q "build completed" /tmp/v84-mka2.log || { echo "V84_FAIL: systemimage"; exit 1; }
test -f "$APK" || { echo "V84_FAIL: SwiftAngle.apk not built"; exit 1; }
unzip -v "$APK" | grep a4a_rules.json | grep -q "Stored" || { echo "V84_FAIL: compressed asset"; exit 1; }
grep -q 'namespace.sphal.search.paths += /system/${LIB}$' "$LDC" || { echo "V84_FAIL: APEX ld.config without /system/lib"; exit 1; }
echo "apex ld.config: sphal += /system/lib OK"
grep -q 'debug.angle.backend=1' "$OUT/system/build.prop" || { echo "V84_FAIL: build.prop without debug.angle.backend"; exit 1; }
echo "build.prop: debug.angle.backend=1 OK"
grep -q '^    user system' "$OUT/system/etc/init/wcnd.rc" && { echo "V72_REGRESSION"; exit 1; } || echo "V72 ok"
test "$(sha256sum "$OUT/system.img" | cut -c1-16)" != "2edaa8a61c6708ee" || { echo "V84_FAIL: system.img equal to V79"; exit 1; }

echo "=== 3) test APK ==="
W=$(mktemp -d)
cp "$APK" "$W/u.apk"
mkdir -p "$W/lib/armeabi-v7a"; cp "$PKG"/*.so "$W/lib/armeabi-v7a/"
( cd "$W" && zip -q -0 -r u.apk lib )
java -Djava.library.path="$T/out/host/linux-x86/lib64" -jar "$T/out/host/linux-x86/framework/signapk.jar" -a 4096 \
  "$T/build/target/product/security/platform.x509.pem" "$T/build/target/product/security/platform.pk8" \
  "$W/u.apk" "$TEST"
"$T/out/host/linux-x86/bin/zipalign" -c -p 4 "$TEST" && echo "test-apk: zipalign -p OK"
sha256sum "$TEST"
rm -rf "$W"

echo "=== 4) package (boot V75 + system V84) ==="
sha256sum "$OUT/boot.img" | cut -c1-16 | sed 's/^/boot.img (V75 fe89ef3181bfecea): /'
python3 "$S/legacy_sparse.py" "$OUT/system.img" "$WIN/results/fase-5/system-legacy-sparse-odin-v84.img"
bash "$S/package-system-for-odin.sh" "$OUT/boot.img" \
  "$WIN/results/fase-5/system-legacy-sparse-odin-v84.img" \
  "$WIN/sm-t280-phase6/packages/SM-T280-android10-swcodec-sphal-PHASE6-v84-DO-NOT-FLASH.tar.md5"
