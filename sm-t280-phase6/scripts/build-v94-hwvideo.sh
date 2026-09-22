#!/bin/bash
# V94 (Odin package): V92 (camera + linker) + V93 (fractional scale, quality via properties) +
# V94 (SwiftShader NV12) + V94b (decodificador H.264 HW: media_codecs, grupo audio en OMX, fix plugin,
# worker nice). Accumulates V87..V91b. Run in WSL (lineage).
# Default properties (adjustable by environment; all hot-changeable with setprop persist.*):
#   SWIFTANGLE_SCALE_DEFAULT=2.5 SWIFTANGLE_THREADS=3 SWIFTANGLE_TEXQ=0 SWIFTANGLE_MIPQ=0 SWIFTANGLE_NICE=10
set -eo pipefail
T=/home/lineage/android/lineage-17.1
WIN=/mnt/c/Dev/Experiments/porting-galaxy-tab-a
S=$WIN/sm-t280-phase6/scripts
OUT=$T/out/target/product/gtexswifi
PKG=$T/device/samsung/gtexswifi/swiftangle/lib/armeabi-v7a
APK=$OUT/system/app/SwiftAngle/SwiftAngle.apk
DM=$T/device/samsung/gtexswifi/device.mk
SCALE=${SWIFTANGLE_SCALE_DEFAULT:-2.5}
THREADS=${SWIFTANGLE_THREADS:-3}
TEXQ=${SWIFTANGLE_TEXQ:-0}
MIPQ=${SWIFTANGLE_MIPQ:-0}
NICE=${SWIFTANGLE_NICE:-10}
ODIN=$WIN/sm-t280-phase6/packages/SM-T280-android10-hwvideo-PHASE6-v94-DO-NOT-FLASH.tar.md5

cd "$T"
for v in apply-v87-clean-wifi-angle apply-v88-swiftangle-scaled-egl apply-v89-wifi-start-recovery apply-v90-wifi-wcnd-notify \
         apply-v91-mediaprovider-pending-scan apply-v91b-swiftangle-scale-to-window apply-v92-camera-provider \
         apply-v92b-linker-textrel-vendor-hal apply-v93-swiftangle-quality-props apply-v94-swiftshader-nv12 \
         apply-v94b-omx-hw-video; do
  python3 "$S/$v.py" | grep -E 'ERROR|_DONE'
done
# default properties
sed -i -E "s/^(PRODUCT_PROPERTY_OVERRIDES \+= persist\.swiftangle\.scale=)[0-9.]+/\1${SCALE}/" "$DM"
for kv in "threads=${THREADS}" "texq=${TEXQ}" "mipq=${MIPQ}" "nice=${NICE}"; do
  k=${kv%%=*}
  if grep -q "persist.swiftangle.${k}=" "$DM"; then
    sed -i -E "s/^(PRODUCT_PROPERTY_OVERRIDES \+= persist\.swiftangle\.${k}=)[-0-9]+/\1${kv#*=}/" "$DM"
  else
    printf '\nPRODUCT_PROPERTY_OVERRIDES += persist.swiftangle.%s\n' "$kv" >> "$DM"
  fi
done
grep -n 'persist.swiftangle' "$DM"
source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null

echo "=== 1) SwiftShader ==="
mka libEGL_swiftshader libGLESv2_swiftshader libGLESv1_CM_swiftshader 2>&1 | grep -E 'error:|FAILED|build completed' | tail -12 | tee /tmp/v94-a.log
grep -q 'build completed' /tmp/v94-a.log || { echo 'V94_FAIL: SwiftShader'; exit 1; }
for m in EGL GLESv2 GLESv1_CM; do cp -f "$OUT/system/vendor/lib/egl/lib${m}_swiftshader.so" "$PKG/lib${m}_angle.so"; done

