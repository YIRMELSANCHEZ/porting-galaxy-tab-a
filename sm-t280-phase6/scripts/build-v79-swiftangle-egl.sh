#!/bin/bash
# V79: on top of V78. Patches libEGL.hpp (libEGL_angle.so name) and the package Android.mk (-0 json),
# recompiles SwiftShader, rebuilds SwiftAngle + system.img, ALSO generates a test APK with the
# embedded libs and signed with the platform key (installable with adb install -r as an update of the
# system package, without reflashing) and packages boot(V75) + system(V79). Run in WSL (lineage).
set -e
T=/home/lineage/android/lineage-17.1
WIN=/mnt/c/Dev/Experiments/porting-galaxy-tab-a
S=$WIN/sm-t280-phase6/scripts
OUT=$T/out/target/product/gtexswifi
PKG=$T/device/samsung/gtexswifi/swiftangle/lib/armeabi-v7a
APK=$OUT/system/app/SwiftAngle/SwiftAngle.apk
TEST=$WIN/sm-t280-phase6/apps/SwiftAngle-test-v79.apk

cd "$T"
python3 "$S/apply-v78-swiftangle.py"
python3 "$S/apply-v79-swiftangle-egl-name.py"
source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null

echo "=== 1) SwiftShader ==="
mka libEGL_swiftshader libGLESv2_swiftshader libGLESv1_CM_swiftshader 2>&1 | grep -E "error:|FAILED|build completed" | tail -5
for m in EGL GLESv2 GLESv1_CM; do cp -f "$OUT/system/vendor/lib/egl/lib${m}_swiftshader.so" "$PKG/lib${m}_angle.so"; done
strings "$PKG/libGLESv2_angle.so" | grep -cE "^libEGL_angle.so$" | sed 's/^/libGLESv2_angle referencia libEGL_angle: /'
strings "$PKG/libEGL_angle.so" | grep -cE "^libGLESv2_angle.so$" | sed 's/^/libEGL_angle referencia libGLESv2_angle: /'

echo "=== 2) SwiftAngle + system.img ==="
mka SwiftAngle systemimage 2>&1 | grep -vE '^\[ *[0-9]+% ' | grep -E "error:|FAILED|build completed" | tail -5
test -f "$APK" || { echo "V79_FAIL: SwiftAngle.apk not built"; exit 1; }
unzip -v "$APK" | grep a4a_rules.json | sed 's/^/asset: /'
unzip -v "$APK" | grep a4a_rules.json | grep -q "Stored" || { echo "V79_FAIL: asset still compressed"; exit 1; }
ls -la "$OUT/system/app/SwiftAngle/lib/arm/"
test "$(sha256sum "$OUT/system.img" | cut -c1-16)" != "eb4bf46dbc760873" || { echo "V79_FAIL: system.img equal to V78"; exit 1; }
grep -q '^    user system' "$OUT/system/etc/init/wcnd.rc" && { echo "V72_REGRESSION"; exit 1; } || echo "V72 ok"

echo "=== 3) test APK with embedded libs, platform signature ==="
W=$(mktemp -d)
cp "$APK" "$W/u.apk"
mkdir -p "$W/lib/armeabi-v7a"; cp "$PKG"/*.so "$W/lib/armeabi-v7a/"
# the generated manifest carries extractNativeLibs=false: the libs must be uncompressed (-0) and page-
# aligned (signapk -a 4096), otherwise PackageManager fails with INSTALL_FAILED_INVALID_APK (res=-2)
( cd "$W" && zip -q -0 -r u.apk lib )
java -Djava.library.path="$T/out/host/linux-x86/lib64" -jar "$T/out/host/linux-x86/framework/signapk.jar" -a 4096 \
  "$T/build/target/product/security/platform.x509.pem" "$T/build/target/product/security/platform.pk8" \
  "$W/u.apk" "$TEST"
"$T/out/host/linux-x86/bin/zipalign" -c -p 4 "$TEST" && echo "test-apk: zipalign -p OK"
unzip -l "$TEST" | grep -E "lib/|a4a|classes" | sed 's/^/test-apk: /'
sha256sum "$TEST"
rm -rf "$W"

echo "=== 4) package (boot V75 + system V79) ==="
sha256sum "$OUT/boot.img" | cut -c1-16 | sed 's/^/boot.img (V75 fe89ef3181bfecea): /'
python3 "$S/legacy_sparse.py" "$OUT/system.img" "$WIN/results/phase-5/system-legacy-sparse-odin-v79.img"
bash "$S/package-system-for-odin.sh" "$OUT/boot.img" \
  "$WIN/results/phase-5/system-legacy-sparse-odin-v79.img" \
  "$WIN/sm-t280-phase6/packages/SM-T280-android10-swiftangle-PHASE6-v79-DO-NOT-FLASH.tar.md5"
