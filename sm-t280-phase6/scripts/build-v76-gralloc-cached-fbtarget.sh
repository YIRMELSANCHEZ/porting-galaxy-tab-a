#!/bin/bash
# V76: applies apply-v76-gralloc-cached-fbtarget.py, rebuilds gralloc.sc8830 + system.img and
# packages boot(V75, already in out/) + system(V76) for Odin. Run inside WSL (user lineage).
set -e
T=/home/lineage/android/lineage-17.1
WIN=/mnt/c/Dev/Experiments/porting-galaxy-tab-a
S=$WIN/sm-t280-phase6/scripts
OUT=$T/out/target/product/gtexswifi

cd "$T"
python3 "$S/apply-v76-gralloc-cached-fbtarget.py"
BEFORE=$(stat -c %Y "$OUT/system/lib/hw/gralloc.sc8830.so")
BOOT=$(sha256sum "$OUT/boot.img" | cut -c1-16)
echo "boot.img in out (should be V75 fe89ef3181bfecea): $BOOT"

source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null
mka systemimage 2>&1 | grep -vE '^\[ *[0-9]+% ' | grep -E 'error:|Error |gralloc|build completed|FAILED' | tail -15

echo "=== verify ==="
AFTER=$(stat -c %Y "$OUT/system/lib/hw/gralloc.sc8830.so")
[ "$AFTER" -gt "$BEFORE" ] && echo "gralloc.sc8830.so rebuilt" || { echo "V76_FAIL: gralloc not rebuilt"; exit 1; }
grep -c "V29: HW_FB via ION copy" "$OUT/system/lib/hw/gralloc.sc8830.so" | sed 's/^/V29 branch present: /'
grep -q 'ro.bluetooth.skip_offload_probe=1' "$OUT/system/build.prop" && echo "V73 prop present"
grep -q '^    user system' "$OUT/system/etc/init/wcnd.rc" && { echo "V72_REGRESSION"; exit 1; } || echo "V72 wcnd ok"

echo "=== package (boot V75 + system V76) ==="
python3 "$S/legacy_sparse.py" "$OUT/system.img" "$WIN/results/fase-5/system-legacy-sparse-odin-v76.img"
bash "$S/package-system-for-odin.sh" "$OUT/boot.img" \
  "$WIN/results/fase-5/system-legacy-sparse-odin-v76.img" \
  "$WIN/sm-t280-phase6/packages/SM-T280-android10-g1-binder-cachedfb-PHASE6-v76-DO-NOT-FLASH.tar.md5"
