#!/bin/bash
# V96 (final "general functional" Odin package): V95 base (all the platform fixes:
# wifi, BT, power, storage, camera provider, SwiftAngle GLES3, HW H.264 video, NV12) +
# V98 (camera: shim LD_PRELOAD + null-pointer fix of the 5.1 HAL in get_memory) +
# V99 (microG: GmsCore + FakeStore as priv-app, native LineageOS signature spoofing).
# Goal: general-purpose tablet with camera, microphone, store (Aurora) and Google apps via microG.
# The target-app-specific optimizations (per-app ANGLE opt-in + props tuning) remain
# are not enabled by default (inert without ANGLE opt-in). Run in WSL (lineage).
set -eo pipefail
T=/home/lineage/android/lineage-17.1
WIN=/mnt/c/Dev/Experiments/porting-galaxy-tab-a
S=$WIN/sm-t280-phase6/scripts
OUT=$T/out/target/product/gtexswifi
PKG=$T/device/samsung/gtexswifi/swiftangle/lib/armeabi-v7a
DM=$T/device/samsung/gtexswifi/device.mk
SCALE=${SWIFTANGLE_SCALE_DEFAULT:-2.75}
ODIN=$WIN/sm-t280-phase6/packages/SM-T280-android10-general-microg-camera-PHASE6-v96-DO-NOT-FLASH.tar.md5

cd "$T"
for v in apply-v87-clean-wifi-angle apply-v88-swiftangle-scaled-egl apply-v89-wifi-start-recovery apply-v90-wifi-wcnd-notify \
         apply-v91-mediaprovider-pending-scan apply-v91b-swiftangle-scale-to-window apply-v92-camera-provider \
         apply-v92b-linker-textrel-vendor-hal apply-v93-swiftangle-quality-props apply-v94-swiftshader-nv12 \
         apply-v94b-omx-hw-video apply-v95-stats apply-v96-fence-deferclear apply-v96b-clear-per-cluster \
         apply-v96c-worker-spin apply-v96d-gl-time apply-v97-bq-drop apply-v97b-h264-trace apply-v97c-hwvideo-toggle \
         apply-v98-camera-null-user apply-v99-microg; do
  python3 "$S/$v.py" | grep -E 'ERROR|_DONE'
done
# default properties (inert without ANGLE opt-in; kept for documented reuse)
sed -i -E "s/^(PRODUCT_PROPERTY_OVERRIDES \+= persist\.swiftangle\.scale=)[0-9.]+/\1${SCALE}/" "$DM"
for kv in "threads=4" "texq=0" "mipq=0" "nice=10" "fence=1" "deferclear=1" "spin=0" "stats=0" "bqdrop=1" "hwvideo=${SWIFTANGLE_HWVIDEO:-0}" "vtrace=0"; do
  k=${kv%%=*}
  if grep -q "persist.swiftangle.${k}=" "$DM"; then
    sed -i -E "s/^(PRODUCT_PROPERTY_OVERRIDES \+= persist\.swiftangle\.${k}=)[-0-9.]+/\1${kv#*=}/" "$DM"
  else
    printf '\nPRODUCT_PROPERTY_OVERRIDES += persist.swiftangle.%s\n' "$kv" >> "$DM"
  fi
done
grep -n 'GmsCore\|FakeStore\|microg-permissions' "$DM"
source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null

echo "=== 1) SwiftShader ==="
mka libEGL_swiftshader libGLESv2_swiftshader libGLESv1_CM_swiftshader 2>&1 | grep -E 'error:|FAILED|build completed' | tail -12 | tee /tmp/v96f-a.log
grep -q 'build completed' /tmp/v96f-a.log || { echo 'V96_FAIL: SwiftShader'; exit 1; }
for m in EGL GLESv2 GLESv1_CM; do cp -f "$OUT/system/vendor/lib/egl/lib${m}_swiftshader.so" "$PKG/lib${m}_angle.so"; done

echo "=== 2) libgui + OMX + camera (V98) + linker + SwiftAngle + microG + system.img ==="
mka libgui libstagefrighthw libstagefright_sprd_h264dec linker android.hardware.camera.provider@2.4-service \
    android.hardware.camera.provider@2.4-impl camera.device@1.0-impl libcamera_shim SwiftAngle GmsCore FakeStore systemimage 2>&1 \
  | grep -vE '^\[ *[0-9]+% ' | grep -E 'error:|FAILED|build completed' | tail -8 | tee /tmp/v96f-b.log
