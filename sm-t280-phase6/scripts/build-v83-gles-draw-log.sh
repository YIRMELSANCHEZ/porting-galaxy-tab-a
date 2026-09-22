#!/bin/bash
# V83: on top of V82 (draw/clear/blit log in libGLESv2 SwiftShader), recompiles SwiftShader, rebuilds SwiftAngle +
# system.img, generates the test APK (adb install -r, without reflashing) and, unless QUICK=1, packages
# boot(V75) + system(V83). Run in WSL (lineage).
set -e
T=/home/lineage/android/lineage-17.1
WIN=/mnt/c/Dev/Experiments/porting-galaxy-tab-a
S=$WIN/sm-t280-phase6/scripts
OUT=$T/out/target/product/gtexswifi
PKG=$T/device/samsung/gtexswifi/swiftangle/lib/armeabi-v7a
APK=$OUT/system/app/SwiftAngle/SwiftAngle.apk
TEST=$WIN/sm-t280-phase6/apps/SwiftAngle-test-v83.apk

cd "$T"
python3 "$S/apply-v78-swiftangle.py"
python3 "$S/apply-v79-swiftangle-egl-name.py"
python3 "$S/apply-v80-reactor-arm-symbols.py"
python3 "$S/apply-v81-reactor-host-cpu.py"
python3 "$S/apply-v82-egl-window-log.py"
python3 "$S/apply-v83-gles-draw-log.py"
source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null

echo "=== 1) SwiftShader ==="
mka libEGL_swiftshader libGLESv2_swiftshader libGLESv1_CM_swiftshader 2>&1 | grep -E "error:|FAILED|build completed" | tail -8 | tee /tmp/v83-mka.log
grep -q "build completed" /tmp/v83-mka.log || { echo "V83_FAIL: SwiftShader does not compile"; exit 1; }
for m in EGL GLESv2 GLESv1_CM; do cp -f "$OUT/system/vendor/lib/egl/lib${m}_swiftshader.so" "$PKG/lib${m}_angle.so"; done
strings "$PKG/libGLESv2_angle.so" | grep -c "unresolved external symbol" | sed 's/^/libGLESv2_angle with log V83: /'

echo "=== 2) SwiftAngle + system.img ==="
mka SwiftAngle systemimage 2>&1 | grep -vE '^\[ *[0-9]+% ' | grep -E "error:|FAILED|build completed" | tail -5
test -f "$APK" || { echo "V83_FAIL: SwiftAngle.apk not built"; exit 1; }
unzip -v "$APK" | grep a4a_rules.json | grep -q "Stored" || { echo "V83_FAIL: compressed asset"; exit 1; }
grep -q '^    user system' "$OUT/system/etc/init/wcnd.rc" && { echo "V72_REGRESSION"; exit 1; } || echo "V72 ok"

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

if [ "$QUICK" = "1" ]; then echo "QUICK: without packaging"; exit 0; fi
echo "=== 4) package (boot V75 + system V83) ==="
sha256sum "$OUT/boot.img" | cut -c1-16 | sed 's/^/boot.img (V75 fe89ef3181bfecea): /'
python3 "$S/legacy_sparse.py" "$OUT/system.img" "$WIN/results/phase-5/system-legacy-sparse-odin-v83.img"
bash "$S/package-system-for-odin.sh" "$OUT/boot.img" \
  "$WIN/results/phase-5/system-legacy-sparse-odin-v83.img" \
  "$WIN/sm-t280-phase6/packages/SM-T280-android10-swiftangle-PHASE6-v83-DO-NOT-FLASH.tar.md5"
