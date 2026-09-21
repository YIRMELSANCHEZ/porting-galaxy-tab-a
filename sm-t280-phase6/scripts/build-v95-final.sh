#!/bin/bash
# V95 (single Odin package): V92 (camera + linker) + V93 (fractional scale, quality via properties) +
# V94 (NV12) + V94b (H.264 HW, OMX with audio group, plugin fix, nice) + V95 (counters, gated) +
# V96/V96b (real fences, deferred clears) + V96c (spin, off) + V96d (time per GL call, gated) +
# V97 (libgui: droppable buffers to SurfaceTexture) + V97b/V97c (H.264 traces gated, hwvideo).
# Accumulates V87..V91b. Run in WSL (lineage).
# Default properties (all changeable with setprop persist.swiftangle.*):
#   scale=2.75 threads=4 texq=0 mipq=0 nice=10 fence=1 deferclear=1 spin=0 stats=0 bqdrop=1 hwvideo=0 vtrace=0
#   (curve measured 2026-09-21 in the main space: 2.5->3.4 fps  2.75->4.4  3->4.8)
set -eo pipefail
T=/home/lineage/android/lineage-17.1
WIN=/mnt/c/Dev/Experiments/porting-galaxy-tab-a
S=$WIN/sm-t280-phase6/scripts
OUT=$T/out/target/product/gtexswifi
PKG=$T/device/samsung/gtexswifi/swiftangle/lib/armeabi-v7a
APK=$OUT/system/app/SwiftAngle/SwiftAngle.apk
DM=$T/device/samsung/gtexswifi/device.mk
SCALE=${SWIFTANGLE_SCALE_DEFAULT:-2.75}
ODIN=$WIN/sm-t280-phase6/packages/SM-T280-android10-perf-hwvideo-PHASE6-v95-DO-NOT-FLASH.tar.md5

cd "$T"
for v in apply-v87-clean-wifi-angle apply-v88-swiftangle-scaled-egl apply-v89-wifi-start-recovery apply-v90-wifi-wcnd-notify \
         apply-v91-mediaprovider-pending-scan apply-v91b-swiftangle-scale-to-window apply-v92-camera-provider \
         apply-v92b-linker-textrel-vendor-hal apply-v93-swiftangle-quality-props apply-v94-swiftshader-nv12 \
         apply-v94b-omx-hw-video apply-v95-stats apply-v96-fence-deferclear apply-v96b-clear-per-cluster \
         apply-v96c-worker-spin apply-v96d-gl-time apply-v97-bq-drop apply-v97b-h264-trace apply-v97c-hwvideo-toggle; do
  python3 "$S/$v.py" | grep -E 'ERROR|_DONE'
done
# default properties
sed -i -E "s/^(PRODUCT_PROPERTY_OVERRIDES \+= persist\.swiftangle\.scale=)[0-9.]+/\1${SCALE}/" "$DM"
for kv in "threads=4" "texq=0" "mipq=0" "nice=10" "fence=1" "deferclear=1" "spin=0" "stats=0" "bqdrop=1" "hwvideo=${SWIFTANGLE_HWVIDEO:-0}" "vtrace=0"; do
  k=${kv%%=*}
  if grep -q "persist.swiftangle.${k}=" "$DM"; then
    sed -i -E "s/^(PRODUCT_PROPERTY_OVERRIDES \+= persist\.swiftangle\.${k}=)[-0-9.]+/\1${kv#*=}/" "$DM"
  else
    printf '\nPRODUCT_PROPERTY_OVERRIDES += persist.swiftangle.%s\n' "$kv" >> "$DM"
  fi
done
grep -n 'persist.swiftangle' "$DM"
source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null

echo "=== 1) SwiftShader ==="
mka libEGL_swiftshader libGLESv2_swiftshader libGLESv1_CM_swiftshader 2>&1 | grep -E 'error:|FAILED|build completed' | tail -12 | tee /tmp/v95f-a.log
grep -q 'build completed' /tmp/v95f-a.log || { echo 'V95_FAIL: SwiftShader'; exit 1; }
for m in EGL GLESv2 GLESv1_CM; do cp -f "$OUT/system/vendor/lib/egl/lib${m}_swiftshader.so" "$PKG/lib${m}_angle.so"; done