grep -q 'build completed' /tmp/v96f-b.log || { echo 'V96_FAIL: systemimage'; exit 1; }

echo "=== 3) static validation ==="
# --- base V95 (plataforma) ---
grep -q 'OMX.sprd.h264.decoder' "$OUT/system/etc/media_codecs.xml" || { echo 'V96_FAIL: media_codecs'; exit 1; }
grep -a -q 'V94_NV12' "$T/external/swiftshader/src/Renderer/Surface.cpp" || { echo 'V96_FAIL: NV12'; exit 1; }
test -f "$OUT/system/vendor/bin/hw/android.hardware.camera.provider@2.4-service" || { echo 'V96_FAIL: camera provider'; exit 1; }
L=$(find "$OUT/system/apex" -path '*runtime*' -name 'linker' | head -1); test -n "$L" || L="$OUT/system/bin/linker"
grep -a -q '/system/vendor/bin/hw/' "$L" || { echo 'V96_FAIL: linker without V92b'; exit 1; }
grep -a -q 'V90_WCND' "$OUT/system/vendor/lib/libwifi-hal.so" || { echo 'V96_FAIL: V90'; exit 1; }
grep -q '^    user system' "$OUT/system/etc/init/wcnd.rc" && { echo 'V72_REGRESSION'; exit 1; }
# --- V98 camera ---
grep -q 'sV98LastOpened' "$T/hardware/interfaces/camera/device/1.0/default/CameraDevice.cpp" || { echo 'V96_FAIL: V98 source'; exit 1; }
grep -q 'LD_PRELOAD' "$OUT/system/vendor/etc/init/zz-camera-provider-shim.rc" || { echo 'V96_FAIL: V98 rc LD_PRELOAD'; exit 1; }
test -f "$OUT/system/vendor/lib/camera.device@1.0-impl.so" || { echo 'V96_FAIL: camera device impl'; exit 1; }
# --- V99 microG ---
test -f "$OUT/system/priv-app/GmsCore/GmsCore.apk" || { echo 'V96_FAIL: GmsCore'; exit 1; }
test -f "$OUT/system/priv-app/FakeStore/FakeStore.apk" || { echo 'V96_FAIL: FakeStore'; exit 1; }
test -f "$OUT/system/etc/permissions/microg-permissions.xml" || { echo 'V96_FAIL: microg permissions'; exit 1; }
python3 -c "import xml.dom.minidom,sys; xml.dom.minidom.parse('$OUT/system/etc/permissions/microg-permissions.xml')" || { echo 'V96_FAIL: invalid microg xml'; exit 1; }
grep -q 'com.google.android.gms' "$OUT/system/etc/permissions/microg-permissions.xml" || { echo 'V96_FAIL: microg xml without gms'; exit 1; }
# The installed signature must remain microG's ("NOGAPPS Project", serial 26ffa009); if PRESIGNED
# had altered it, the signature spoofing would not work.
KT=$T/prebuilts/jdk/jdk9/linux-x86/bin/keytool
for apk in GmsCore/GmsCore.apk FakeStore/FakeStore.apk; do
  own=$("$KT" -printcert -jarfile "$OUT/system/priv-app/$apk" 2>/dev/null | grep -m1 'Owner:')
  echo "$own" | grep -q 'NOGAPPS Project' || { echo "V96_FAIL: broken microG signature in $apk ($own)"; exit 1; }
done
echo 'V96_STATIC_VERIFY_PASS'

echo "=== 4) Odin package ==="
python3 "$S/legacy_sparse.py" "$OUT/system.img" "$WIN/results/fase-5/system-legacy-sparse-odin-v96.img"
bash "$S/package-system-for-odin.sh" "$OUT/boot.img" "$WIN/results/fase-5/system-legacy-sparse-odin-v96.img" "$ODIN"
bash "$S/verify-odin-boot-system-package.sh" "$ODIN"
sha256sum "$OUT/boot.img" "$OUT/system.img" "$ODIN"
echo 'V96_BUILD_AND_PACKAGE_PASS'
