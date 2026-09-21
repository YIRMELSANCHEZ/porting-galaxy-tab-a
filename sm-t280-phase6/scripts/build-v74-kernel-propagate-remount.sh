#!/bin/bash
# V74: applies apply-v74-kernel-propagate-remount.py, forces the kernel relink (gotcha: mka bootimage
# does not always recompile/relink after touching source), verifies and packages boot(V74)+system(V73) for Odin.
# Run inside WSL (user lineage).
set -e
T=/home/lineage/android/lineage-17.1
WIN=/mnt/c/Dev/Experiments/porting-galaxy-tab-a
S=$WIN/sm-t280-phase6/scripts
OUT=$T/out/target/product/gtexswifi
KO=$OUT/obj/KERNEL_OBJ

cd "$T"
python3 "$S/apply-v74-kernel-propagate-remount.py"
touch kernel/samsung/gtexswifi/fs/pnode.c
rm -f "$KO/fs/pnode.o" "$KO/arch/arm/boot/zImage" "$KO/arch/arm/boot/Image" "$KO/vmlinux" "$OUT/kernel" "$OUT/boot.img"
BEFORE_SYS=$(sha256sum "$OUT/system.img" | cut -c1-16)

source build/envsetup.sh >/dev/null
lunch lineage_gtexswifi-userdebug >/dev/null
mka bootimage 2>&1 | grep -vE '^\[ *[0-9]+% ' | grep -E 'error|Error|warning: .*pnode|pnode|zImage|boot.img|build completed|FAILED' | tail -20

echo "=== verify ==="
ls -la "$KO/fs/pnode.o" "$OUT/kernel" "$OUT/boot.img"
grep -c "propagation_next" "$KO/fs/pnode.o" >/dev/null && echo "pnode.o contains refs (binary)"
# the local symbol propagation_next must remain and propagate_remount must reference __lookup_mnt
"$T/prebuilts/gcc/linux-x86/arm/arm-linux-androideabi-4.9/bin/arm-linux-androideabi-objdump" -d "$KO/fs/pnode.o" 2>/dev/null | awk '/<propagate_remount>:/,/^$/' | grep -cE "__lookup_mnt" | sed 's/^/refs to __lookup_mnt in propagate_remount: /'
echo "system.img unchanged: $BEFORE_SYS == $(sha256sum "$OUT/system.img" | cut -c1-16)"

echo "=== package (boot V74 + system V73 legacy sparse already generated) ==="
test -f "$WIN/results/fase-5/system-legacy-sparse-odin-v73.img" || { echo "MISSING system v73 sparse"; exit 1; }
bash "$S/package-system-for-odin.sh" "$OUT/boot.img" \
  "$WIN/results/fase-5/system-legacy-sparse-odin-v73.img" \
  "$WIN/sm-t280-phase6/packages/SM-T280-android10-storage-remount-PHASE6-v74-DO-NOT-FLASH.tar.md5"