echo "=== 2) libgui + OMX + camera + linker + SwiftAngle + system.img ==="
mka libgui libstagefrighthw libstagefright_sprd_h264dec linker android.hardware.camera.provider@2.4-service android.hardware.camera.provider@2.4-impl libcamera_shim SwiftAngle systemimage 2>&1 \
  | grep -vE '^\[ *[0-9]+% ' | grep -E 'error:|FAILED|build completed' | tail -8 | tee /tmp/v95f-b.log
grep -q 'build completed' /tmp/v95f-b.log || { echo 'V95_FAIL: systemimage'; exit 1; }

echo "=== 3) static validation ==="
grep -q 'OMX.sprd.h264.decoder' "$OUT/system/etc/media_codecs.xml" || { echo 'V95_FAIL: media_codecs'; exit 1; }
grep -q 'group camera drmrpc mediadrm audio' "$OUT/system/vendor/etc/init/zz-omx-vsp.rc" || { echo 'V95_FAIL: rc OMX'; exit 1; }
grep -a -q 'V94b: initCheck failed' "$OUT/system/lib/libstagefrighthw.so" || { echo 'V95_FAIL: plugin'; exit 1; }
grep -a -q 'persist.swiftangle.hwvideo' "$OUT/system/lib/libstagefright_sprd_h264dec.so" || { echo 'V95_FAIL: hwvideo toggle'; exit 1; }
grep -a -q 'persist.swiftangle.bqdrop' "$OUT/system/lib/libgui.so" || { echo 'V95_FAIL: libgui'; exit 1; }
for k in nice texq deferclear stats spin; do grep -a -q "persist.swiftangle.${k}" "$PKG/libGLESv2_angle.so" || { echo "V95_FAIL: libGLESv2 without ${k}"; exit 1; }; done
grep -a -q 'persist.swiftangle.fence' "$PKG/libEGL_angle.so" || { echo 'V95_FAIL: libEGL fence'; exit 1; }
grep -q 'V94_NV12' "$T/external/swiftshader/src/Renderer/Surface.cpp" || { echo 'V95_FAIL: NV12'; exit 1; }
SYSLIB=$OUT/system/app/SwiftAngle/lib/arm/libGLESv2_angle.so
test -f "$SYSLIB" && { cmp -s "$PKG/libGLESv2_angle.so" "$SYSLIB" || { echo 'V95_FAIL: lib de sistema vieja'; exit 1; }; }
for k in scale threads texq mipq nice fence deferclear spin stats bqdrop hwvideo vtrace; do grep -q "^persist.swiftangle.${k}=" "$OUT/system/build.prop" || { echo "V95_FAIL: build.prop without ${k}"; exit 1; }; done
grep -q "^persist.swiftangle.scale=${SCALE}$" "$OUT/system/build.prop" || { echo 'V95_FAIL: scale'; exit 1; }
test -f "$OUT/system/vendor/bin/hw/android.hardware.camera.provider@2.4-service" || { echo 'V95_FAIL: camera'; exit 1; }
L=$(find "$OUT/system/apex" -path '*runtime*' -name 'linker' | head -1); test -n "$L" || L="$OUT/system/bin/linker"
grep -a -q '/system/vendor/bin/hw/' "$L" || { echo 'V95_FAIL: linker without V92b'; exit 1; }
grep -a -q 'V90_WCND' "$OUT/system/vendor/lib/libwifi-hal.so" || { echo 'V95_FAIL: V90'; exit 1; }
grep -q '^    user system' "$OUT/system/etc/init/wcnd.rc" && { echo 'V72_REGRESSION'; exit 1; }
echo 'V95_STATIC_VERIFY_PASS'

echo "=== 4) Odin package ==="
python3 "$S/legacy_sparse.py" "$OUT/system.img" "$WIN/results/fase-5/system-legacy-sparse-odin-v95.img"
bash "$S/package-system-for-odin.sh" "$OUT/boot.img" "$WIN/results/fase-5/system-legacy-sparse-odin-v95.img" "$ODIN"
bash "$S/verify-odin-boot-system-package.sh" "$ODIN"
sha256sum "$OUT/boot.img" "$OUT/system.img" "$ODIN"
echo 'V95_BUILD_AND_PACKAGE_PASS'
