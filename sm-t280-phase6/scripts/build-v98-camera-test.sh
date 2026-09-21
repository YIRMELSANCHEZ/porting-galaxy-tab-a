#!/bin/bash
# V98 (hot test): applies the patch and compiles only camera.device@1.0-impl. Does not produce a package.
set -eo pipefail
T=/home/lineage/android/lineage-17.1
S=/mnt/c/Dev/Experiments/porting-galaxy-tab-a/sm-t280-phase6/scripts
OUT=$T/out/target/product/gtexswifi
cd "$T"
python3 "$S/apply-v98-camera-null-user.py"
grep -n 'V98' hardware/interfaces/camera/device/1.0/default/CameraDevice.cpp | head
grep -n 'LD_' device/samsung/gtexswifi/system/etc/init/zz-camera-provider-shim.rc
source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null
mka camera.device@1.0-impl 2>&1 | grep -E 'error:|FAILED|build completed' | tail -5
L=$OUT/system/vendor/lib/camera.device@1.0-impl.so
test -f "$L" || L=$OUT/vendor/lib/camera.device@1.0-impl.so
grep -a -q 'V98' "$L" 2>/dev/null && echo 'V98 marker in the lib: yes' || echo 'V98 marker in the lib: no (normal, it is code, not a string)'
ls -l "$L"; sha256sum "$L"
cp -f "$L" /mnt/c/Dev/Experiments/porting-galaxy-tab-a/sm-t280-phase6/apps/camera.device@1.0-impl-v98.so
echo V98_TEST_BUILD_OK