echo "=== 2) OMX plugin + camera + linker + SwiftAngle + system.img ==="
mka libstagefrighthw linker android.hardware.camera.provider@2.4-service android.hardware.camera.provider@2.4-impl libcamera_shim SwiftAngle systemimage 2>&1 \
  | grep -vE '^\[ *[0-9]+% ' | grep -E 'error:|FAILED|build completed' | tail -8 | tee /tmp/v94-b.log
grep -q 'build completed' /tmp/v94-b.log || { echo 'V94_FAIL: systemimage'; exit 1; }

echo "=== 3) static validation ==="
grep -q 'OMX.sprd.h264.decoder' "$OUT/system/etc/media_codecs.xml" || { echo 'V94_FAIL: media_codecs without HW'; exit 1; }
grep -q 'group camera drmrpc mediadrm audio' "$OUT/system/vendor/etc/init/zz-omx-vsp.rc" || { echo 'V94_FAIL: rc OMX'; exit 1; }
grep -a -q 'V94b: initCheck failed' "$OUT/system/lib/libstagefrighthw.so" || { echo 'V94_FAIL: plugin without V94b'; exit 1; }
grep -a -q 'persist.swiftangle.nice' "$PKG/libGLESv2_angle.so" || { echo 'V94_FAIL: SwiftShader without nice'; exit 1; }
grep -a -q 'persist.swiftangle.texq' "$PKG/libGLESv2_angle.so" || { echo 'V94_FAIL: SwiftShader without V93'; exit 1; }
grep -q 'V94_NV12' "$T/external/swiftshader/src/Renderer/Surface.cpp" || { echo 'V94_FAIL: NV12'; exit 1; }
SYSLIB=$OUT/system/app/SwiftAngle/lib/arm/libGLESv2_angle.so
if [ -f "$SYSLIB" ]; then
  cmp -s "$PKG/libGLESv2_angle.so" "$SYSLIB" || { echo 'V94_FAIL: lib de sistema vieja'; exit 1; }
else
  unzip -l "$APK" | grep -q 'libGLESv2_angle.so' || { echo 'V94_FAIL: APK without libs'; exit 1; }
  cmp -s "$PKG/libGLESv2_angle.so" <(unzip -p "$APK" lib/armeabi-v7a/libGLESv2_angle.so) || { echo 'V94_FAIL: APK with old libGLESv2'; exit 1; }
fi
for k in scale threads texq mipq nice; do grep -q "^persist.swiftangle.${k}=" "$OUT/system/build.prop" || { echo "V94_FAIL: build.prop without ${k}"; exit 1; }; done
grep -q '^persist.swiftangle.scale=2.5$' "$OUT/system/build.prop" || { echo 'V94_FAIL: scale'; exit 1; }
test -f "$OUT/system/vendor/bin/hw/android.hardware.camera.provider@2.4-service" || { echo 'V94_FAIL: camera'; exit 1; }
L=$(find "$OUT/system/apex" -path '*runtime*' -name 'linker' | head -1); test -n "$L" || L="$OUT/system/bin/linker"
grep -a -q '/system/vendor/bin/hw/' "$L" || { echo 'V94_FAIL: linker without V92b'; exit 1; }
grep -a -q 'V90_WCND' "$OUT/system/vendor/lib/libwifi-hal.so" || { echo 'V94_FAIL: V90'; exit 1; }
grep -q '^    user system' "$OUT/system/etc/init/wcnd.rc" && { echo 'V72_REGRESSION'; exit 1; }
echo 'V94_STATIC_VERIFY_PASS'

echo "=== 4) Odin package ==="
python3 "$S/legacy_sparse.py" "$OUT/system.img" "$WIN/results/phase-5/system-legacy-sparse-odin-v94.img"
bash "$S/package-system-for-odin.sh" "$OUT/boot.img" "$WIN/results/phase-5/system-legacy-sparse-odin-v94.img" "$ODIN"
bash "$S/verify-odin-boot-system-package.sh" "$ODIN"
sha256sum "$OUT/boot.img" "$OUT/system.img" "$ODIN"
echo 'V94_BUILD_AND_PACKAGE_PASS'
