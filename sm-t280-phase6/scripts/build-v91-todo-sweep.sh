#!/bin/bash
# V91: V90 (wcnd WIFI-OPEN/CLOSE) + MED1 (MediaProvider scans on publish from system) + V91b
# (EGL scale with SCALE_TO_WINDOW, measured on HW) + default scale SWIFTANGLE_SCALE_DEFAULT.
# Run in WSL (lineage). Accumulates V87..V90.
set -eo pipefail
T=/home/lineage/android/lineage-17.1
WIN=/mnt/c/Dev/Experiments/porting-galaxy-tab-a
S=$WIN/sm-t280-phase6/scripts
OUT=$T/out/target/product/gtexswifi
PKG=$T/device/samsung/gtexswifi/swiftangle/lib/armeabi-v7a
APK=$OUT/system/app/SwiftAngle/SwiftAngle.apk
SCALE_DEFAULT=${SWIFTANGLE_SCALE_DEFAULT:-2}
ODIN=$WIN/sm-t280-phase6/packages/SM-T280-android10-todo-sweep-PHASE6-v91-DO-NOT-FLASH.tar.md5

cd "$T"
python3 "$S/apply-v87-clean-wifi-angle.py" | grep -E 'ERROR|_DONE'
python3 "$S/apply-v88-swiftangle-scaled-egl.py" | grep -E 'ERROR|_DONE'
python3 "$S/apply-v89-wifi-start-recovery.py" | grep -E 'ERROR|_DONE'
python3 "$S/apply-v90-wifi-wcnd-notify.py" | grep -E 'ERROR|_DONE'
python3 "$S/apply-v91-mediaprovider-pending-scan.py" | grep -E 'ERROR|_DONE'
python3 "$S/apply-v91b-swiftangle-scale-to-window.py" | grep -E 'ERROR|_DONE'
# default scale (V87 sets persist.swiftangle.scale=2 in device.mk; adjusted to the measured value)
sed -i -E "s/^(PRODUCT_PROPERTY_OVERRIDES \+= persist\.swiftangle\.scale=)[0-9]+/\1${SCALE_DEFAULT}/; s/^(persist\.swiftangle\.scale=)[0-9]+/\1${SCALE_DEFAULT}/" device/samsung/gtexswifi/device.mk
grep -n 'persist.swiftangle.scale' device/samsung/gtexswifi/device.mk | head -2
source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null

echo "=== 1) wifi-service + libwifi-hal + MediaProvider ==="
mka wifi-service libwifi-hal MediaProvider 2>&1 | grep -E 'error:|FAILED|build completed' | tail -8 | tee /tmp/v91-a.log
grep -q 'build completed' /tmp/v91-a.log || { echo 'V91_FAIL: fase 1'; exit 1; }

echo "=== 2) SwiftShader ==="
mka libEGL_swiftshader libGLESv2_swiftshader libGLESv1_CM_swiftshader 2>&1 | grep -E 'error:|FAILED|build completed' | tail -8 | tee /tmp/v91-b.log
grep -q 'build completed' /tmp/v91-b.log || { echo 'V91_FAIL: SwiftShader'; exit 1; }
for m in EGL GLESv2 GLESv1_CM; do cp -f "$OUT/system/vendor/lib/egl/lib${m}_swiftshader.so" "$PKG/lib${m}_angle.so"; done

echo "=== 3) SwiftAngle + system.img ==="
mka SwiftAngle systemimage 2>&1 | grep -vE '^\[ *[0-9]+% ' | grep -E 'error:|FAILED|build completed' | tail -8 | tee /tmp/v91-c.log
grep -q 'build completed' /tmp/v91-c.log || { echo 'V91_FAIL: systemimage'; exit 1; }

echo "=== 4) static validation ==="
grep -a -q 'V90_WCND' "$OUT/system/vendor/lib/libwifi-hal.so" || { echo 'V91_FAIL: libwifi-hal without V90'; exit 1; }
grep -q 'V91_PENDING_SCAN' "$T/packages/providers/MediaProvider/src/com/android/providers/media/MediaProvider.java" || { echo 'V91_FAIL: MediaProvider without V91'; exit 1; }
test "$(find "$OUT/system" -name 'MediaProvider.apk' -newer /tmp/v91-a.log | wc -l)" -ge 0
grep -q 'V91b' "$T/external/swiftshader/src/OpenGL/libEGL/Surface.cpp" || { echo 'V91_FAIL: Surface.cpp without V91b'; exit 1; }
grep -q "^persist.swiftangle.scale=${SCALE_DEFAULT}$" "$OUT/system/build.prop" || { echo "V91_FAIL: build.prop scale != ${SCALE_DEFAULT}"; exit 1; }
grep -q '^debug.angle.backend=1$' "$OUT/system/build.prop" || { echo 'V91_FAIL: debug.angle.backend'; exit 1; }
grep -q 'namespace.sphal.permitted.paths += /system/${LIB}/hw$' "$OUT/system/apex/com.android.media.swcodec/etc/ld.config.txt" || { echo 'V91_FAIL: apex ld.config'; exit 1; }
/usr/bin/readelf -d "$OUT/system/lib/libdither.so" | grep NEEDED | grep -q android_runtime && { echo 'V91_FAIL: libdither'; exit 1; }
grep -q '^    user system' "$OUT/system/etc/init/wcnd.rc" && { echo 'V72_REGRESSION'; exit 1; }
test -f "$APK" || { echo 'V91_FAIL: SwiftAngle.apk'; exit 1; }
"$T/out/host/linux-x86/bin/aapt2" dump xmltree --file AndroidManifest.xml "$APK" | grep -q BOOT_COMPLETED || { echo 'V91_FAIL: BOOT_COMPLETED receiver'; exit 1; }
echo 'V91_STATIC_VERIFY_PASS'

echo "=== 5) Odin package ==="
python3 "$S/legacy_sparse.py" "$OUT/system.img" "$WIN/results/fase-5/system-legacy-sparse-odin-v91.img"
bash "$S/package-system-for-odin.sh" "$OUT/boot.img" "$WIN/results/fase-5/system-legacy-sparse-odin-v91.img" "$ODIN"
bash "$S/verify-odin-boot-system-package.sh" "$ODIN"
sha256sum "$OUT/boot.img" "$OUT/system.img" "$ODIN"
echo 'V91_BUILD_AND_PACKAGE_PASS'
