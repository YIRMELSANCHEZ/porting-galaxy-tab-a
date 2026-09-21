#!/bin/bash
# V78: patch (_angle names in SwiftShader + SwiftAngle package), recompiles the SwiftShader libs,
# copies them renamed as the package's prebuilt JNI, builds SwiftAngle + system.img and packages
# boot(V75, already in out/) + system(V78). Run inside WSL (user lineage).
set -e
T=/home/lineage/android/lineage-17.1
WIN=/mnt/c/Dev/Experiments/porting-galaxy-tab-a
S=$WIN/sm-t280-phase6/scripts
OUT=$T/out/target/product/gtexswifi
PKG=$T/device/samsung/gtexswifi/swiftangle/lib/armeabi-v7a

cd "$T"
python3 "$S/apply-v78-swiftangle.py"
source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null

echo "=== 1) SwiftShader (with _angle names) ==="
mka libEGL_swiftshader libGLESv2_swiftshader libGLESv1_CM_swiftshader 2>&1 | grep -E "error:|FAILED|build completed" | tail -5
for m in EGL GLESv2 GLESv1_CM; do cp -f "$OUT/system/vendor/lib/egl/lib${m}_swiftshader.so" "$PKG/lib${m}_angle.so"; done
ls -la "$PKG"
strings "$PKG/libEGL_angle.so" | grep -cE "libGLESv2_angle.so" | sed 's/^/libEGL_angle referencia libGLESv2_angle: /'

echo "=== 2) SwiftAngle + system.img ==="
mka SwiftAngle systemimage 2>&1 | grep -vE '^\[ *[0-9]+% ' | grep -E "error:|FAILED|SwiftAngle|build completed" | tail -8
echo "=== verify ==="
test -f "$OUT/system/app/SwiftAngle/SwiftAngle.apk" || { echo "V78_FAIL: SwiftAngle.apk not built"; exit 1; }
ls -la "$OUT/system/app/SwiftAngle/" "$OUT/system/app/SwiftAngle/lib/arm/" 2>&1
"$T/out/host/linux-x86/bin/aapt2" dump badging "$OUT/system/app/SwiftAngle/SwiftAngle.apk" 2>/dev/null | grep -E "^package|native-code|extractNativeLibs" | head -3
"$T/out/host/linux-x86/bin/aapt2" dump xmltree --file AndroidManifest.xml "$OUT/system/app/SwiftAngle/SwiftAngle.apk" 2>/dev/null | grep -cE "ANGLE_FOR_ANDROID" | sed 's/^/intent ANGLE_FOR_ANDROID: /'
unzip -l "$OUT/system/app/SwiftAngle/SwiftAngle.apk" | grep -c "assets/a4a_rules.json" | sed 's/^/asset a4a_rules.json: /'
test "$(sha256sum "$OUT/system.img" | cut -c1-16)" != "cbee9cdb2b76063f" || { echo "V78_FAIL: system.img did not change vs V76"; exit 1; }
grep -q '^    user system' "$OUT/system/etc/init/wcnd.rc" && { echo "V72_REGRESSION"; exit 1; } || echo "V72 ok"
sha256sum "$OUT/boot.img" | cut -c1-16 | sed 's/^/boot.img (V75 fe89ef3181bfecea): /'

echo "=== 3) package (boot V75 + system V78) ==="
python3 "$S/legacy_sparse.py" "$OUT/system.img" "$WIN/results/fase-5/system-legacy-sparse-odin-v78.img"
bash "$S/package-system-for-odin.sh" "$OUT/boot.img" \
  "$WIN/results/fase-5/system-legacy-sparse-odin-v78.img" \
  "$WIN/sm-t280-phase6/packages/SM-T280-android10-swiftangle-PHASE6-v78-DO-NOT-FLASH.tar.md5"
