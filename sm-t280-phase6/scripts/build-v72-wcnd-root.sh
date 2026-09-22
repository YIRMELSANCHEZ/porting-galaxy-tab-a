#!/bin/bash
# V72: applies apply-v72-wcnd-root.py, rebuilds system.img, verifies the staging and packages
# for Odin (boot.img unchanged + legacy sparse system). Run inside WSL (user lineage).
set -e
T=/home/lineage/android/lineage-17.1
WIN=/mnt/c/Dev/Experiments/porting-galaxy-tab-a
S=$WIN/sm-t280-phase6/scripts
OUT=$T/out/target/product/gtexswifi

cd "$T"
python3 "$S/apply-v72-wcnd-root.py"

source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null
mka out/target/product/gtexswifi/system/etc/init/wcnd.rc systemimage 2>&1 | tail -5

echo "=== verify in the staging ==="
cat "$OUT/system/etc/init/wcnd.rc"
if grep -q '^    user system' "$OUT/system/etc/init/wcnd.rc"; then echo "V72_STAGING_FAIL"; exit 1; fi
grep -q 'net_bt_stack' "$OUT/system/etc/init/wcnd.rc" && { echo "V72_STAGING_FAIL_GID"; exit 1; }
echo "V72_STAGING_OK"

echo "=== package ==="
python3 "$S/legacy_sparse.py" "$OUT/system.img" "$WIN/results/phase-5/system-legacy-sparse-odin-v72.img"
bash "$S/package-system-for-odin.sh" "$OUT/boot.img" \
  "$WIN/results/phase-5/system-legacy-sparse-odin-v72.img" \
  "$WIN/sm-t280-phase6/packages/SM-T280-android10-bt-wcnd-root-PHASE6-v72-DO-NOT-FLASH.tar.md5"
