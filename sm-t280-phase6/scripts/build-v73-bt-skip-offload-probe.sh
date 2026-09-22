#!/bin/bash
# V73: applies apply-v73-bt-skip-offload-probe.py, rebuilds libbluetooth + system.img, verifies
# and packages for Odin (boot.img unchanged). Run inside WSL (user lineage).
set -e
T=/home/lineage/android/lineage-17.1
WIN=/mnt/c/Dev/Experiments/porting-galaxy-tab-a
S=$WIN/sm-t280-phase6/scripts
OUT=$T/out/target/product/gtexswifi

cd "$T"
python3 "$S/apply-v73-bt-skip-offload-probe.py"

source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null
mka systemimage 2>&1 | grep -vE '^\[ *[0-9]+% ' | tail -30

echo "=== verify in the staging ==="
grep -c 'V73 skipping BLE offload' "$OUT/system/lib/libbluetooth.so" || { echo "V73_STAGING_FAIL_LIB"; exit 1; }
grep -H 'ro.bluetooth.skip_offload_probe' "$OUT/system/build.prop" || { echo "V73_STAGING_FAIL_PROP"; exit 1; }
grep -q '^    user system' "$OUT/system/etc/init/wcnd.rc" && { echo "V72_REGRESSION"; exit 1; }
echo "V73_STAGING_OK"

echo "=== package ==="
python3 "$S/legacy_sparse.py" "$OUT/system.img" "$WIN/results/phase-5/system-legacy-sparse-odin-v73.img"
bash "$S/package-system-for-odin.sh" "$OUT/boot.img" \
  "$WIN/results/phase-5/system-legacy-sparse-odin-v73.img" \
  "$WIN/sm-t280-phase6/packages/SM-T280-android10-bt-skip-offload-PHASE6-v73-DO-NOT-FLASH.tar.md5"
